"""Water mill component pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

_FRACTION_PATTERN = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
_RANGE_PATTERN = re.compile(r"^(\d+)\s*,\s*([\[\(])\s*(\d+)\s*,\s*(\d+|\+|inf|INF|∞)\s*([\]\)])$")

MCP_TOOL_META = {
    "name": "calculate_water_mill_component_price",
    "description": "Calculate water mill component cost from grinding faces and part size.",
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

_COMPONENT_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, component_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        component_cost = EXCLUDED.component_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""


def determine_mill_type(has_auto_material: bool, has_material_preparation: Any) -> str:
    return "s_water_mill" if has_auto_material or has_material_preparation else "l_water_mill"


def determine_part_type(length_mm: float, width_mm: float, thickness_mm: float) -> str:
    dimensions = sorted([length_mm, width_mm, thickness_mm])
    mid_dim = dimensions[1]
    max_dim = dimensions[2]
    if mid_dim > 250:
        return "plate"
    if max_dim >= mid_dim * 2:
        return "long_strip"
    return "component"


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return

    if field_name != "component_cost":
        raise ValueError(f"Unsupported field_name for water mill component calculator: {field_name}")

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
    component_cost: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(_COMPONENT_UPSERT_SQL, job_id, subgraph_id, component_cost, category, steps_json)
    return True


def _parse_price_value(price_value: Any) -> float:
    if price_value is None:
        raise ValueError("Price value is None")
    if isinstance(price_value, (int, float)):
        return float(price_value)

    price_str = str(price_value).strip()
    try:
        return float(price_str)
    except ValueError:
        pass

    match = _FRACTION_PATTERN.match(price_str)
    if match:
        numerator = float(match.group(1))
        denominator = float(match.group(2))
        if denominator == 0:
            raise ValueError("Denominator cannot be zero")
        return numerator / denominator

    raise ValueError(f"Cannot parse price value: {price_str}")


def _parse_min_num(min_num: Any) -> tuple[int | None, dict[str, Any] | None]:
    if not min_num:
        return None, None

    min_num_str = str(min_num).strip()
    match = _RANGE_PATTERN.match(min_num_str)
    if match:
        grinding_faces = int(match.group(1))
        min_val = float(match.group(3))
        max_token = match.group(4)
        max_val = float("inf") if max_token in {"+", "inf", "INF", "∞"} else float(max_token)
        return grinding_faces, {
            "min": min_val,
            "max": max_val,
            "min_inclusive": match.group(2) == "[",
            "max_inclusive": match.group(5) == "]",
        }

    try:
        return int(min_num_str), None
    except ValueError:
        logger.warning("Failed to parse min_num: %s", min_num)
        return None, None


def _build_price_map(water_mill_data: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    price_map: dict[str, list[dict[str, Any]]] = {"grinding_rules": []}

    for price in water_mill_data.get("l_water_mill_prices", []):
        if str(price.get("sub_category")) != "component":
            continue

        try:
            price_float = _parse_price_value(price.get("price"))
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to parse component price: %s, error: %s", price.get("price"), exc)
            continue

        grinding_faces, size_range = _parse_min_num(price.get("min_num", ""))
        if grinding_faces is None:
            continue

        price_map["grinding_rules"].append(
            {
                "grinding_faces": grinding_faces,
                "price": price_float,
                "unit": price.get("unit"),
                "size_range": size_range,
            }
        )

    return price_map


def _in_range(value: float, range_info: Mapping[str, Any]) -> bool:
    if not range_info:
        return False

    min_val = float(range_info["min"])
    max_val = float(range_info["max"])
    if range_info.get("min_inclusive", False):
        if value < min_val:
            return False
    elif value <= min_val:
        return False

    if max_val == float("inf"):
        return True

    if range_info.get("max_inclusive", False):
        return value <= max_val
    return value < max_val


def _get_part_type_reason(dimensions: list[float], part_type: str) -> str:
    min_dim, mid_dim, max_dim = dimensions
    if part_type == "plate":
        return f"mid_dim={mid_dim}mm > 250mm"
    if part_type == "long_strip":
        return f"max_dim={max_dim}mm >= mid_dim={mid_dim}mm * 2"
    return f"dimensions={min_dim},{mid_dim},{max_dim} do not match plate/long_strip"


async def _calculate_part_price(
    job_id: str,
    part: Mapping[str, Any],
    price_map: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    length_mm = float(part.get("length_mm") or 0)
    width_mm = float(part.get("width_mm") or 0)
    thickness_mm = float(part.get("thickness_mm") or 0)
    has_auto_material = part.get("has_auto_material", False)
    has_material_preparation = part.get("has_material_preparation")
    water_mill = part.get("water_mill")

    logger.info("Calculating component cost for part: %s (%s)", part_name, subgraph_id)

    calculation_steps: list[dict[str, Any]] = []
    mill_type = determine_mill_type(has_auto_material, has_material_preparation)
    calculation_steps.append(
        {
            "step": "determine_mill_type",
            "has_auto_material": bool(has_auto_material),
            "has_material_preparation": has_material_preparation,
            "mill_type": mill_type,
        }
    )

    if mill_type != "l_water_mill":
        calculation_steps.append(
            {
                "step": "skip_component_for_small_mill",
                "note": "component cost only applies to large water mill",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "component_cost": 0.0,
                "note": "small water mill does not calculate component cost",
            },
            None,
        )

    part_type = determine_part_type(length_mm, width_mm, thickness_mm)
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

    if part_type != "component":
        calculation_steps.append(
            {
                "step": "skip_non_component_part",
                "note": "part is plate or long_strip",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "part_type": part_type,
                "component_cost": 0.0,
                "note": "part is not component",
            },
            None,
        )

    if isinstance(water_mill, str):
        try:
            water_mill = json.loads(water_mill)
        except Exception as exc:
            logger.error("Failed to parse water_mill JSON for %s: %s", part_name, exc)
            water_mill = {}

    if not water_mill or "water_mill_details" not in water_mill:
        calculation_steps.append({"step": "missing_water_mill_details", "note": "no water_mill_details data"})
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "part_type": part_type,
                "component_cost": 0.0,
                "note": "no water_mill_details data",
            },
            None,
        )

    grinding_value = 0
    for detail in water_mill.get("water_mill_details", []):
        if isinstance(detail, Mapping) and "grinding" in detail:
            grinding_value = int(detail.get("grinding", 0) or 0)
            break

    if grinding_value == 0:
        calculation_steps.append({"step": "missing_grinding_value", "note": "grinding is zero"})
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "part_type": part_type,
                "grinding": grinding_value,
                "component_cost": 0.0,
                "note": "grinding is zero",
            },
            None,
        )

    calculation_steps.append(
        {
            "step": "read_grinding_value",
            "grinding": grinding_value,
        }
    )

    grinding_rules = list(price_map.get("grinding_rules", []))
    if not grinding_rules:
        calculation_steps.append({"step": "missing_grinding_rules", "note": "no component pricing rules"})
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "part_type": part_type,
                "grinding": grinding_value,
                "component_cost": 0.0,
                "note": "no component pricing rules",
            },
            None,
        )

    max_length_width = max(length_mm, width_mm)
    base_rule = None
    for rule in grinding_rules:
        if rule["grinding_faces"] == 6 and rule.get("size_range") and _in_range(max_length_width, rule["size_range"]):
            base_rule = rule
            break

    if not base_rule:
        calculation_steps.append(
            {
                "step": "missing_base_rule",
                "max_length_width": max_length_width,
                "note": "no 6-face base rule matched",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "part_type": part_type,
                "grinding": grinding_value,
                "component_cost": 0.0,
                "note": "no 6-face base rule matched",
            },
            None,
        )

    if grinding_value == 6:
        component_cost = float(base_rule["price"])
        calculation_steps.append(
            {
                "step": "calculate_component_cost",
                "grinding": grinding_value,
                "base_price": component_cost,
                "unit": base_rule.get("unit"),
            }
        )
    else:
        multiplier_rule = None
        for rule in grinding_rules:
            if rule["grinding_faces"] == grinding_value and not rule.get("size_range"):
                multiplier_rule = rule
                break

        if not multiplier_rule:
            calculation_steps.append(
                {
                    "step": "missing_multiplier_rule",
                    "grinding": grinding_value,
                    "note": f"no multiplier rule for {grinding_value}-face grinding",
                }
            )
            return (
                {
                    "subgraph_id": subgraph_id,
                    "part_name": part_name,
                    "mill_type": mill_type,
                    "part_type": part_type,
                    "grinding": grinding_value,
                    "component_cost": 0.0,
                    "note": f"no multiplier rule for {grinding_value}-face grinding",
                },
                None,
            )

        component_cost = float(base_rule["price"]) * float(multiplier_rule["price"])
        calculation_steps.append(
            {
                "step": "calculate_component_cost",
                "grinding": grinding_value,
                "base_price": float(base_rule["price"]),
                "multiplier": float(multiplier_rule["price"]),
                "formula": f"{base_rule['price']} * {multiplier_rule['price']}",
                "component_cost": round(component_cost, 2),
                "unit": "hour",
            }
        )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "mill_type": mill_type,
        "part_type": part_type,
        "grinding": grinding_value,
        "component_cost": round(component_cost, 2),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "component_cost": component_cost,
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

    logger.info(
        "Calculating water mill component cost for job_id: %s, parts count: %s",
        job_id,
        len(parts),
    )

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
                    "value": item["component_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "water_mill_component",
            "component_cost",
        )

    logger.info("Completed calculation for %s parts", len(results))
    return {
        "job_id": job_id,
        "results": results,
    }


def calculate_sync(
    search_data: Dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> Dict[str, Any]:
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "batch_upsert_with_steps", "calculate", "calculate_sync"]
