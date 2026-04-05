"""Wire special pricing calculator domain implementation."""

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
    "name": "calculate_wire_special_price",
    "description": "Calculate wire special processing cost from part geometry and special price rules.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode and wire_special results",
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
    "needs": ["base_itemcode", "wire_special"],
}

_WIRE_SPECIAL_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, special_base_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        special_base_cost = EXCLUDED.special_base_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""


def _build_price_map(special_prices: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    price_map: dict[str, float] = {"template_threshold": 400.0}

    for price in special_prices:
        sub_category = price.get("sub_category")
        if not sub_category:
            continue

        try:
            price_value = float(price.get("price", 0) or 0)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to parse price for %s: %s", sub_category, exc)
            continue

        if sub_category == "template_component":
            price_map["template_threshold"] = price_value
        else:
            price_map[str(sub_category)] = price_value

    return price_map


def _get_wire_type(wire_process_note: Any) -> str:
    note = "" if wire_process_note is None else str(wire_process_note)
    normalized = note.lower()
    if "慢丝" in note or "鎱笣" in note or "slow" in normalized:
        return "slow"
    if "中丝" in note or "涓笣" in note or "medium" in normalized:
        return "medium"
    if "快丝" in note or "蹇笣" in note or "fast" in normalized:
        return "fast"
    return "fast"


def _is_template(
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    threshold: float,
) -> tuple[bool, bool]:
    dimensions = [length_mm, width_mm, thickness_mm]
    max_dimension = max(d for d in dimensions if d is not None)
    is_valid = max_dimension > 0
    is_template = max_dimension > threshold
    return is_template, is_valid


def _has_side_cut(metadata: Mapping[str, Any] | None) -> bool:
    if not metadata or "wire_cut_details" not in metadata:
        return False

    for detail in metadata.get("wire_cut_details", []):
        if not isinstance(detail, Mapping):
            continue
        view = detail.get("view")
        total_length = detail.get("total_length", 0)
        if view in {"front_view", "side_view"} and total_length != 0:
            return True
    return False


async def _calculate_part_price(
    job_id: str,
    part: Mapping[str, Any],
    price_map: Mapping[str, float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    wire_process_note = part.get("wire_process_note")
    length_mm = float(part.get("length_mm") or 0)
    width_mm = float(part.get("width_mm") or 0)
    thickness_mm = float(part.get("thickness_mm") or 0)
    metadata = part.get("metadata")

    logger.info(
        "Calculating wire special for part: %s (%s), wire_process_note: %s",
        part_name,
        subgraph_id,
        wire_process_note,
    )

    if not metadata:
        calculation_steps = [
            {
                "step": "檢查metadata",
                "note": "metadata為空，跳過線割特殊價格計算",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "wire_type": _get_wire_type(wire_process_note),
                "is_template": False,
                "has_side_cut": False,
                "special_base_cost": 0.0,
                "note": "metadata為空，跳過計算",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "special_base_cost": 0.0,
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
                    "reason": f"JSON解析失敗: {exc}",
                }
            ]
            return (
                {
                    "subgraph_id": subgraph_id,
                    "part_name": part_name,
                    "wire_type": _get_wire_type(wire_process_note),
                    "is_template": False,
                    "has_side_cut": False,
                    "special_base_cost": 0.0,
                    "note": f"metadata JSON解析失敗: {exc}",
                },
                {
                    "job_id": job_id,
                    "subgraph_id": subgraph_id,
                    "special_base_cost": 0.0,
                    "calculation_steps": calculation_steps,
                },
            )

    if not isinstance(metadata, Mapping):
        calculation_steps = [
            {
                "step": "檢查metadata類型",
                "note": "metadata不是字典類型，跳過線割特殊價格計算",
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "wire_type": _get_wire_type(wire_process_note),
                "is_template": False,
                "has_side_cut": False,
                "special_base_cost": 0.0,
                "note": "metadata類型錯誤，跳過計算",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "special_base_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    template_threshold = float(price_map.get("template_threshold", 400.0))
    wire_type = _get_wire_type(wire_process_note)
    is_template, is_valid = _is_template(length_mm, width_mm, thickness_mm, template_threshold)
    max_dimension = max(length_mm, width_mm, thickness_mm)

    calculation_steps = [
        {
            "step": "判斷線割類型",
            "wire_process_note": wire_process_note,
            "wire_type": wire_type,
        }
    ]

    if not is_valid:
        calculation_steps.append(
            {
                "step": "驗證尺寸資料",
                "status": "failed",
                "reason": f"最大尺寸 {max_dimension}mm <= 0，數據無效",
                "dimensions": {
                    "length_mm": length_mm,
                    "width_mm": width_mm,
                    "thickness_mm": thickness_mm,
                    "max_dimension": max_dimension,
                },
            }
        )
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "wire_type": wire_type,
                "is_template": False,
                "has_side_cut": False,
                "special_base_cost": 0.0,
                "note": "尺寸數據無效，跳過計算",
            },
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "special_base_cost": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    calculation_steps.append(
        {
            "step": "判斷零件類型",
            "dimensions": {
                "length_mm": length_mm,
                "width_mm": width_mm,
                "thickness_mm": thickness_mm,
                "max_dimension": max_dimension,
            },
            "threshold": template_threshold,
            "is_template": is_template,
            "reason": f"最大尺寸 {max_dimension}mm {'>' if is_template else '<='} {template_threshold}mm",
        }
    )

    if is_template:
        fee_key = f"{wire_type}_template"
    else:
        fee_key = f"{wire_type}_component"
    special1 = float(price_map.get(fee_key, 0.0) or 0.0)

    calculation_steps.append(
        {
            "step": "計算基礎費用(special1)",
            "fee_type": fee_key,
            "amount": special1,
        }
    )

    has_side_cut = _has_side_cut(metadata)
    side_cut_details = []
    for detail in metadata.get("wire_cut_details", []):
        if not isinstance(detail, Mapping):
            continue
        view = detail.get("view")
        total_length = detail.get("total_length", 0)
        if view in {"front_view", "side_view"}:
            side_cut_details.append({"view": view, "total_length": total_length})

    calculation_steps.append(
        {
            "step": "判斷是否有側割",
            "side_cut_details": side_cut_details,
            "has_side_cut": has_side_cut,
        }
    )

    side_cut_key = f"{wire_type}_side"
    special2 = float(price_map.get(side_cut_key, 0.0) or 0.0) if has_side_cut else 0.0

    calculation_steps.append(
        {
            "step": "計算側割費用(special2)",
            "fee_type": side_cut_key if has_side_cut else "無側割",
            "has_side_cut": has_side_cut,
            "amount": special2,
        }
    )

    special_base_cost = special1 + special2
    calculation_steps.append(
        {
            "step": "計算總特殊費用",
            "formula": f"{special1} + {special2}",
            "special_base_cost": round(special_base_cost, 2),
        }
    )

    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "wire_type": wire_type,
        "is_template": is_template,
        "has_side_cut": has_side_cut,
        "special_base_cost": round(special_base_cost, 2),
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "special_base_cost": special_base_cost,
        "calculation_steps": calculation_steps,
    }
    return result, db_data


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    if not updates:
        return

    if field_name != "special_base_cost":
        raise ValueError(f"Unsupported field_name for wire special calculator: {field_name}")

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
    special_base_cost: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    await db.execute(
        _WIRE_SPECIAL_UPSERT_SQL,
        job_id,
        subgraph_id,
        special_base_cost,
        category,
        json.dumps(list(steps), default=str),
    )
    return True


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_data = search_data["base_itemcode"]
    special_data = search_data["wire_special"]

    if not job_id:
        job_id = base_data.get("job_id")

    parts = list(base_data.get("parts", []))
    if subgraph_ids:
        allowed = set(subgraph_ids)
        parts = [part for part in parts if part.get("subgraph_id") in allowed]

    logger.info("Calculating wire special for job_id: %s, parts count: %s", job_id, len(parts))

    price_map = _build_price_map(special_data.get("special_prices", []))

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []
    for part in parts:
        result, db_data = await _calculate_part_price(job_id, part, price_map)
        results.append(result)
        db_updates.append(db_data)

    if db_updates:
        await batch_upsert_with_steps(
            [
                {
                    "job_id": item["job_id"],
                    "subgraph_id": item["subgraph_id"],
                    "value": item["special_base_cost"],
                    "steps": item["calculation_steps"],
                }
                for item in db_updates
            ],
            "wire_special",
            "special_base_cost",
        )

    logger.info("Completed calculation for %s parts", len(results))
    return {"job_id": job_id, "results": results}


def calculate_sync(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "batch_upsert_with_steps", "calculate", "calculate_sync"]
