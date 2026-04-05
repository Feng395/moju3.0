"""Tooth hole pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

_MIN_NUM_PATTERN = re.compile(r"([<>=]+)M(\d+)")

MCP_TOOL_META = {
    "name": "calculate_tooth_hole_cost",
    "description": "Calculate tooth hole and screw cost from base_itemcode and tooth_hole price data.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode and tooth_hole results",
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
    "needs": ["base_itemcode", "tooth_hole"],
}

_TOOTH_HOLE_COST_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, tooth_hole_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        tooth_hole_cost = EXCLUDED.tooth_hole_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""

_TOOTH_HOLE_TIME_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, tooth_hole_time_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        tooth_hole_time_cost = EXCLUDED.tooth_hole_time_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""


def _build_price_map(tooth_hole_data: Mapping[str, Any]) -> dict[str, Any]:
    """Build lookup tables for hole time, hourly rate and diameter pricing."""
    price_map: dict[str, Any] = {
        "through_hole": [],
        "blind_hole": [],
        "screw": {},
        "stop_screw": {},
    }

    for price in tooth_hole_data.get("tooth_hole_prices", []):
        sub_category = price.get("sub_category")
        if not sub_category:
            continue

        sub_category = str(sub_category)
        price_value = float(price.get("price", 0) or 0)
        unit = str(price.get("unit", "") or "")
        min_num = price.get("min_num", "")

        if sub_category not in {"through_hole", "blind_hole"}:
            continue

        if "元/小时" in unit:
            price_map[sub_category].append(
                {
                    "hourly_rate": price_value,
                    "unit": unit,
                }
            )
            continue

        if "小时" not in unit:
            continue

        if min_num and str(min_num) != "None":
            match = _MIN_NUM_PATTERN.match(str(min_num))
            if not match:
                logger.warning("Failed to parse min_num format: %s", min_num)
                continue
            condition = match.group(1)
            threshold = int(match.group(2))
            price_map[sub_category].append(
                {
                    "time": price_value,
                    "unit": unit,
                    "condition": condition,
                    "threshold": threshold,
                }
            )
        else:
            price_map[sub_category].append(
                {
                    "time": price_value,
                    "unit": unit,
                    "condition": None,
                    "threshold": None,
                }
            )

    for price in tooth_hole_data.get("screw_prices", []):
        sub_category = price.get("sub_category")
        if not sub_category:
            continue
        price_map["screw"][str(sub_category)] = float(price.get("price", 0) or 0)

    for price in tooth_hole_data.get("stop_screw_prices", []):
        sub_category = price.get("sub_category")
        if not sub_category:
            continue
        price_map["stop_screw"][str(sub_category)] = float(price.get("price", 0) or 0)

    return price_map


def _extract_size_number(size: Any) -> int:
    """Extract a numeric size from values like M8 or m12."""
    try:
        return int(str(size).replace("M", "").replace("m", ""))
    except Exception:
        return 0


def _select_time_rule(rules: Sequence[Mapping[str, Any]], size_number: int) -> tuple[float, str | None]:
    """Select the matching time rule for a hole size."""
    time_per_hole = 0.0
    matched_condition: str | None = None

    for rule in rules:
        if "time" not in rule:
            continue

        condition = rule.get("condition")
        threshold = rule.get("threshold")

        if condition is None:
            if time_per_hole == 0:
                time_per_hole = float(rule["time"])
                matched_condition = "默认"
            continue

        if condition == "<" and size_number < threshold:
            return float(rule["time"]), f"<M{threshold}"
        if condition == ">=" and size_number >= threshold:
            return float(rule["time"]), f">=M{threshold}"
        if condition == "<=" and size_number <= threshold:
            return float(rule["time"]), f"<=M{threshold}"
        if condition == ">" and size_number > threshold:
            return float(rule["time"]), f">M{threshold}"

    return time_per_hole, matched_condition


async def _calculate_part_cost(
    job_id: str,
    part: Mapping[str, Any],
    price_map: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    """Calculate tooth hole cost for a single part."""
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    tooth_hole = part.get("tooth_hole")

    logger.info("Calculating tooth hole cost for part: %s (%s)", part_name, subgraph_id)

    if isinstance(tooth_hole, str):
        try:
            tooth_hole = json.loads(tooth_hole)
        except Exception as exc:  # pragma: no cover - defensive parsing
            logger.error("Failed to parse tooth_hole JSON for %s: %s", part_name, exc)
            tooth_hole = {}

    if not tooth_hole or "tooth_hole_details" not in tooth_hole:
        logger.info("No tooth_hole data for part: %s", part_name)
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "tooth_hole_cost": 0.0,
                "tooth_hole_time_cost": 0.0,
                "total_perimeter": 0.0,
            },
            None,
            None,
        )

    tooth_hole_details = tooth_hole.get("tooth_hole_details", [])
    calculation_steps: list[dict[str, Any]] = []
    total_discharge_cost = 0.0
    total_discharge_time = 0.0
    total_perimeter = 0.0
    perimeter_by_view: dict[str, float] = {}

    for detail in tooth_hole_details:
        code = detail.get("code")
        size = detail.get("size")
        number = detail.get("number", 0) or 0
        is_through = detail.get("is_through") == "t"
        set_screw = detail.get("set_screw") == "t"
        view = detail.get("view", "top_view")

        hole_type = "通孔" if is_through else "盲孔"
        calculation_steps.append(
            {
                "step": "判断孔类型",
                "code": code,
                "size": size,
                "number": number,
                "is_through": is_through,
                "hole_type": hole_type,
                "set_screw": set_screw,
            }
        )

        size_number = _extract_size_number(size)
        hole_category = "through_hole" if is_through else "blind_hole"
        rules = price_map.get(hole_category, [])

        hourly_rate = 0.0
        for rule in rules:
            if "hourly_rate" in rule:
                hourly_rate = float(rule["hourly_rate"])
                break

        time_per_hole, matched_condition = _select_time_rule(rules, size_number)
        if time_per_hole == 0:
            logger.warning("No matching time rule for %s, size_number=%s", hole_category, size_number)
        if hourly_rate == 0:
            logger.warning("No hourly_rate found for %s", hole_category)

        total_time = float(number) * time_per_hole
        discharge_cost = total_time * hourly_rate
        total_discharge_time += total_time
        total_discharge_cost += discharge_cost

        calculation_steps.append(
            {
                "step": "计算放电时间和费用",
                "size": size,
                "size_number": size_number,
                "matched_condition": matched_condition,
                "time_per_hole": time_per_hole,
                "number": number,
                "total_time": round(total_time, 4),
                "hourly_rate": hourly_rate,
                "discharge_cost": round(discharge_cost, 2),
                "formula": f"{number} × {time_per_hole}小时 × {hourly_rate}元/小时 = {round(discharge_cost, 2)}元",
            }
        )

        if is_through:
            if set_screw:
                diameter = float(price_map["stop_screw"].get(str(size), 0) or 0)
                price_source = "stop_screw"
            else:
                diameter = float(price_map["screw"].get(str(size), 0) or 0)
                price_source = "screw"

            perimeter = math.pi * diameter * float(number)
            total_perimeter += perimeter
            perimeter_by_view[view] = perimeter_by_view.get(view, 0.0) + perimeter

            calculation_steps.append(
                {
                    "step": "计算周长（通孔）",
                    "view": view,
                    "size": size,
                    "diameter": diameter,
                    "number": number,
                    "perimeter": round(perimeter, 2),
                    "price_source": price_source,
                    "formula": f"π × {diameter} × {number} = {round(perimeter, 2)}",
                }
            )
        else:
            calculation_steps.append(
                {
                    "step": "盲孔无需计算周长",
                    "note": "盲孔不计算周长",
                }
            )

    calculation_steps.append(
        {
            "step": "费用和时间汇总",
            "total_discharge_time": round(total_discharge_time, 4),
            "total_discharge_cost": round(total_discharge_cost, 2),
            "total_perimeter": round(total_perimeter, 2),
            "perimeter_by_view": {key: round(value, 2) for key, value in perimeter_by_view.items()},
        }
    )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "tooth_hole_cost": round(total_discharge_cost, 2),
        "tooth_hole_time_cost": round(total_discharge_time, 4),
        "total_perimeter": round(total_perimeter, 2),
        "perimeter_by_view": {key: round(value, 2) for key, value in perimeter_by_view.items()},
    }
    db_data_cost = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "tooth_hole_cost": total_discharge_cost,
        "calculation_steps": calculation_steps,
    }
    db_data_time = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "tooth_hole_time_cost": total_discharge_time,
        "calculation_steps": [],
    }

    logger.info(
        "[%s] %s: tooth_hole_cost=%.2f, tooth_hole_time_cost=%.4f, total_perimeter=%.2f",
        subgraph_id,
        part_name,
        total_discharge_cost,
        total_discharge_time,
        total_perimeter,
    )

    return result, db_data_cost, db_data_time


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    """Batch upsert tooth hole calculation details."""
    if not updates:
        return

    sql_template = {
        "tooth_hole_cost": _TOOTH_HOLE_COST_UPSERT_SQL,
        "tooth_hole_time_cost": _TOOTH_HOLE_TIME_UPSERT_SQL,
    }.get(field_name)
    if sql_template is None:
        raise ValueError(f"Unsupported field_name for tooth hole calculator: {field_name}")

    logger.info("Batch updating %s records for category: %s", len(updates), category)
    tasks = [
        _upsert_single_record(
            update["job_id"],
            update["subgraph_id"],
            update["value"],
            category,
            update["steps"],
            sql_template,
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
    field_value: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
    sql_template: str,
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(sql_template, job_id, subgraph_id, str(field_value), category, steps_json)
    return True


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate tooth hole cost for each part in the base itemcode results."""
    base_data = search_data["base_itemcode"]
    tooth_hole_data = search_data["tooth_hole"]

    if not job_id:
        job_id = base_data.get("job_id")

    logger.info(
        "Calculating tooth hole cost for job_id: %s, parts count: %s",
        job_id,
        len(base_data.get("parts", [])),
    )

    price_map = _build_price_map(tooth_hole_data)

    results: list[dict[str, Any]] = []
    db_updates_cost: list[dict[str, Any]] = []
    db_updates_time: list[dict[str, Any]] = []

    for part in base_data.get("parts", []):
        result, db_data_cost, db_data_time = await _calculate_part_cost(job_id, part, price_map)
        results.append(result)
        if db_data_cost:
            db_updates_cost.append(db_data_cost)
        if db_data_time:
            db_updates_time.append(db_data_time)

    if db_updates_cost:
        await batch_upsert_with_steps(
            [
                {
                    "job_id": item["job_id"],
                    "subgraph_id": item["subgraph_id"],
                    "value": item["tooth_hole_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates_cost
            ],
            "tooth_hole",
            "tooth_hole_cost",
        )

    if db_updates_time:
        await batch_upsert_with_steps(
            [
                {
                    "job_id": item["job_id"],
                    "subgraph_id": item["subgraph_id"],
                    "value": item["tooth_hole_time_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates_time
            ],
            "tooth_hole_time",
            "tooth_hole_time_cost",
        )

    logger.info("Completed calculation for %s parts", len(results))
    return {"job_id": job_id, "results": results}


def calculate_sync(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = [
    "MCP_TOOL_META",
    "batch_upsert_with_steps",
    "calculate",
    "calculate_sync",
]
