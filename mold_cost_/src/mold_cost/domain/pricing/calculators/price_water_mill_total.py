"""Water mill total pricing calculator domain implementation."""

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

MCP_TOOL_META = {
    "name": "calculate_water_mill_total_cost",
    "description": "Calculate water mill total cost and processing time.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode, total and water_mill results",
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
    "needs": ["base_itemcode", "total", "water_mill"],
}

_CALCULATION_STEPS_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, calculation_steps)
    VALUES
        ($1::uuid, $2::text,
         jsonb_build_array(jsonb_build_object('category', $3::text, 'steps', $4::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $3::text
        ) || jsonb_build_array(jsonb_build_object('category', $3::text, 'steps', $4::jsonb))
"""


def _round_2(value: Any) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _determine_mill_type(has_auto_material: Any, has_material_preparation: Any) -> str:
    return "s_water_mill" if bool(has_auto_material) or bool(has_material_preparation) else "l_water_mill"


def _build_price_map(water_mill_data: dict[str, Any]) -> dict[str, float]:
    def _extract_hourly_rate(prices: list[dict[str, Any]]) -> float:
        if not prices:
            return 0.0

        preferred = None
        for item in prices:
            if str(item.get("sub_category", "")).lower() == "water_mill":
                preferred = item
                break
        if preferred is None:
            preferred = prices[0]
        return float(preferred.get("price", 0) or 0)

    return {
        "small_hourly_rate": _extract_hourly_rate(list(water_mill_data.get("s_water_mill_prices", []))),
        "large_hourly_rate": _extract_hourly_rate(list(water_mill_data.get("l_water_mill_prices", []))),
    }


def _calculate_small_grinding(costs: dict[str, Any], quantity: float, hourly_rate: float) -> tuple[float, float, list[dict[str, Any]]]:
    chamfer_minutes = float(costs.get("chamfer_cost", 0) or 0)
    bevel_minutes = float(costs.get("bevel_cost", 0) or 0)
    oil_tank_hours = float(costs.get("oil_tank_cost", 0) or 0)
    thread_ends_cost = float(costs.get("thread_ends_cost", 0) or 0)
    hanging_table_cost = float(costs.get("hanging_table_cost", 0) or 0)
    high_cost = float(costs.get("high_cost", 0) or 0)

    chamfer_hours = chamfer_minutes / 60.0
    bevel_hours = bevel_minutes / 60.0
    per_part_hours = chamfer_hours + bevel_hours + oil_tank_hours
    total_time_hours = per_part_hours * quantity
    time_cost_total = total_time_hours * hourly_rate
    fixed_cost_total = thread_ends_cost + hanging_table_cost + high_cost
    total_cost = time_cost_total + fixed_cost_total

    return (
        _round_2(total_cost),
        _round_2(total_time_hours),
        [
            {
                "step": "collect_small_grinding_inputs",
                "thread_ends_cost": thread_ends_cost,
                "hanging_table_cost": hanging_table_cost,
                "high_cost": high_cost,
                "chamfer_minutes": chamfer_minutes,
                "bevel_minutes": bevel_minutes,
                "oil_tank_hours": oil_tank_hours,
            },
            {
                "step": "convert_small_grinding_time",
                "chamfer_hours": round(chamfer_hours, 4),
                "bevel_hours": round(bevel_hours, 4),
                "per_part_hours": round(per_part_hours, 4),
            },
            {
                "step": "calculate_small_grinding_total",
                "formula": f"(({chamfer_minutes}/60)+({bevel_minutes}/60)+{oil_tank_hours}) * {quantity} * {hourly_rate} + {thread_ends_cost} + {hanging_table_cost} + {high_cost}",
                "hourly_rate": hourly_rate,
                "quantity": quantity,
                "time_cost_total": _round_2(time_cost_total),
                "fixed_cost_total": _round_2(fixed_cost_total),
                "total_cost": _round_2(total_cost),
                "total_time_hours": _round_2(total_time_hours),
            },
        ],
    )


def _calculate_large_grinding(costs: dict[str, Any], quantity: float, hourly_rate: float) -> tuple[float, float, list[dict[str, Any]]]:
    long_strip_hours = float(costs.get("long_strip_cost", 0) or 0)
    component_hours = float(costs.get("component_cost", 0) or 0)
    plate_cost = float(costs.get("plate_cost", 0) or 0)

    per_part_hours = long_strip_hours + component_hours
    total_time_hours = per_part_hours * quantity
    time_cost_total = total_time_hours * hourly_rate
    plate_cost_total = plate_cost * quantity
    total_cost = time_cost_total + plate_cost_total

    return (
        _round_2(total_cost),
        _round_2(total_time_hours),
        [
            {
                "step": "collect_large_grinding_inputs",
                "long_strip_hours": long_strip_hours,
                "component_hours": component_hours,
                "plate_cost": plate_cost,
            },
            {
                "step": "calculate_large_grinding_total",
                "formula": f"({long_strip_hours}+{component_hours}) * {quantity} * {hourly_rate} + {plate_cost} * {quantity}",
                "hourly_rate": hourly_rate,
                "quantity": quantity,
                "per_part_hours": round(per_part_hours, 4),
                "time_cost_total": _round_2(time_cost_total),
                "plate_cost_total": _round_2(plate_cost_total),
                "total_cost": _round_2(total_cost),
                "total_time_hours": _round_2(total_time_hours),
            },
        ],
    )


async def _calculate_part_total(
    part: dict[str, Any],
    cost_map: dict[str, dict[str, Any]],
    price_map: dict[str, float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    quantity = float(part.get("quantity", 1) or 1)
    has_auto_material = part.get("has_auto_material", False)
    has_material_preparation = part.get("has_material_preparation")
    mill_type = _determine_mill_type(has_auto_material, has_material_preparation)
    costs = cost_map.get(subgraph_id, {})

    calculation_steps = [
        {
            "step": "determine_mill_type",
            "has_auto_material": bool(has_auto_material),
            "has_material_preparation": bool(has_material_preparation),
            "mill_type": mill_type,
        }
    ]

    small_grinding_cost = 0.0
    small_grinding_time = 0.0
    large_grinding_cost = 0.0
    large_grinding_time = 0.0

    if mill_type == "s_water_mill":
        small_grinding_cost, small_grinding_time, detail_steps = _calculate_small_grinding(
            costs, quantity, price_map["small_hourly_rate"]
        )
        calculation_steps.extend(detail_steps)
    else:
        large_grinding_cost, large_grinding_time, detail_steps = _calculate_large_grinding(
            costs, quantity, price_map["large_hourly_rate"]
        )
        calculation_steps.extend(detail_steps)

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "quantity": quantity,
        "mill_type": mill_type,
        "small_grinding_cost": small_grinding_cost,
        "large_grinding_cost": large_grinding_cost,
        "small_grinding_time": small_grinding_time,
        "large_grinding_time": large_grinding_time,
    }
    db_data = {
        "subgraph_id": subgraph_id,
        "mill_type": mill_type,
        "small_grinding_cost": small_grinding_cost,
        "large_grinding_cost": large_grinding_cost,
        "small_grinding_time": small_grinding_time,
        "large_grinding_time": large_grinding_time,
        "calculation_steps": calculation_steps,
    }

    logger.info(
        "[%s] %s: mill_type=%s, small_cost=%.2f, large_cost=%.2f, small_time=%.2f, large_time=%.2f",
        subgraph_id,
        part_name,
        mill_type,
        small_grinding_cost,
        large_grinding_cost,
        small_grinding_time,
        large_grinding_time,
    )
    return result, db_data


async def _batch_update_subgraphs(job_id: str, updates: list[dict[str, Any]]) -> None:
    sql = """
        UPDATE subgraphs
        SET
            small_grinding_cost = $3,
            large_grinding_cost = $4,
            small_grinding_time = $5,
            large_grinding_time = $6,
            updated_at = NOW()
        WHERE job_id = $1::uuid AND subgraph_id = $2::text
    """
    tasks = [
        db.execute(
            sql,
            job_id,
            data["subgraph_id"],
            data["small_grinding_cost"],
            data["large_grinding_cost"],
            data["small_grinding_time"],
            data["large_grinding_time"],
        )
        for data in updates
    ]
    if tasks:
        await asyncio.gather(*tasks)


async def batch_upsert_with_steps(
    updates: list[dict[str, Any]],
    category: str,
    field_name: str | None,
) -> None:
    if field_name is not None:
        raise ValueError(f"Unsupported field_name for water mill total calculator: {field_name}")
    if not updates:
        return

    tasks = [
        _upsert_single_record(
            update["job_id"],
            update["subgraph_id"],
            category,
            update["steps"],
        )
        for update in updates
    ]
    await asyncio.gather(*tasks)


async def _upsert_single_record(
    job_id: str,
    subgraph_id: str,
    category: str,
    steps: list[dict[str, Any]],
) -> bool:
    await db.execute(
        _CALCULATION_STEPS_UPSERT_SQL,
        job_id,
        subgraph_id,
        category,
        json.dumps(steps, default=str),
    )
    return True


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_data = search_data["base_itemcode"]
    total_data = search_data["total"]
    water_mill_data = search_data["water_mill"]

    if not job_id:
        job_id = base_data.get("job_id")

    parts = list(base_data.get("parts", []))
    if subgraph_ids:
        allowed = set(subgraph_ids)
        parts = [part for part in parts if part.get("subgraph_id") in allowed]

    logger.info("Calculating water mill total for job_id: %s, parts count: %s", job_id, len(parts))

    price_map = _build_price_map(water_mill_data)
    cost_map = {
        detail["subgraph_id"]: detail
        for detail in total_data.get("cost_details", [])
    }

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []

    for part in parts:
        result, db_data = await _calculate_part_total(part, cost_map, price_map)
        results.append(result)
        db_updates.append(db_data)

    if db_updates:
        small_updates = [
            {
                "job_id": job_id,
                "subgraph_id": data["subgraph_id"],
                "value": data["small_grinding_cost"],
                "steps": data["calculation_steps"],
            }
            for data in db_updates
            if data["mill_type"] == "s_water_mill" and data["small_grinding_cost"] > 0
        ]
        large_updates = [
            {
                "job_id": job_id,
                "subgraph_id": data["subgraph_id"],
                "value": data["large_grinding_cost"],
                "steps": data["calculation_steps"],
            }
            for data in db_updates
            if data["mill_type"] == "l_water_mill" and data["large_grinding_cost"] > 0
        ]

        if small_updates:
            await batch_upsert_with_steps(small_updates, "water_mill_total_small", None)
        if large_updates:
            await batch_upsert_with_steps(large_updates, "water_mill_total_large", None)
        await _batch_update_subgraphs(job_id, db_updates)

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
