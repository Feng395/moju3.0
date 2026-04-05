"""Water mill oil tank pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "calculate_water_mill_oil_tank_cost",
    "description": "Calculate water mill oil tank cost from part data and water mill price rules.",
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

_OIL_TANK_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, oil_tank_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        oil_tank_cost = EXCLUDED.oil_tank_cost,
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


def _parse_water_mill_payload(water_mill: Any) -> dict[str, Any]:
    if isinstance(water_mill, str):
        try:
            return json.loads(water_mill)
        except Exception as exc:  # pragma: no cover - defensive parsing
            logger.error("Failed to parse water_mill JSON: %s", exc)
            return {}
    if isinstance(water_mill, Mapping):
        return dict(water_mill)
    return {}


def _build_price_map(water_mill_data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    price_map: dict[str, dict[str, Any]] = {}

    for price in water_mill_data.get("s_water_mill_prices", []):
        if str(price.get("sub_category")) != "oil_tank":
            continue

        try:
            price_map["oil_tank"] = {
                "price": float(price.get("price", 0) or 0),
                "unit": price.get("unit", ""),
            }
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to parse oil_tank price: %s, error: %s", price.get("price"), exc)

    return price_map


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return

    if field_name != "oil_tank_cost":
        raise ValueError(f"Unsupported field_name for water mill oil tank calculator: {field_name}")

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
    oil_tank_cost: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(_OIL_TANK_UPSERT_SQL, job_id, subgraph_id, oil_tank_cost, category, steps_json)
    return True


async def _calculate_part_price(
    job_id: str,
    part: Mapping[str, Any],
    price_map: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    has_auto_material = part.get("has_auto_material", False)
    has_material_preparation = part.get("has_material_preparation")
    water_mill = _parse_water_mill_payload(part.get("water_mill"))
    mill_type = _determine_mill_type(has_auto_material, has_material_preparation)

    logger.info("Calculating oil tank cost for part: %s (%s)", part_name, subgraph_id)

    calculation_steps: list[dict[str, Any]] = [
        {
            "step": "determine_mill_type",
            "has_auto_material": bool(has_auto_material),
            "has_material_preparation": has_material_preparation,
            "mill_type": mill_type,
            "reason": f"has_auto_material={has_auto_material} or has_material_preparation={has_material_preparation}",
        }
    ]

    if not water_mill or "water_mill_details" not in water_mill:
        calculation_steps.append(
            {
                "step": "check_water_mill_details",
                "note": "no water_mill_details data",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "oil_tank_cost": 0.0,
                "note": "no water_mill_details data",
            },
            None,
        )

    oil_tank_count = 0.0
    for detail in water_mill.get("water_mill_details", []):
        if not isinstance(detail, Mapping):
            continue
        if "oil_tank" in detail:
            try:
                oil_tank_count = float(detail.get("oil_tank", 0) or 0)
            except (TypeError, ValueError):
                oil_tank_count = 0.0
            break

    if oil_tank_count == 0:
        logger.info("No oil_tank for %s", part_name)
        calculation_steps.append(
            {
                "step": "check_oil_tank_data",
                "oil_tank_count": oil_tank_count,
                "note": "oil_tank count is zero",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "oil_tank_cost": 0.0,
                "note": "oil_tank count is zero",
            },
            None,
        )

    if mill_type != "s_water_mill":
        calculation_steps.append(
            {
                "step": "skip_large_mill",
                "note": "oil tank cost only applies to small water mill",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "oil_tank_cost": 0.0,
                "note": "large water mill does not calculate oil tank cost",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "oil_tank_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    oil_tank_info = price_map.get("oil_tank", {})
    oil_tank_unit_price = float(oil_tank_info.get("price", 0) or 0)
    unit = oil_tank_info.get("unit", "")

    calculation_steps.append(
        {
            "step": "collect_oil_tank_price",
            "unit_price": oil_tank_unit_price,
            "unit": unit,
        }
    )

    oil_tank_cost = oil_tank_count * oil_tank_unit_price

    calculation_steps.append(
        {
            "step": "calculate_oil_tank_cost",
            "oil_tank_count": oil_tank_count,
            "unit_price": oil_tank_unit_price,
            "formula": f"{oil_tank_count} * {oil_tank_unit_price}",
            "oil_tank_cost": round(oil_tank_cost, 2),
        }
    )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "mill_type": mill_type,
        "oil_tank_count": oil_tank_count,
        "oil_tank_cost": round(oil_tank_cost, 2),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "oil_tank_cost": oil_tank_cost,
        "calculation_steps": calculation_steps,
    }
    return result, db_data


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

    logger.info("Calculating water mill oil tank cost for job_id: %s, parts count: %s", job_id, len(parts))

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
                    "value": item["oil_tank_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "water_mill_oil_tank",
            "oil_tank_cost",
        )

    logger.info("Completed calculation for %s parts", len(results))
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
