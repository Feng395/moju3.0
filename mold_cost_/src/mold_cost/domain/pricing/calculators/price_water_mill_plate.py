"""Water mill plate pricing calculator domain implementation."""

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
    "name": "calculate_water_mill_plate_price",
    "description": "Calculate water mill plate cost from part geometry and water mill price rules.",
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

_PLATE_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, plate_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        plate_cost = EXCLUDED.plate_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""


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


def _build_price_map(water_mill_data: Mapping[str, Any]) -> dict[str, Any]:
    price_map = {
        "plate_no_heat": 0.0,
        "plate_heat_45": 0.0,
        "plate_heat_other": 0.0,
        "min_area": 0.0,
    }

    for price in water_mill_data.get("l_water_mill_prices", []):
        if price.get("sub_category") != "plate":
            continue

        try:
            price_value = float(price.get("price", 0) or 0)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to parse plate price: %s, error: %s", price.get("price"), exc)
            continue

        unit = str(price.get("unit", "") or "")
        if unit == "mm2":
            price_map["min_area"] = price_value
        elif "mm2" in unit:
            if price_value == 0.15:
                price_map["plate_no_heat"] = price_value
            elif price_value == 0.17:
                price_map["plate_heat_45"] = price_value
            elif price_value == 0.2:
                price_map["plate_heat_other"] = price_value

    return price_map


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return

    if field_name != "plate_cost":
        raise ValueError(f"Unsupported field_name for water mill plate calculator: {field_name}")

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
    plate_cost: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(_PLATE_UPSERT_SQL, job_id, subgraph_id, plate_cost, category, steps_json)
    return True


async def _calculate_part_price(
    job_id: str,
    part: Mapping[str, Any],
    price_map: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    length_mm = float(part.get("length_mm") or 0)
    width_mm = float(part.get("width_mm") or 0)
    thickness_mm = float(part.get("thickness_mm") or 0)
    has_auto_material = part.get("has_auto_material", False)
    has_material_preparation = part.get("has_material_preparation")
    needs_heat_treatment = part.get("needs_heat_treatment", False)
    material = part.get("material", "")

    logger.info("Calculating plate cost for part: %s (%s)", part_name, subgraph_id)

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
                "step": "skip_non_large_mill",
                "note": "plate cost only applies to large water mill",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "plate_cost": 0.0,
                "note": "小水磨不计算板费",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "plate_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    if length_mm == 0 or width_mm == 0:
        calculation_steps.append(
            {
                "step": "check_dimensions",
                "length_mm": length_mm,
                "width_mm": width_mm,
                "note": "length or width is zero",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "plate_cost": 0.0,
                "note": "闀挎垨瀹戒负0",
            },
            None,
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

    if part_type != "plate":
        calculation_steps.append(
            {
                "step": "skip_non_plate_part",
                "part_type": part_type,
                "note": "current part is not plate",
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "mill_type": mill_type,
                "part_type": part_type,
                "plate_cost": 0.0,
                "note": "涓嶆槸鏉跨被鍨?",
            },
            None,
        )

    if needs_heat_treatment:
        if material == "45#":
            unit_price = float(price_map.get("plate_heat_45", 0) or 0)
            price_type = "闇€瑕佺儹澶勭悊涓旀潗鏂欎负45#"
        else:
            unit_price = float(price_map.get("plate_heat_other", 0) or 0)
            price_type = f"闇€瑕佺儹澶勭悊涓旀潗鏂欎负{material}"
    else:
        unit_price = float(price_map.get("plate_no_heat", 0) or 0)
        price_type = "涓嶉渶瑕佺儹澶勭悊"

    calculation_steps.append(
        {
            "step": "determine_unit_price",
            "needs_heat_treatment": needs_heat_treatment,
            "material": material,
            "unit_price": unit_price,
            "price_type": price_type,
        }
    )

    area = length_mm * width_mm
    min_area = float(price_map.get("min_area", 0) or 0)
    calculation_steps.append(
        {
            "step": "calculate_area",
            "length_mm": length_mm,
            "width_mm": width_mm,
            "area": area,
            "divisor": min_area,
            "note": f"area = {length_mm} * {width_mm} = {area}mm2, divisor = {min_area}mm2",
        }
    )

    if min_area > 0:
        plate_cost = (area / min_area) * unit_price
        calculation_steps.append(
            {
                "step": "calculate_plate_cost",
                "length_mm": length_mm,
                "width_mm": width_mm,
                "area": area,
                "divisor": min_area,
                "unit_price": unit_price,
                "formula": f"({length_mm} * {width_mm}) / {min_area} * {unit_price}",
                "plate_cost": round(plate_cost, 2),
            }
        )
    else:
        plate_cost = 0.0
        calculation_steps.append(
            {
                "step": "calculate_plate_cost",
                "area": area,
                "divisor": min_area,
                "unit_price": unit_price,
                "plate_cost": 0.0,
                "note": "min_area is zero",
            }
        )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "mill_type": mill_type,
        "part_type": part_type,
        "needs_heat_treatment": needs_heat_treatment,
        "material": material,
        "area": area,
        "unit_price": unit_price,
        "plate_cost": round(plate_cost, 2),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "plate_cost": plate_cost,
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

    logger.info("Calculating water mill plate for job_id: %s, parts count: %s", job_id, len(parts))

    price_map = _build_price_map(_parse_water_mill_payload(water_mill_data))
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
                    "value": item["plate_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "water_mill_plate",
            "plate_cost",
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
