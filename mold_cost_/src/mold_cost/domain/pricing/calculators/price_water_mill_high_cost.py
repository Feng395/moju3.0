"""Water mill high cost pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "calculate_water_mill_high_cost",
    "description": "Calculate water mill high cost from part data and water mill price rules.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode and water_mill results",
            },
            "job_id": {
                "type": "string",
                "description": "Job ID (UUID)",
            },
            "subgraph_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subgraph ID list",
            },
        },
        "required": ["search_data"],
    },
    "handler": "calculate",
    "needs": ["base_itemcode", "water_mill"],
}

_HIGH_COST_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, high_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        high_cost = EXCLUDED.high_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""


def _determine_mill_type(has_auto_material: Any, has_material_preparation: Any) -> str:
    return "s_water_mill" if bool(has_auto_material) or bool(has_material_preparation) else "l_water_mill"


def _build_price_map(water_mill_data: dict[str, Any]) -> dict[str, Any]:
    price_map: dict[str, Any] = {}
    for price in water_mill_data.get("s_water_mill_prices", []):
        if price.get("sub_category") != "high":
            continue
        try:
            price_map["high"] = {
                "price": float(price.get("price", 0) or 0),
                "unit": price.get("unit", ""),
            }
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to parse high price: %s, error: %s", price.get("price"), exc)
    return price_map


async def _get_material_preparation_thickness(job_id: str, part_code: str) -> float:
    subgraph_sql = """
        SELECT subgraph_id
        FROM subgraphs
        WHERE job_id = $1::uuid AND part_code = $2
        LIMIT 1
    """
    try:
        row = await db.fetch_one(subgraph_sql, job_id, part_code)
        if not row:
            logger.warning("No subgraph found for part_code: %s", part_code)
            return 0.0

        subgraph_id = row["subgraph_id"]
        features_sql = """
            SELECT thickness_mm
            FROM features
            WHERE job_id = $1::uuid AND subgraph_id = $2
            LIMIT 1
        """
        row = await db.fetch_one(features_sql, job_id, subgraph_id)
        if not row:
            logger.warning("No features found for subgraph_id: %s", subgraph_id)
            return 0.0

        thickness_mm = row["thickness_mm"] or 0
        logger.info("Found thickness %smm for part_code: %s", thickness_mm, part_code)
        return float(thickness_mm)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to get material preparation thickness: %s", exc)
        return 0.0


async def _calculate_part_price(
    job_id: str,
    part: dict[str, Any],
    price_map: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    has_auto_material = part.get("has_auto_material", False)
    has_material_preparation = part.get("has_material_preparation")
    thickness_mm = float(part.get("thickness_mm") or 0)
    quantity = float(part.get("quantity") or 1)

    logger.info("Calculating high cost for part: %s (%s)", part_name, subgraph_id)

    mill_type = _determine_mill_type(has_auto_material, has_material_preparation)
    calculation_steps: list[dict[str, Any]] = [
        {
            "step": "determine_mill_type",
            "has_auto_material": bool(has_auto_material),
            "has_material_preparation": has_material_preparation,
            "mill_type": mill_type,
            "reason": f"has_auto_material={has_auto_material} or has_material_preparation={has_material_preparation}",
        }
    ]

    if mill_type != "s_water_mill":
        calculation_steps.append(
            {
                "step": "skip_high_cost",
                "note": "high cost only applies to small water mill",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "high_cost": 0.0,
                "note": "large water mill does not calculate high cost",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "high_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    if not has_material_preparation:
        calculation_steps.append(
            {
                "step": "check_material_preparation",
                "has_material_preparation": has_material_preparation,
                "note": "missing material preparation",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "high_cost": 0.0,
                "note": "missing material preparation",
            },
            None,
        )

    calculation_steps.append(
        {
            "step": "check_material_preparation",
            "has_material_preparation": has_material_preparation,
            "note": f"prepared for {has_material_preparation}",
        }
    )

    material_thickness = await _get_material_preparation_thickness(job_id, has_material_preparation)
    calculation_steps.append(
        {
            "step": "query_material_thickness",
            "material_part_code": has_material_preparation,
            "material_thickness": material_thickness,
            "current_thickness": thickness_mm,
        }
    )

    if material_thickness == 0:
        calculation_steps.append(
            {
                "step": "check_thickness_diff",
                "note": f"missing thickness for {has_material_preparation}",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "material_part_code": has_material_preparation,
                "material_thickness": material_thickness,
                "current_thickness": thickness_mm,
                "high_cost": 0.0,
                "note": f"missing thickness for {has_material_preparation}",
            },
            None,
        )

    if material_thickness == thickness_mm:
        calculation_steps.append(
            {
                "step": "check_thickness_diff",
                "material_thickness": material_thickness,
                "current_thickness": thickness_mm,
                "note": "same thickness",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "material_part_code": has_material_preparation,
                "material_thickness": material_thickness,
                "current_thickness": thickness_mm,
                "high_cost": 0.0,
                "note": "same thickness",
            },
            None,
        )

    calculation_steps.append(
        {
            "step": "check_thickness_diff",
            "material_thickness": material_thickness,
            "current_thickness": thickness_mm,
            "thickness_diff": abs(material_thickness - thickness_mm),
            "note": "thickness differs, calculate high cost",
        }
    )

    high_info = price_map.get("high", {})
    high_unit_price = float(high_info.get("price", 0) or 0)
    unit = high_info.get("unit", "")

    calculation_steps.append(
        {
            "step": "get_high_cost_unit_price",
            "unit_price": high_unit_price,
            "unit": unit,
        }
    )

    high_cost = quantity * high_unit_price
    calculation_steps.append(
        {
            "step": "calculate_high_cost",
            "quantity": quantity,
            "unit_price": high_unit_price,
            "formula": f"{quantity} * {high_unit_price}",
            "high_cost": round(high_cost, 2),
        }
    )

    return (
        {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "mill_type": mill_type,
            "material_part_code": has_material_preparation,
            "material_thickness": material_thickness,
            "current_thickness": thickness_mm,
            "quantity": quantity,
            "high_cost": round(high_cost, 2),
        },
        {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "high_cost": high_cost,
            "calculation_steps": calculation_steps,
        },
    )


async def batch_upsert_with_steps(
    updates: list[dict[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return

    if field_name != "high_cost":
        raise ValueError(f"Unsupported field_name for water mill high calculator: {field_name}")

    tasks = [
        _upsert_single_record(
            update["job_id"],
            update["subgraph_id"],
            update["value"],
            category,
            update["steps"],
        )
        for update in updates
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    failures = [result for result in results if isinstance(result, Exception)]
    if failures:
        raise failures[0]


async def _upsert_single_record(
    job_id: str,
    subgraph_id: str,
    high_cost: Any,
    category: str,
    steps: list[dict[str, Any]],
) -> bool:
    await db.execute(_HIGH_COST_UPSERT_SQL, job_id, subgraph_id, high_cost, category, json.dumps(steps, default=str))
    return True


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_data = search_data["base_itemcode"]
    water_mill_data = search_data["water_mill"]

    if not job_id:
        job_id = base_data.get("job_id")

    parts = list(base_data.get("parts", []))
    if subgraph_ids:
        allowed = set(subgraph_ids)
        parts = [part for part in parts if part.get("subgraph_id") in allowed]

    logger.info("Calculating water mill high cost for job_id: %s, parts count: %s", job_id, len(parts))

    price_map = _build_price_map(water_mill_data)
    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []

    for part in parts:
        result, db_data = await _calculate_part_price(job_id, part, price_map)
        results.append(result)
        if db_data:
            db_updates.append(db_data)

    if db_updates:
        await batch_upsert_with_steps(
            [
                {
                    "job_id": item["job_id"],
                    "subgraph_id": item["subgraph_id"],
                    "value": item["high_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "water_mill_high",
            "high_cost",
        )

    return {
        "job_id": job_id,
        "results": results,
    }


def calculate_sync(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "batch_upsert_with_steps", "calculate", "calculate_sync"]
