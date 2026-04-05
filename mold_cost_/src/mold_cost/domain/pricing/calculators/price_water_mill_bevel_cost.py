"""Water mill bevel pricing calculator domain implementation."""

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

MCP_TOOL_META = {
    "name": "calculate_water_mill_bevel_cost",
    "description": "Calculate water mill bevel cost from part data and water mill price rules.",
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

_BEVEL_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, bevel_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        bevel_cost = EXCLUDED.bevel_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""

_RANGE_PATTERN = re.compile(r"([\[\(])(\d+),\s*(\d+|[+\-∞]+)([\]\)])")


def _determine_mill_type(has_auto_material: Any, has_material_preparation: Any) -> str:
    return "s_water_mill" if bool(has_auto_material) or bool(has_material_preparation) else "l_water_mill"


def _parse_range(min_num: Any) -> dict[str, Any] | None:
    if not min_num:
        return None
    match = _RANGE_PATTERN.match(str(min_num))
    if not match:
        return None

    min_bracket, min_value, max_value, max_bracket = match.groups()
    try:
        upper = float("inf") if any(token in str(max_value) for token in ("+", "-", "∞")) else float(max_value)
        return {
            "min": float(min_value),
            "max": upper,
            "min_inclusive": min_bracket == "[",
            "max_inclusive": max_bracket == "]",
        }
    except (TypeError, ValueError):
        return None


def _build_price_map(water_mill_data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    price_map: dict[str, list[dict[str, Any]]] = {"bevel_prices": []}

    for price in water_mill_data.get("s_water_mill_prices", []):
        if price.get("sub_category") != "bevel":
            continue

        try:
            entry: dict[str, Any] = {
                "price": float(price.get("price", 0) or 0),
                "unit": price.get("unit", ""),
            }
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to parse bevel price: %s, error: %s", price.get("price"), exc)
            continue

        range_info = _parse_range(price.get("min_num"))
        if range_info:
            entry.update(range_info)
        price_map["bevel_prices"].append(entry)

    price_map["bevel_prices"].sort(key=lambda item: item["price"])
    return price_map


def _in_range(value: float, range_info: dict[str, Any]) -> bool:
    if "min" not in range_info or "max" not in range_info:
        return False

    min_value = float(range_info["min"])
    max_value = float(range_info["max"])
    if range_info.get("min_inclusive", False):
        if value < min_value:
            return False
    elif value <= min_value:
        return False

    if max_value == float("inf"):
        return True

    if range_info.get("max_inclusive", False):
        return value <= max_value
    return value < max_value


def _get_bevel_unit_price(bevel_count: float, price_map: dict[str, list[dict[str, Any]]]) -> tuple[float, str]:
    bevel_prices = price_map.get("bevel_prices", [])
    if not bevel_prices:
        return 0.0, ""
    if len(bevel_prices) == 1:
        return float(bevel_prices[0]["price"]), str(bevel_prices[0].get("unit", ""))

    for price_info in bevel_prices:
        if _in_range(bevel_count, price_info):
            return float(price_info["price"]), str(price_info.get("unit", ""))

    logger.warning("No matching price range for bevel_count=%s, using first price", bevel_count)
    return float(bevel_prices[0]["price"]), str(bevel_prices[0].get("unit", ""))


async def _calculate_part_price(job_id: str, part: dict[str, Any], price_map: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], dict[str, Any] | None]:
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
            "has_material_preparation": has_material_preparation,
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
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "bevel_cost": 0.0,
                "note": "missing water_mill_details",
            },
            None,
        )

    bevel_data = None
    for detail in water_mill.get("water_mill_details", []):
        if "bevel" in detail:
            bevel_data = detail.get("bevel")
            break

    if not bevel_data:
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "bevel_cost": 0.0,
                "note": "bevel count is empty",
            },
            None,
        )

    bevel_values = [value for value in bevel_data if value] if isinstance(bevel_data, list) else [bevel_data]
    bevel_values = [float(value) for value in bevel_values if float(value) != 0]
    if not bevel_values:
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "bevel_cost": 0.0,
                "note": "bevel count is empty",
            },
            None,
        )

    if mill_type != "s_water_mill":
        calculation_steps.append(
            {
                "step": "skip_large_water_mill",
                "note": "bevel cost only applies to small water mill",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "bevel_values": bevel_values,
                "bevel_details": [],
                "bevel_cost": 0.0,
                "note": "large water mill does not calculate bevel cost",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "bevel_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    total_bevel_cost = 0.0
    bevel_details: list[dict[str, Any]] = []
    for index, bevel_value in enumerate(bevel_values, 1):
        unit_price, unit = _get_bevel_unit_price(bevel_value, price_map)
        price_rule = "<=10" if bevel_value <= 10 else ">10"
        total_bevel_cost += unit_price
        bevel_details.append(
            {
                "index": index,
                "bevel_value": bevel_value,
                "price_rule": price_rule,
                "unit_price": unit_price,
                "unit": unit,
            }
        )
        calculation_steps.append(
            {
                "step": f"calculate_bevel_{index}",
                "bevel_value": bevel_value,
                "price_rule": price_rule,
                "unit_price": unit_price,
                "unit": unit,
            }
        )

    calculation_steps.append(
        {
            "step": "sum_bevel_cost",
            "bevel_values": bevel_values,
            "bevel_details": bevel_details,
            "total_bevel_cost": round(total_bevel_cost, 2),
        }
    )

    return (
        {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "mill_type": mill_type,
            "bevel_values": bevel_values,
            "bevel_details": bevel_details,
            "bevel_cost": round(total_bevel_cost, 2),
        },
        {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "bevel_cost": total_bevel_cost,
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

    if field_name != "bevel_cost":
        raise ValueError(f"Unsupported field_name for water mill bevel calculator: {field_name}")

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
    bevel_cost: Any,
    category: str,
    steps: list[dict[str, Any]],
) -> bool:
    await db.execute(_BEVEL_UPSERT_SQL, job_id, subgraph_id, bevel_cost, category, json.dumps(steps, default=str))
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

    logger.info("Calculating water mill bevel cost for job_id: %s, parts count: %s", job_id, len(parts))

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
                    "value": item["bevel_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "water_mill_bevel",
            "bevel_cost",
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
