"""Water mill long strip pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

_RANGE_PATTERN = re.compile(r"([\[\(])\s*(\d+)\s*,\s*(\d+|[+∞\u221e]+)\s*([\]\)])")

MCP_TOOL_META = {
    "name": "calculate_water_mill_long_strip_price",
    "description": "Calculate water mill long strip cost from part geometry and water mill price ranges.",
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

_LONG_STRIP_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, long_strip_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        long_strip_cost = EXCLUDED.long_strip_cost,
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


def _determine_part_type(length_mm: float, width_mm: float, thickness_mm: float) -> str:
    dimensions = sorted([float(length_mm or 0), float(width_mm or 0), float(thickness_mm or 0)])
    min_dim, mid_dim, max_dim = dimensions

    if mid_dim > 250:
        return "plate"
    if max_dim >= mid_dim * 2:
        return "long_strip"
    return "component"


def _get_part_type_reason(dimensions: list[float], part_type: str) -> str:
    min_dim, mid_dim, max_dim = dimensions
    if part_type == "plate":
        return f"mid_dim={mid_dim}mm > 250mm"
    if part_type == "long_strip":
        return f"max_dim={max_dim}mm >= mid_dim={mid_dim}mm * 2"
    return f"does not satisfy plate or long_strip rules (min={min_dim}, mid={mid_dim}, max={max_dim})"


def _build_price_map(water_mill_data: dict[str, Any]) -> list[dict[str, Any]]:
    price_list: list[dict[str, Any]] = []

    for price in water_mill_data.get("l_water_mill_prices", []):
        if price.get("sub_category") != "long_strip":
            continue

        price_value = price.get("price")
        unit = price.get("unit")
        min_num = price.get("min_num", "")
        if not min_num:
            continue

        match = _RANGE_PATTERN.match(str(min_num))
        if not match:
            logger.warning("Failed to parse long_strip range: %s", min_num)
            continue

        min_bracket, min_value, max_value, max_bracket = match.groups()
        try:
            range_min = float(min_value)
            range_max = float("inf") if any(token in str(max_value) for token in ("+", "∞", "∞")) else float(max_value)
            price_list.append(
                {
                    "price": float(price_value),
                    "range_min": range_min,
                    "range_max": range_max,
                    "min_inclusive": min_bracket == "[",
                    "max_inclusive": max_bracket == "]",
                    "unit": unit,
                }
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to parse long_strip price %s / %s: %s", price_value, min_num, exc)

    price_list.sort(key=lambda item: item["range_min"])
    return price_list


def _in_range(value: float, range_info: dict[str, Any]) -> bool:
    min_val = float(range_info["range_min"])
    max_val = float(range_info["range_max"])
    min_inclusive = bool(range_info.get("min_inclusive", False))
    max_inclusive = bool(range_info.get("max_inclusive", False))

    if min_inclusive:
        if value < min_val:
            return False
    elif value <= min_val:
        return False

    if max_val == float("inf"):
        return True

    if max_inclusive:
        return value <= max_val
    return value < max_val


def _get_unit_price_by_length(max_length: float, price_list: list[dict[str, Any]]) -> tuple[float, str]:
    for price_info in price_list:
        if _in_range(max_length, price_info):
            min_bracket = "[" if price_info["min_inclusive"] else "("
            max_bracket = "]" if price_info["max_inclusive"] else ")"
            max_value = "+" if price_info["range_max"] == float("inf") else price_info["range_max"]
            return float(price_info["price"]), f"{min_bracket}{price_info['range_min']}, {max_value}{max_bracket}"

    if price_list:
        last_price = price_list[-1]
        min_bracket = "[" if last_price["min_inclusive"] else "("
        max_bracket = "]" if last_price["max_inclusive"] else ")"
        max_value = "+" if last_price["range_max"] == float("inf") else last_price["range_max"]
        return float(last_price["price"]), f"{min_bracket}{last_price['range_min']}, {max_value}{max_bracket}"

    return 0.0, "no price data"


async def _calculate_part_price(
    job_id: str,
    part: dict[str, Any],
    price_list: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    length_mm = float(part.get("length_mm") or 0)
    width_mm = float(part.get("width_mm") or 0)
    thickness_mm = float(part.get("thickness_mm") or 0)
    has_auto_material = part.get("has_auto_material", False)
    has_material_preparation = part.get("has_material_preparation")
    quantity = float(part.get("quantity") or 1)

    logger.info("Calculating long strip cost for part: %s (%s)", part_name, subgraph_id)

    calculation_steps: list[dict[str, Any]] = []
    mill_type = _determine_mill_type(has_auto_material, has_material_preparation)
    calculation_steps.append(
        {
            "step": "determine_mill_type",
            "has_auto_material": bool(has_auto_material),
            "has_material_preparation": has_material_preparation,
            "mill_type": mill_type,
            "reason": f"has_auto_material={has_auto_material} or has_material_preparation={has_material_preparation}",
        }
    )

    if mill_type != "l_water_mill":
        calculation_steps.append(
            {
                "step": "skip_non_long_strip",
                "note": "long strip cost only applies to large water mill",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "long_strip_cost": 0.0,
                "note": "小水磨不计算长条费",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "long_strip_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    part_type = _determine_part_type(length_mm, width_mm, thickness_mm)
    dimensions = sorted([length_mm, width_mm, thickness_mm])
    calculation_steps.append(
        {
            "step": "determine_part_type",
            "dimensions": {
                "length_mm": length_mm,
                "width_mm": width_mm,
                "thickness_mm": thickness_mm,
                "sorted": dimensions,
            },
            "part_type": part_type,
            "reason": _get_part_type_reason(dimensions, part_type),
        }
    )

    if part_type != "long_strip":
        calculation_steps.append(
            {
                "step": "skip_non_long_strip_part",
                "part_type": part_type,
                "note": "current part is not long strip",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "part_type": part_type,
                "long_strip_cost": 0.0,
                "note": "不是长条类型",
            },
            None,
        )

    max_length = max(length_mm, width_mm, thickness_mm)
    calculation_steps.append(
        {
            "step": "extract_max_length",
            "length_mm": length_mm,
            "width_mm": width_mm,
            "thickness_mm": thickness_mm,
            "max_length": max_length,
        }
    )

    if max_length == 0:
        calculation_steps.append(
            {
                "step": "skip_zero_max_length",
                "max_length": max_length,
                "note": "max length is zero",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "part_type": part_type,
                "max_length": max_length,
                "long_strip_cost": 0.0,
                "note": "最长边为0，无法计算",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "long_strip_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    unit_price, range_desc = _get_unit_price_by_length(max_length, price_list)
    calculation_steps.append(
        {
            "step": "determine_unit_price",
            "max_length": max_length,
            "range": range_desc,
            "unit_price": unit_price,
            "unit": "小时/件",
        }
    )

    long_strip_cost = unit_price
    calculation_steps.append(
        {
            "step": "calculate_long_strip_cost",
            "unit_price": unit_price,
            "quantity": quantity,
            "long_strip_cost": round(long_strip_cost, 2),
        }
    )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "mill_type": mill_type,
        "part_type": part_type,
        "max_length": max_length,
        "unit_price": unit_price,
        "long_strip_cost": round(long_strip_cost, 2),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "long_strip_cost": long_strip_cost,
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

    if field_name != "long_strip_cost":
        raise ValueError(f"Unsupported field_name for long strip calculator: {field_name}")

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
    long_strip_cost: Any,
    category: str,
    steps: list[dict[str, Any]],
) -> bool:
    await db.execute(_LONG_STRIP_UPSERT_SQL, job_id, subgraph_id, long_strip_cost, category, json.dumps(steps, default=str))
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

    logger.info("Calculating water mill long strip for job_id: %s, parts count: %s", job_id, len(parts))

    price_list = _build_price_map(water_mill_data)
    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []

    for part in parts:
        result, db_data = await _calculate_part_price(job_id, part, price_list)
        results.append(result)
        if db_data:
            db_updates.append(db_data)

    if db_updates:
        await batch_upsert_with_steps(
            [
                {
                    "job_id": item["job_id"],
                    "subgraph_id": item["subgraph_id"],
                    "value": item["long_strip_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "water_mill_long_strip",
            "long_strip_cost",
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
