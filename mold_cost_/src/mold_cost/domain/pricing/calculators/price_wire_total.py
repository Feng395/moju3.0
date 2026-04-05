"""Wire total pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Any, Dict, List

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "calculate_total_cost",
    "description": "计算总价：单价 × 数量，更新到 subgraphs 表",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "检索数据，包含 base_itemcode 和 total",
            },
            "job_id": {
                "type": "string",
                "description": "任务ID (UUID)",
            },
            "subgraph_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "子图ID列表",
            },
        },
        "required": ["search_data"],
    },
    "handler": "calculate",
    "needs": ["base_itemcode", "total"],
}

_WIRE_TYPE_ALIASES = {
    "slow": "慢丝",
    "mid": "中丝",
    "medium": "中丝",
    "middle": "中丝",
    "fast": "快丝",
    "慢丝": "慢丝",
    "中丝": "中丝",
    "快丝": "快丝",
}


async def calculate(
    search_data: Dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: List[str] | None = None,
) -> Dict[str, Any]:
    """Calculate wire-related total costs and persist the calculation steps."""
    base_data = search_data["base_itemcode"]
    total_data = search_data["total"]

    if not job_id:
        job_id = base_data.get("job_id")

    logger.info(
        "Calculating wire total cost for job_id: %s, parts count: %s",
        job_id,
        len(base_data.get("parts", [])),
    )

    quantity_map = {
        part["subgraph_id"]: part.get("quantity", 1)
        for part in base_data.get("parts", [])
    }
    metadata_map = {
        part["subgraph_id"]: part.get("metadata", {})
        for part in base_data.get("parts", [])
    }
    cost_map = {
        detail["subgraph_id"]: detail
        for detail in total_data.get("cost_details", [])
    }

    results: List[Dict[str, Any]] = []
    db_updates: List[Dict[str, Any]] = []

    for part in base_data.get("parts", []):
        result, db_data = await _calculate_part_total(
            part=part,
            quantity_map=quantity_map,
            metadata_map=metadata_map,
            cost_map=cost_map,
        )
        results.append(result)
        if db_data:
            db_updates.append(db_data)

    if db_updates:
        await _batch_update_subgraphs(job_id, db_updates)
        await batch_upsert_with_steps(
            [
                {
                    "job_id": job_id,
                    "subgraph_id": data["subgraph_id"],
                    "value": None,
                    "steps": data["calculation_steps"],
                }
                for data in db_updates
            ],
            "wire_total",
            None,
        )

    logger.info("Completed wire total calculation for %s parts", len(results))
    return {
        "job_id": job_id,
        "results": results,
    }


async def _calculate_part_total(
    part: Dict[str, Any],
    quantity_map: Dict[str, Any],
    metadata_map: Dict[str, Any],
    cost_map: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Calculate the wire total for a single part."""
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    quantity = quantity_map.get(subgraph_id, 1)
    metadata = metadata_map.get(subgraph_id, {})
    costs = cost_map.get(subgraph_id, {})

    logger.info(
        "Calculating wire total for part: %s (%s), quantity: %s",
        part_name,
        subgraph_id,
        quantity,
    )

    weight = costs.get("weight", 0.0)
    material_cost = costs.get("material_cost", 0.0)
    heat_treatment_cost = costs.get("heat_treatment_cost", 0.0)
    material_additional_cost = costs.get("material_additional_cost", 0.0)
    basic_processing_cost = costs.get("basic_processing_cost", 0.0)
    special_base_cost = costs.get("special_base_cost", 0.0)
    standard_base_cost = costs.get("standard_base_cost", 0.0)
    tooth_hole_cost = costs.get("tooth_hole_cost", 0.0)
    tooth_hole_time_cost = costs.get("tooth_hole_time_cost", 0.0)
    calculation_steps = costs.get("calculation_steps", [])

    weight_kg = float(Decimal(str(weight)) * Decimal(str(quantity)))
    material_cost_total = float(Decimal(str(material_cost)) * Decimal(str(quantity)))
    heat_treatment_cost_total = float(Decimal(str(heat_treatment_cost)) * Decimal(str(quantity)))
    material_additional_cost_total = float(material_additional_cost)

    wire_cost_base = max(basic_processing_cost, special_base_cost, standard_base_cost)
    if wire_cost_base == basic_processing_cost:
        wire_cost_source = "basic_processing_cost"
    elif wire_cost_base == special_base_cost:
        wire_cost_source = "special_base_cost"
    else:
        wire_cost_source = "standard_base_cost"

    wire_cost_per_unit = wire_cost_base + material_additional_cost
    wire_type = _extract_wire_type(calculation_steps)

    slow_wire_cost = 0.0
    mid_wire_cost = 0.0
    fast_wire_cost = 0.0
    if wire_type == "慢丝":
        slow_wire_cost = float(Decimal(str(wire_cost_per_unit)) * Decimal(str(quantity)))
    elif wire_type == "中丝":
        mid_wire_cost = float(Decimal(str(wire_cost_per_unit)) * Decimal(str(quantity)))
    else:
        fast_wire_cost = float(Decimal(str(wire_cost_per_unit)) * Decimal(str(quantity)))

    material_unit_price = _extract_unit_price(calculation_steps, "material")
    heat_treatment_unit_price = _extract_unit_price(calculation_steps, "heat")
    wire_length = _extract_wire_length(metadata)

    slow_wire_length = wire_length if wire_type == "慢丝" else 0.0
    mid_wire_length = wire_length if wire_type == "中丝" else 0.0
    fast_wire_length = wire_length if wire_type == "快丝" or wire_type not in {"慢丝", "中丝"} else 0.0

    wire_total_calculation_steps = [
        {
            "step": "获取单价数据",
            "weight": weight,
            "material_cost": material_cost,
            "heat_treatment_cost": heat_treatment_cost,
            "material_additional_cost": material_additional_cost,
            "basic_processing_cost": basic_processing_cost,
            "special_base_cost": special_base_cost,
            "standard_base_cost": standard_base_cost,
        },
        {
            "step": "计算线割基础费用",
            "formula": f"max({basic_processing_cost}, {special_base_cost}, {standard_base_cost})",
            "basic_processing_cost": basic_processing_cost,
            "special_base_cost": special_base_cost,
            "standard_base_cost": standard_base_cost,
            "selected": wire_cost_source,
            "wire_cost_base": wire_cost_base,
        },
        {
            "step": "计算线割单价",
            "formula": f"{wire_cost_base} + {material_additional_cost}",
            "wire_cost_base": wire_cost_base,
            "material_additional_cost": material_additional_cost,
            "wire_cost_per_unit": wire_cost_per_unit,
        },
        {
            "step": "确定线割类型",
            "wire_type": wire_type,
        },
        {
            "step": "计算线割总价",
            "formula": f"{wire_cost_per_unit} * {quantity}",
            "wire_cost_per_unit": wire_cost_per_unit,
            "quantity": quantity,
            "slow_wire_cost": slow_wire_cost,
            "mid_wire_cost": mid_wire_cost,
            "fast_wire_cost": fast_wire_cost,
        },
        {
            "step": "计算其他总价",
            "weight_kg": weight_kg,
            "material_cost_total": material_cost_total,
            "heat_treatment_cost_total": heat_treatment_cost_total,
            "formulas": {
                "weight_kg": f"{weight} * {quantity}",
                "material_cost": f"{material_cost} * {quantity}",
                "heat_treatment_cost": f"{heat_treatment_cost} * {quantity}",
            },
        },
        {
            "step": "提取单价和长度",
            "material_unit_price": material_unit_price,
            "heat_treatment_unit_price": heat_treatment_unit_price,
            "wire_length": wire_length,
            "slow_wire_length": slow_wire_length,
            "mid_wire_length": mid_wire_length,
            "fast_wire_length": fast_wire_length,
        },
    ]

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "quantity": quantity,
        "weight_kg": weight_kg,
        "material_cost": material_cost_total,
        "heat_treatment_cost": heat_treatment_cost_total,
        "material_additional_cost": material_additional_cost_total,
        "slow_wire_cost": slow_wire_cost,
        "mid_wire_cost": mid_wire_cost,
        "fast_wire_cost": fast_wire_cost,
        "material_unit_price": material_unit_price,
        "heat_treatment_unit_price": heat_treatment_unit_price,
        "slow_wire_length": slow_wire_length,
        "mid_wire_length": mid_wire_length,
        "fast_wire_length": fast_wire_length,
        "wire_type": wire_type,
        "wire_cost_source": wire_cost_source,
        "edm_time": tooth_hole_time_cost,
        "edm_cost": tooth_hole_cost,
    }

    db_data = {
        "subgraph_id": subgraph_id,
        "weight_kg": weight_kg,
        "material_cost": material_cost_total,
        "heat_treatment_cost": heat_treatment_cost_total,
        "slow_wire_cost": slow_wire_cost,
        "mid_wire_cost": mid_wire_cost,
        "fast_wire_cost": fast_wire_cost,
        "material_unit_price": material_unit_price,
        "heat_treatment_unit_price": heat_treatment_unit_price,
        "slow_wire_length": slow_wire_length,
        "mid_wire_length": mid_wire_length,
        "fast_wire_length": fast_wire_length,
        "edm_time": tooth_hole_time_cost,
        "edm_cost": tooth_hole_cost,
        "calculation_steps": wire_total_calculation_steps,
    }

    logger.info(
        "[%s] %s: quantity=%s, weight_kg=%.3f, material_cost=%.2f, heat_treatment_cost=%.2f, "
        "wire_type=%s, wire_cost_source=%s, wire_cost_per_unit=%.2f",
        subgraph_id,
        part_name,
        quantity,
        weight_kg,
        material_cost_total,
        heat_treatment_cost_total,
        wire_type,
        wire_cost_source,
        wire_cost_per_unit,
    )

    return result, db_data


def _extract_wire_type(calculation_steps: List[Dict[str, Any]]) -> str:
    """Extract and normalize wire type from calculation steps."""
    for step_category in calculation_steps:
        if not isinstance(step_category, dict):
            continue
        category = step_category.get("category", "")
        if category not in {"wire_special", "wire_speci", "wire_base"}:
            continue
        for step in step_category.get("steps", []):
            if not isinstance(step, dict):
                continue
            if "wire_type" not in step and "判断线割类型" not in step.get("step", ""):
                continue
            raw_wire_type = str(step.get("wire_type", "")).strip()
            if raw_wire_type:
                return _WIRE_TYPE_ALIASES.get(raw_wire_type, raw_wire_type)
    return ""


def _extract_unit_price(calculation_steps: List[Dict[str, Any]], category_name: str) -> float:
    """Extract unit price from calculation steps."""
    for step_category in calculation_steps:
        if not isinstance(step_category, dict):
            continue
        if step_category.get("category", "") != category_name:
            continue
        for step in step_category.get("steps", []):
            if not isinstance(step, dict):
                continue
            if "匹配材料" in step.get("step", ""):
                unit_price = step.get("unit_price", 0.0)
                if unit_price:
                    return float(unit_price)
    return 0.0


def _extract_wire_length(metadata: Dict[str, Any]) -> float:
    """Extract wire cutting length from metadata.wire_cut_details."""
    if not metadata:
        return 0.0
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            logger.warning("Failed to parse metadata as JSON")
            return 0.0
    if not isinstance(metadata, dict):
        return 0.0

    total_length = 0.0
    for detail in metadata.get("wire_cut_details", []):
        if not isinstance(detail, dict):
            continue
        if detail.get("view") in {"top_view", "side_view", "front_view"}:
            length = detail.get("total_length", 0.0)
            if length:
                total_length += float(length)
    return total_length


async def _batch_update_subgraphs(job_id: str, updates: List[Dict[str, Any]]) -> None:
    """Persist wire total fields on the subgraphs table."""
    logger.info("Batch updating %s wire total records", len(updates))
    sql = """
        UPDATE subgraphs
        SET
            weight_kg = $3,
            material_cost = $4,
            heat_treatment_cost = $5,
            slow_wire_cost = $6,
            mid_wire_cost = $7,
            fast_wire_cost = $8,
            material_unit_price = $9,
            heat_treatment_unit_price = $10,
            slow_wire_length = $11,
            mid_wire_length = $12,
            fast_wire_length = $13,
            edm_time = $14,
            edm_cost = $15,
            updated_at = NOW()
        WHERE job_id = $1::uuid AND subgraph_id = $2::text
    """

    tasks = [
        db.execute(
            sql,
            job_id,
            data["subgraph_id"],
            data["weight_kg"],
            data["material_cost"],
            data["heat_treatment_cost"],
            data["slow_wire_cost"],
            data["mid_wire_cost"],
            data["fast_wire_cost"],
            data["material_unit_price"],
            data["heat_treatment_unit_price"],
            data["slow_wire_length"],
            data["mid_wire_length"],
            data["fast_wire_length"],
            data["edm_time"],
            data["edm_cost"],
        )
        for data in updates
    ]
    if tasks:
        await asyncio.gather(*tasks)


async def batch_upsert_with_steps(
    updates: List[Dict[str, Any]],
    category: str,
    field_name: str | None,
) -> None:
    """Local clone of the generic calculation-step batch upsert helper."""
    if not updates:
        return

    logger.info("Batch updating %s records for category: %s", len(updates), category)
    tasks = [
        _upsert_single_record(
            data["job_id"],
            data["subgraph_id"],
            field_name,
            data.get("value"),
            category,
            data["steps"],
        )
        for data in updates
    ]
    await asyncio.gather(*tasks, return_exceptions=False)


async def _upsert_single_record(
    job_id: str,
    subgraph_id: str,
    field_name: str | None,
    field_value: Any,
    category: str,
    steps: List[Dict[str, Any]],
) -> bool:
    """Persist calculation steps into processing_cost_calculation_details."""
    steps_json = json.dumps(steps, default=str)
    sql = """
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

    await db.execute(sql, job_id, subgraph_id, category, steps_json)
    return True


def calculate_sync(
    search_data: Dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: List[str] | None = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for compatibility."""
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "batch_upsert_with_steps", "calculate", "calculate_sync"]
