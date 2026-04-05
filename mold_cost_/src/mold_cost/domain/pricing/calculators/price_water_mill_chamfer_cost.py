"""Water mill chamfer pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

_CHAMFER_TYPES = (
    "c1_c2_chamfer",
    "c3_c5_chamfer",
    "r1_r2_chamfer",
    "r3_r5_chamfer",
)

MCP_TOOL_META = {
    "name": "calculate_water_mill_chamfer_cost",
    "description": "Calculate water mill chamfer cost for small water mill parts.",
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

_CHAMFER_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, chamfer_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        chamfer_cost = EXCLUDED.chamfer_cost,
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


def _build_price_map(water_mill_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    price_map: dict[str, dict[str, Any]] = {}
    for price in water_mill_data.get("s_water_mill_prices", []):
        sub_category = str(price.get("sub_category", "") or "")
        if sub_category in _CHAMFER_TYPES:
            try:
                price_map[sub_category] = {
                    "price": float(price.get("price", 0) or 0),
                    "unit": price.get("unit", ""),
                }
            except (TypeError, ValueError) as exc:
                logger.warning("Failed to parse %s price: %s, error: %s", sub_category, price.get("price"), exc)
    return price_map


def _round_2(value: Any) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


async def _calculate_part_price(
    job_id: str,
    part: dict[str, Any],
    price_map: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    has_auto_material = part.get("has_auto_material", False)
    has_material_preparation = part.get("has_material_preparation")
    water_mill = part.get("water_mill")

    mill_type = _determine_mill_type(has_auto_material, has_material_preparation)
    calculation_steps: list[dict[str, Any]] = [
        {
            "step": "determine_mill_type",
            "has_auto_material": bool(has_auto_material),
            "has_material_preparation": bool(has_material_preparation),
            "mill_type": mill_type,
        }
    ]

    if isinstance(water_mill, str):
        try:
            water_mill = json.loads(water_mill)
        except Exception as exc:
            logger.error("Failed to parse water_mill JSON for %s: %s", part_name, exc)
            water_mill = {}

    if not water_mill or "water_mill_details" not in water_mill:
        logger.warning("No water_mill_details for %s", part_name)
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "chamfer_cost": 0.0,
                "note": "no water_mill_details",
            },
            None,
        )

    water_mill_details = water_mill.get("water_mill_details", [])
    chamfer_counts: dict[str, int] = {key: 0 for key in _CHAMFER_TYPES}
    for detail in water_mill_details:
        if not isinstance(detail, dict):
            continue
        for chamfer_type in _CHAMFER_TYPES:
            if chamfer_type in detail:
                try:
                    chamfer_counts[chamfer_type] = int(detail.get(chamfer_type, 0) or 0)
                except (TypeError, ValueError):
                    chamfer_counts[chamfer_type] = 0

    calculation_steps.append(
        {
            "step": "collect_chamfer_counts",
            "chamfer_counts": chamfer_counts,
        }
    )

    if mill_type != "s_water_mill":
        calculation_steps.append(
            {
                "step": "skip_large_water_mill",
                "note": "chamfer cost applies only to small water mill parts",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "chamfer_cost": 0.0,
                "note": "large water mill does not calculate chamfer cost",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "chamfer_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    chamfer_costs: dict[str, float] = {}
    total_chamfer_cost = 0.0
    for chamfer_type, count in chamfer_counts.items():
        if count <= 0:
            continue
        price_info = price_map.get(chamfer_type, {})
        unit_price = float(price_info.get("price", 0) or 0)
        cost = count * unit_price
        chamfer_costs[chamfer_type] = cost
        total_chamfer_cost += cost
        calculation_steps.append(
            {
                "step": f"calculate_{chamfer_type}",
                "chamfer_type": chamfer_type,
                "count": count,
                "unit_price": unit_price,
                "cost": _round_2(cost),
            }
        )

    if chamfer_costs:
        calculation_steps.append(
            {
                "step": "summarize_chamfer_cost",
                "formula": " + ".join(f"{key}({_round_2(value)})" for key, value in chamfer_costs.items())
                + f" = {_round_2(total_chamfer_cost)}",
                "chamfer_costs": {key: _round_2(value) for key, value in chamfer_costs.items()},
                "total_chamfer_cost": _round_2(total_chamfer_cost),
            }
        )
    else:
        calculation_steps.append(
            {
                "step": "summarize_chamfer_cost",
                "note": "all chamfer counts are zero",
                "total_chamfer_cost": 0.0,
            }
        )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "mill_type": mill_type,
        "chamfer_counts": chamfer_counts,
        "chamfer_costs": {key: _round_2(value) for key, value in chamfer_costs.items()},
        "chamfer_cost": _round_2(total_chamfer_cost),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "chamfer_cost": total_chamfer_cost,
        "calculation_steps": calculation_steps,
    }
    return result, db_data


async def batch_upsert_with_steps(
    updates: list[dict[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return
    if field_name != "chamfer_cost":
        raise ValueError(f"Unsupported field_name for chamfer calculator: {field_name}")

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
    chamfer_cost: Any,
    category: str,
    steps: list[dict[str, Any]],
) -> bool:
    steps_json = json.dumps(steps, default=str)
    await db.execute(_CHAMFER_UPSERT_SQL, job_id, subgraph_id, chamfer_cost, category, steps_json)
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

    logger.info("Calculating water mill chamfer cost for job_id: %s, parts count: %s", job_id, len(parts))

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
                    "value": item["chamfer_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "water_mill_chamfer",
            "chamfer_cost",
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
