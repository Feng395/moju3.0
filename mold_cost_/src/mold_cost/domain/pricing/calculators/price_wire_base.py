"""Wire base pricing calculator domain implementation."""

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

_RANGE_PATTERN = re.compile(r"([\[\(])\s*(\d+)\s*,\s*([^\]\)]+)\s*([\]\)])")

MCP_TOOL_META = {
    "name": "calculate_wire_base_price",
    "description": "Calculate wire base processing cost from part geometry, wire process rules and optional tooth hole perimeter.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode, wire_base and optional tooth_hole results",
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
    "needs": ["base_itemcode", "wire_base"],
    "optional": ["tooth_hole"],
}

_WIRE_BASE_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, basic_processing_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        basic_processing_cost = EXCLUDED.basic_processing_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""


def _build_rule_map(rule_prices: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rule_map: dict[str, Any] = {"area_num_length": 0.0}

    for rule in rule_prices:
        sub_category = rule.get("sub_category")
        if not sub_category:
            continue

        price_value = rule.get("price")
        min_num = rule.get("min_num")

        if sub_category == "area_num":
            try:
                rule_map["area_num_length"] = float(price_value)
            except (TypeError, ValueError) as exc:
                logger.warning("Failed to parse area_num length: %s, error: %s", price_value, exc)
            continue

        if price_value is None:
            logger.warning("Skipping rule with None price for sub_category: %s", sub_category)
            continue

        if not min_num:
            logger.warning("Skipping rule without min_num for sub_category: %s", sub_category)
            continue

        match = _RANGE_PATTERN.match(str(min_num))
        if not match:
            logger.warning("Invalid min_num format for %s: %s", sub_category, min_num)
            continue

        min_bracket, min_value, max_value, max_bracket = match.groups()
        try:
            min_float = float(min_value)
            if any(token in str(max_value) for token in ("+", "∞", "inf", "INF", "无", "不限")):
                max_float = float("inf")
            else:
                max_float = float(max_value)
            multiplier = float(price_value)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to parse rule for %s, min_num=%s, error: %s", sub_category, min_num, exc)
            continue

        rule_map.setdefault(str(sub_category), []).append(
            {
                "min": min_float,
                "max": max_float,
                "min_inclusive": min_bracket == "[",
                "max_inclusive": max_bracket == "]",
                "multiplier": multiplier,
            }
        )

    return rule_map


def _build_tooth_hole_perimeter_map(tooth_hole_data: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    perimeter_map: dict[str, dict[str, float]] = {}
    if not tooth_hole_data:
        return perimeter_map

    for result in tooth_hole_data.get("results", []):
        if not isinstance(result, Mapping):
            continue
        subgraph_id = result.get("subgraph_id")
        perimeter_by_view = result.get("perimeter_by_view", {})
        if subgraph_id and isinstance(perimeter_by_view, Mapping):
            perimeter_map[str(subgraph_id)] = {
                str(view): float(value or 0) for view, value in perimeter_by_view.items()
            }
    return perimeter_map


def _get_dimension_by_view(view: str, length_mm: float, width_mm: float, thickness_mm: float) -> tuple[float, str]:
    min_dimension = 15.0
    if view == "top_view":
        return max(float(thickness_mm or 0), min_dimension), "thickness_mm"
    if view == "front_view":
        return max(float(width_mm or 0), min_dimension), "width_mm"
    if view == "side_view":
        return max(float(length_mm or 0), min_dimension), "length_mm"
    return 0.0, "unknown"


def _in_range(value: float, range_info: Mapping[str, Any]) -> bool:
    if not range_info:
        return False

    min_value = float(range_info["min"])
    max_value = float(range_info["max"])
    min_inclusive = bool(range_info["min_inclusive"])
    max_inclusive = bool(range_info["max_inclusive"])

    if min_inclusive:
        if value < min_value:
            return False
    elif value <= min_value:
        return False

    if max_value == float("inf"):
        return True

    if max_inclusive:
        return value <= max_value
    return value < max_value


def _apply_extra_thick_rule(dimension: float, rule_map: Mapping[str, Any]) -> tuple[float, str]:
    for rule in rule_map.get("extra_thick", []):
        if _in_range(dimension, rule):
            multiplier = float(rule["multiplier"])
            min_bracket = "[" if rule["min_inclusive"] else "("
            max_bracket = "]" if rule["max_inclusive"] else ")"
            max_value = "+" if rule["max"] == float("inf") else rule["max"]
            return multiplier, f"尺寸{dimension}在{min_bracket}{rule['min']},{max_value}{max_bracket}区间，乘{multiplier}"
    return 1.0, ""


def _apply_slider_rule(slider_angle: float, rule_map: Mapping[str, Any]) -> tuple[float, str]:
    for rule in rule_map.get("slider", []):
        if _in_range(slider_angle, rule):
            multiplier = float(rule["multiplier"])
            min_bracket = "[" if rule["min_inclusive"] else "("
            max_bracket = "]" if rule["max_inclusive"] else ")"
            max_value = "+" if rule["max"] == float("inf") else rule["max"]
            return multiplier, f"slider_angle={slider_angle}在{min_bracket}{rule['min']},{max_value}{max_bracket}区间，乘{multiplier}"
    return 1.0, ""


def _build_total_length_note(
    original_length: float,
    area_num: int,
    area_num_length_per_unit: float,
    tooth_hole_length: float,
    total_length: float,
) -> str:
    parts = [str(original_length)]
    if area_num > 0 and area_num_length_per_unit > 0:
        parts.append(f"({area_num} × {area_num_length_per_unit})")
    if tooth_hole_length > 0:
        parts.append(f"{round(tooth_hole_length, 4)}")
    if len(parts) == 1:
        return parts[0]
    return " + ".join(parts) + f" = {round(total_length, 4)}"


async def _calculate_part_price(
    job_id: str,
    part: Mapping[str, Any],
    wire_map: Mapping[str, Any],
    rule_map: Mapping[str, Any],
    tooth_hole_perimeter_map: Mapping[str, Mapping[str, float]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    wire_process = part.get("wire_process")
    length_mm = part.get("length_mm")
    width_mm = part.get("width_mm")
    thickness_mm = part.get("thickness_mm")
    metadata = part.get("metadata")
    has_auto_material = part.get("has_auto_material", False)
    needs_heat_treatment = part.get("needs_heat_treatment", False)

    logger.info("Calculating wire base for part: %s (%s), wire_process: %s", part_name, subgraph_id, wire_process)

    tooth_hole_perimeter_by_view: dict[str, float] = {}
    if has_auto_material and needs_heat_treatment:
        tooth_hole_perimeter_by_view = dict(tooth_hole_perimeter_map.get(str(subgraph_id), {}))

    wire_part = None
    status = "ok"
    if not wire_process:
        logger.warning("wire_process is empty for part: %s, using default fast_cut", part_name)
        wire_part = wire_map.get("fast_cut")
        status = "error"
    else:
        wire_part = wire_map.get(str(wire_process))
        if not wire_part:
            logger.warning("No wire process found for %s, using default fast_cut", wire_process)
            wire_part = wire_map.get("fast_cut")
            status = "error"

    if not wire_part:
        logger.error("Default fast_cut not found in wire_map for part: %s", part_name)
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "error": "未找到工艺且默认工艺fast_cut也不存在",
            },
            None,
        )

    unit_price = float(wire_part["price"])
    process_description = wire_part["description"]
    conditions = wire_part["conditions"]

    if not metadata:
        calculation_steps = [
            {
                "step": "检查metadata",
                "note": "metadata为空，跳过线割基础价格计算",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "basic_processing_cost": 0.0,
                "note": "metadata为空，跳过计算",
                "process_description": process_description,
                "conditions": conditions,
                "status": "error",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "basic_processing_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception as exc:
            calculation_steps = [
                {
                    "step": "解析metadata",
                    "status": "failed",
                    "reason": f"JSON解析失败: {exc}",
                }
            ]
            return (
                {
                    "subgraph_id": subgraph_id,
                    "part_name": part_name,
                    "basic_processing_cost": 0.0,
                    "note": f"metadata JSON解析失败: {exc}",
                    "process_description": process_description,
                    "conditions": conditions,
                    "status": "error",
                },
                {
                    "job_id": job_id,
                    "subgraph_id": subgraph_id,
                    "basic_processing_cost": 0.0,
                    "calculation_steps": calculation_steps,
                },
            )

    if not isinstance(metadata, dict):
        calculation_steps = [
            {
                "step": "检查metadata类型",
                "note": "metadata不是字典类型，跳过线割基础价格计算",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "basic_processing_cost": 0.0,
                "note": "metadata类型错误，跳过计算",
                "process_description": process_description,
                "conditions": conditions,
                "status": "error",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "basic_processing_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    if "wire_cut_details" not in metadata:
        calculation_steps = [
            {
                "step": "检查wire_cut_details",
                "note": "metadata中缺少wire_cut_details，跳过计算",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "basic_processing_cost": 0.0,
                "note": "metadata中缺少wire_cut_details，跳过计算",
                "process_description": process_description,
                "conditions": conditions,
                "status": "error",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "basic_processing_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    wire_cut_details = metadata["wire_cut_details"]
    area_num_length_per_unit = float(rule_map.get("area_num_length", 0) or 0)
    calculation_steps: list[dict[str, Any]] = []

    if tooth_hole_perimeter_by_view:
        calculation_steps.append(
            {
                "step": "牙孔周长（将加到对应视图）",
                "has_auto_material": has_auto_material,
                "needs_heat_treatment": needs_heat_treatment,
                "perimeter_by_view": tooth_hole_perimeter_by_view,
            }
        )

    view_totals: dict[str, float] = {}
    view_cone_flags: dict[str, bool] = {}

    for detail in wire_cut_details:
        if not isinstance(detail, Mapping):
            continue

        code = detail.get("code")
        view = detail.get("view")
        original_total_length = float(detail.get("total_length", 0) or 0)
        slider_angle = float(detail.get("slider_angle", 0) or 0)
        instruction = detail.get("instruction", "")
        area_num = int(detail.get("area_num", 0) or 0)
        cone = detail.get("cone", "f")

        if view and cone == "t":
            view_cone_flags[str(view)] = True

        added_length = area_num * area_num_length_per_unit if area_num and area_num_length_per_unit else 0.0
        tooth_hole_length = tooth_hole_perimeter_by_view.get(str(view), 0.0) if view else 0.0
        total_length = original_total_length + added_length + tooth_hole_length

        if not view or original_total_length == 0:
            calculation_steps.append(
                {
                    "code": code,
                    "view": view,
                    "status": "跳过",
                    "reason": "view为空或total_length为0",
                }
            )
            continue

        dimension, dimension_name = _get_dimension_by_view(str(view), length_mm, width_mm, thickness_mm)
        original_dimension = {
            "thickness_mm": thickness_mm,
            "width_mm": width_mm,
            "length_mm": length_mm,
        }.get(dimension_name, 0)

        if slider_angle:
            base_price = total_length * unit_price
            base_calculation_formula = f"{round(total_length, 4)} * {unit_price}"
            calculation_note = "slider_angle不为空，不乘尺寸"
        else:
            base_price = total_length * dimension * unit_price
            base_calculation_formula = f"{round(total_length, 4)} * {dimension} * {unit_price}"
            calculation_note = "常规计算"

        view_dimension_mapping = {
            "top_view": "俯视图使用厚度(thickness_mm)",
            "front_view": "主视图使用宽度(width_mm)",
            "side_view": "侧视图使用长度(length_mm)",
        }

        step = {
            "code": code,
            "view": view,
            "instruction": instruction,
            "cone": cone,
            "slider_angle": slider_angle,
            "original_total_length": original_total_length,
            "area_num": area_num,
            "added_length": round(added_length, 4) if added_length > 0 else 0,
            "tooth_hole_length": round(tooth_hole_length, 4) if tooth_hole_length > 0 else 0,
            "total_length": round(total_length, 4),
            "total_length_note": _build_total_length_note(
                original_total_length,
                area_num,
                area_num_length_per_unit,
                tooth_hole_length,
                total_length,
            ),
            "original_dimension": original_dimension,
            "dimension": dimension,
            "dimension_name": dimension_name,
            "dimension_note": f"原始{original_dimension}mm，按{dimension}mm计算" if float(original_dimension or 0) < 15 else f"{dimension}mm",
            "view_dimension_note": view_dimension_mapping.get(str(view), "未知视图"),
            "unit_price": unit_price,
            "calculation_note": calculation_note,
            "base_calculation": f"{base_calculation_formula} = {round(base_price, 4)}",
            "base_price": round(base_price, 4),
            "multipliers": [],
            "calculation_formula": base_calculation_formula,
        }

        final_price = float(base_price)
        formula_parts = [base_calculation_formula]

        extra_thick_mult, extra_thick_desc = _apply_extra_thick_rule(dimension, rule_map)
        if extra_thick_mult != 1.0:
            final_price *= extra_thick_mult
            formula_parts.append(f"* {extra_thick_mult}")
            step["multipliers"].append(
                {
                    "type": "extra_thick",
                    "multiplier": extra_thick_mult,
                    "description": extra_thick_desc,
                }
            )

        slider_mult, slider_desc = _apply_slider_rule(slider_angle, rule_map)
        if slider_mult != 1.0:
            final_price *= slider_mult
            formula_parts.append(f"* {slider_mult}")
            step["multipliers"].append(
                {
                    "type": "slider",
                    "multiplier": slider_mult,
                    "description": slider_desc,
                }
            )

        step["final_price"] = round(final_price, 4)
        step["complete_formula"] = " ".join(formula_parts) + f" = {round(final_price, 4)}"
        step[f"{code}_price"] = round(final_price, 4)
        calculation_steps.append(step)

        view_totals[str(view)] = view_totals.get(str(view), 0.0) + final_price

    view_totals_after_cone = {
        view: total * 1.5 if view_cone_flags.get(view, False) else total
        for view, total in view_totals.items()
    }
    basic_processing_cost = sum(view_totals_after_cone.values())

    calculation_steps.append(
        {
            "step": "视图汇总（应用cone规则前）",
            "view_totals": {key: round(value, 4) for key, value in view_totals.items()},
        }
    )
    if any(view_cone_flags.values()):
        cone_details = [
            {
                "view": view,
                "before_cone": round(view_totals[view], 4),
                "after_cone": round(view_totals_after_cone[view], 4),
                "multiplier": 1.5,
            }
            for view in view_totals
            if view_cone_flags.get(view, False)
        ]
        calculation_steps.append({"step": "应用视图级别cone规则", "cone_details": cone_details})
    calculation_steps.append(
        {
            "step": "视图汇总（应用cone规则后）",
            "view_totals_after_cone": {key: round(value, 4) for key, value in view_totals_after_cone.items()},
        }
    )
    calculation_steps.append(
        {
            "step": "最终总价",
            "basic_processing_cost": round(basic_processing_cost, 4),
        }
    )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "process_description": process_description,
        "conditions": conditions,
        "basic_processing_cost": round(basic_processing_cost, 4),
        "status": status,
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "basic_processing_cost": basic_processing_cost,
        "calculation_steps": calculation_steps,
    }
    return result, db_data


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    """Batch upsert calculation details for wire base."""
    if not updates:
        return

    if field_name != "basic_processing_cost":
        raise ValueError(f"Unsupported field_name for wire base calculator: {field_name}")

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
    basic_processing_cost: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(_WIRE_BASE_UPSERT_SQL, job_id, subgraph_id, basic_processing_cost, category, steps_json)
    return True


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate wire base processing cost for each part in the base itemcode results."""
    base_data = search_data["base_itemcode"]
    wire_data = search_data["wire_base"]
    tooth_hole_data = search_data.get("tooth_hole")

    if not job_id:
        job_id = base_data.get("job_id")

    logger.info(
        "Calculating wire base cost for job_id: %s, parts count: %s",
        job_id,
        len(base_data.get("parts", [])),
    )

    wire_parts = wire_data.get("wire_parts", [])
    if not wire_parts:
        logger.warning("No wire_parts found in wire_data for job_id: %s", job_id)
        return {
            "job_id": job_id,
            "results": [],
            "message": "未找到线割工艺数据",
        }

    wire_map = {
        str(item["conditions"]): item
        for item in wire_parts
        if item.get("conditions")
    }
    rule_map = _build_rule_map(wire_data.get("rule_prices", []))
    tooth_hole_perimeter_map = _build_tooth_hole_perimeter_map(tooth_hole_data or {})

    parts = list(base_data.get("parts", []))
    if subgraph_ids:
        allowed = set(subgraph_ids)
        parts = [part for part in parts if part.get("subgraph_id") in allowed]

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []

    for part in parts:
        result, db_data = await _calculate_part_price(
            job_id,
            part,
            wire_map,
            rule_map,
            tooth_hole_perimeter_map,
        )
        results.append(result)
        if db_data:
            db_updates.append(db_data)

    if db_updates:
        await batch_upsert_with_steps(
            [
                {
                    "job_id": item["job_id"],
                    "subgraph_id": item["subgraph_id"],
                    "value": item["basic_processing_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "wire_base",
            "basic_processing_cost",
        )

    logger.info("Completed wire base calculation for %s parts", len(results))
    return {
        "job_id": job_id,
        "results": results,
    }


def calculate_sync(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Sync wrapper for compatibility."""
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = [
    "MCP_TOOL_META",
    "batch_upsert_with_steps",
    "calculate",
    "calculate_sync",
]
