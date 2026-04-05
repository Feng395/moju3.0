"""Heat treatment pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MATERIAL_ALIASES = {
    "TOOLOX33": "T00L0X33",
    "TOOLOX44": "T00L0X44",
}

DEFAULT_DENSITY = Decimal("0.00000785")

MCP_TOOL_META = {
    "name": "calculate_heat_treatment_cost",
    "description": "Calculate heat treatment cost from base itemcode, heat price, and density data.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode, heat and density results",
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
    "needs": ["base_itemcode", "heat", "density"],
}

_HEAT_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, heat_treatment_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        heat_treatment_cost = EXCLUDED.heat_treatment_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""


def _build_density_map(density_data: Sequence[Mapping[str, Any]]) -> dict[str, Decimal]:
    density_map: dict[str, Decimal] = {}
    for item in density_data:
        sub_category = item.get("sub_category")
        if not sub_category:
            continue
        density_map[str(sub_category).upper()] = Decimal(str(item.get("price", 0) or 0))
    logger.info("Built density map with %s entries", len(density_map))
    return density_map


def _build_price_map(heat_prices: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    price_map: dict[str, dict[str, Any]] = {}
    for price_item in heat_prices:
        sub_category = price_item.get("sub_category")
        if not sub_category:
            continue
        normalized = str(sub_category).upper()
        price_map[normalized] = {
            "price": float(price_item.get("price", 0) or 0),
            "unit": price_item.get("unit", ""),
            "original_sub_category": sub_category,
        }
    logger.info("Built heat price map with %s entries", len(price_map))
    return price_map


def _get_material_density(material: str, density_map: Mapping[str, Decimal]) -> tuple[Decimal, str]:
    if not material:
        logger.warning("Material is empty, using default density")
        return DEFAULT_DENSITY, "默认钢材"

    material_upper = material.upper()
    if material_upper in MATERIAL_ALIASES:
        mapped_material = MATERIAL_ALIASES[material_upper]
        logger.info("Material alias mapping: %s -> %s", material, mapped_material)
        material_upper = mapped_material

    if material_upper in density_map:
        density = density_map[material_upper]
        logger.info("Found density for material %s: %s", material, density)
        return density, material_upper

    logger.warning("Material %s not found in density map, using default density", material)
    return DEFAULT_DENSITY, f"{material}(使用默认密度)"


def _failure_result(
    *,
    job_id: str,
    subgraph_id: str,
    part_name: str,
    note: str,
    calculation_steps: list[dict[str, Any]],
    needs_heat_treatment: bool,
    material: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "needs_heat_treatment": needs_heat_treatment,
        "heat_treatment_cost": 0.0,
        "note": note,
    }
    if material is not None:
        result["material"] = material
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "heat_treatment_cost": 0.0,
        "calculation_steps": calculation_steps,
    }
    return result, db_data


async def _calculate_part_cost(
    job_id: str,
    part: Mapping[str, Any],
    price_map: Mapping[str, Mapping[str, Any]],
    density_map: Mapping[str, Decimal],
) -> tuple[dict[str, Any], dict[str, Any]]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    needs_heat_treatment = part.get("needs_heat_treatment")
    material = part.get("material")
    length_mm = part.get("length_mm")
    width_mm = part.get("width_mm")
    thickness_mm = part.get("thickness_mm")

    logger.info(
        "Calculating heat treatment cost for part: %s (%s), needs_heat_treatment: %s, material: %s",
        part_name,
        subgraph_id,
        needs_heat_treatment,
        material,
    )

    if not needs_heat_treatment:
        calculation_steps = [
            {
                "step": "判断是否需要热处理",
                "needs_heat_treatment": False,
                "heat_treatment_cost": 0.0,
                "note": "不需要热处理",
            }
        ]
        return _failure_result(
            job_id=job_id,
            subgraph_id=subgraph_id,
            part_name=part_name,
            note="不需要热处理",
            calculation_steps=calculation_steps,
            needs_heat_treatment=False,
            material=material,
        )

    if not all([length_mm, width_mm, thickness_mm]):
        missing = []
        if not length_mm:
            missing.append("length_mm")
        if not width_mm:
            missing.append("width_mm")
        if not thickness_mm:
            missing.append("thickness_mm")

        calculation_steps = [
            {
                "step": "数据验证",
                "status": "failed",
                "needs_heat_treatment": True,
                "reason": f"缺少必需字段: {', '.join(missing)}",
                "missing_fields": missing,
                "heat_treatment_cost": 0.0,
            }
        ]
        return _failure_result(
            job_id=job_id,
            subgraph_id=subgraph_id,
            part_name=part_name,
            note=f"缺少必需字段: {', '.join(missing)}",
            calculation_steps=calculation_steps,
            needs_heat_treatment=True,
            material=material,
        )

    if not material:
        calculation_steps = [
            {
                "step": "数据验证",
                "status": "failed",
                "needs_heat_treatment": True,
                "reason": "material为空",
                "heat_treatment_cost": 0.0,
            }
        ]
        return _failure_result(
            job_id=job_id,
            subgraph_id=subgraph_id,
            part_name=part_name,
            note="material为空",
            calculation_steps=calculation_steps,
            needs_heat_treatment=True,
            material=material,
        )

    material_upper = material.upper()
    original_material = material
    if material_upper in MATERIAL_ALIASES:
        material_mapped = MATERIAL_ALIASES[material_upper]
        logger.info("Material alias mapping: %s -> %s", material, material_mapped)
    else:
        material_mapped = material_upper

    price_info = price_map.get(material_mapped)
    if not price_info:
        calculation_steps = [
            {
                "step": "匹配热处理价格",
                "status": "failed",
                "material": material,
                "mapped_material": material_mapped,
                "reason": f"未找到material对应的热处理价格: {material}",
                "heat_treatment_cost": 0.0,
            }
        ]
        return _failure_result(
            job_id=job_id,
            subgraph_id=subgraph_id,
            part_name=part_name,
            note=f"未找到material对应的热处理价格: {material}",
            calculation_steps=calculation_steps,
            needs_heat_treatment=True,
            material=material,
        )

    unit_price = price_info["price"]
    unit = price_info["unit"]
    matched_sub_category = price_info.get("original_sub_category", material_mapped)
    density, matched_density_material = _get_material_density(material, density_map)

    length = Decimal(str(length_mm))
    width = Decimal(str(width_mm))
    thickness = Decimal(str(thickness_mm))

    weight = (density * length * width * thickness).quantize(Decimal("0.0001"), ROUND_HALF_UP)
    heat_treatment_cost = (weight * Decimal(str(unit_price))).quantize(Decimal("0.01"), ROUND_HALF_UP)

    calculation_steps = [
        {
            "step": "判断是否需要热处理",
            "needs_heat_treatment": True,
        },
        {
            "step": "匹配热处理价格",
            "material": original_material,
            "matched_sub_category": matched_sub_category,
            "match_note": f"不区分大小写匹配: {original_material} -> {matched_sub_category}"
            + (
                f" (别名映射: {material_upper} -> {material_mapped})"
                if material_upper in MATERIAL_ALIASES
                else ""
            ),
            "unit_price": unit_price,
            "unit": unit,
        },
        {
            "step": "匹配材料密度",
            "material": original_material,
            "matched_material": matched_density_material,
            "density": float(density),
            "unit": "g/cm³",
        },
        {
            "step": "获取尺寸数据",
            "length_mm": float(length_mm),
            "width_mm": float(width_mm),
            "thickness_mm": float(thickness_mm),
        },
        {
            "step": "计算重量",
            "formula": f"{density} * {length_mm} * {width_mm} * {thickness_mm}",
            "weight": float(weight),
        },
        {
            "step": "计算热处理费",
            "formula": f"{float(weight)} * {unit_price}",
            "heat_treatment_cost": float(heat_treatment_cost),
        },
    ]

    logger.info(
        "[%s] %s: material=%s, weight=%s, unit_price=%s, heat_treatment_cost=%s",
        subgraph_id,
        part_name,
        original_material,
        weight,
        unit_price,
        heat_treatment_cost,
    )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "needs_heat_treatment": True,
        "material": original_material,
        "length_mm": float(length_mm),
        "width_mm": float(width_mm),
        "thickness_mm": float(thickness_mm),
        "weight": float(weight),
        "unit_price": unit_price,
        "unit": unit,
        "heat_treatment_cost": float(heat_treatment_cost),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "heat_treatment_cost": float(heat_treatment_cost),
        "calculation_steps": calculation_steps,
    }
    return result, db_data


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    """Batch upsert calculation details for this calculator."""
    if not updates:
        return

    if field_name != "heat_treatment_cost":
        raise ValueError(f"Unsupported field_name for heat calculator: {field_name}")

    logger.info("Batch updating %s records for category: %s", len(updates), category)
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
    field_value: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(_HEAT_UPSERT_SQL, job_id, subgraph_id, field_value, category, steps_json)
    return True


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_data = search_data["base_itemcode"]
    heat_data = search_data["heat"]
    density_data = search_data["density"]

    if not job_id:
        job_id = base_data.get("job_id")

    logger.info(
        "Calculating heat treatment cost for job_id: %s, parts count: %s",
        job_id,
        len(base_data.get("parts", [])),
    )

    density_map = _build_density_map(density_data.get("density_data", []))
    price_map = _build_price_map(heat_data.get("heat_prices", []))

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []
    for part in base_data["parts"]:
        result, db_data = await _calculate_part_cost(job_id, part, price_map, density_map)
        results.append(result)
        db_updates.append(db_data)

    if db_updates:
        updates_for_batch = [
            {
                "job_id": item["job_id"],
                "subgraph_id": item["subgraph_id"],
                "value": item["heat_treatment_cost"],
                "steps": item["calculation_steps"],
            }
            for item in db_updates
        ]
        await batch_upsert_with_steps(updates_for_batch, "heat", "heat_treatment_cost")

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
    "MATERIAL_ALIASES",
    "DEFAULT_DENSITY",
    "batch_upsert_with_steps",
    "calculate",
    "calculate_sync",
]
