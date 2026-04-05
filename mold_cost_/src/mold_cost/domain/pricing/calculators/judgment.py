"""Pricing judgment cleanup calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from shared.unified_logging import get_logger

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "judgment_cleanup",
    "description": "Clean incompatible pricing fields before final total calculation.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode",
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
    "needs": ["base_itemcode"],
    "depends_on": [],
}

_MATERIAL_PREPARATION_SUBGRAPHS_SQL = """
    UPDATE subgraphs
    SET
        weight_kg = NULL,
        material_unit_price = NULL,
        material_cost = NULL,
        heat_treatment_unit_price = NULL,
        heat_treatment_cost = NULL,
        process_description = NULL,
        nc_roughing_time = NULL,
        nc_milling_time = NULL,
        drilling_time = NULL,
        milling_machine_time = NULL,
        large_grinding_time = NULL,
        small_grinding_time = NULL,
        edm_time = NULL,
        engraving_time = NULL,
        slow_wire_length = NULL,
        slow_wire_side_length = NULL,
        mid_wire_length = NULL,
        fast_wire_length = NULL,
        separate_item = NULL,
        total_cost = NULL,
        wire_process_note = NULL,
        nc_roughing_cost = NULL,
        nc_milling_cost = NULL,
        drilling_cost = NULL,
        milling_machine_cost = NULL,
        large_grinding_cost = NULL,
        small_grinding_cost = NULL,
        slow_wire_cost = NULL,
        slow_wire_side_cost = NULL,
        mid_wire_cost = NULL,
        fast_wire_cost = NULL,
        edm_cost = NULL,
        engraving_cost = NULL,
        separate_item_cost = NULL,
        processing_cost_total = NULL,
        applied_snapshot_ids = NULL,
        rule_reason = NULL,
        override_by_user = false,
        cost_calculation_method = NULL,
        has_sheet_line = false,
        sheet_area_mm2 = NULL,
        sheet_perimeter_mm = NULL,
        sheet_line_data = NULL,
        has_single_nc_calc = false,
        single_prt_file = NULL,
        process_changed = false,
        original_process = NULL,
        prt_3d_file = NULL,
        recalc_count = 0,
        last_recalc_at = NULL,
        last_recalc_by = NULL,
        status = 'pending',
        metadata = NULL,
        wire_process = NULL,
        small_grinding_count = NULL,
        updated_at = NOW()
    WHERE job_id = $1::uuid AND subgraph_id = $2::text
"""

_MATERIAL_PREPARATION_DETAILS_SQL = """
    UPDATE processing_cost_calculation_details
    SET
        calculation_steps = jsonb_build_array(
            jsonb_build_object(
                'category', 'material_preparation',
                'steps', jsonb_build_array(
                    jsonb_build_object(
                        'step', 'material_preparation_cleanup',
                        'note', $3::text
                    )
                )
            )
        )
    WHERE job_id = $1::uuid AND subgraph_id = $2::text
"""

_WIRE_CLEAR_SUBGRAPHS_SQL = """
    UPDATE subgraphs
    SET
        slow_wire_length = NULL,
        slow_wire_side_length = NULL,
        mid_wire_length = NULL,
        fast_wire_length = NULL,
        slow_wire_cost = NULL,
        slow_wire_side_cost = NULL,
        mid_wire_cost = NULL,
        fast_wire_cost = NULL,
        updated_at = NOW()
    WHERE job_id = $1::uuid AND subgraph_id = $2::text
"""

_WIRE_CLEAR_DETAILS_SQL = """
    UPDATE processing_cost_calculation_details
    SET
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' NOT IN ('wire_base', 'wire_speci', 'wire_special', 'wire_standard', 'wire_total')
        )
    WHERE job_id = $1::uuid AND subgraph_id = $2::text
"""


def _iter_parts(base_data: dict[str, Any], subgraph_ids: list[str] | None) -> list[dict[str, Any]]:
    parts = list(base_data.get("parts", []))
    if not subgraph_ids:
        return parts
    allowed = set(subgraph_ids)
    return [part for part in parts if part.get("subgraph_id") in allowed]


def _metadata_has_valid_wire_length(metadata: Any) -> bool:
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            return False
    if not isinstance(metadata, dict):
        return False
    details = metadata.get("wire_cut_details")
    if not isinstance(details, list):
        return False
    for detail in details:
        if not isinstance(detail, dict):
            continue
        try:
            if float(detail.get("total_length", 0) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


async def _cleanup_material_preparation(job_id: str, subgraph_id: str, target: str) -> None:
    note = f"该物料备料于: {target}"
    await db.execute(_MATERIAL_PREPARATION_SUBGRAPHS_SQL, job_id, subgraph_id)
    await db.execute(_MATERIAL_PREPARATION_DETAILS_SQL, job_id, subgraph_id, note)


async def _clear_wire_fields(job_id: str, subgraph_id: str) -> None:
    await db.execute(_WIRE_CLEAR_SUBGRAPHS_SQL, job_id, subgraph_id)
    await db.execute(_WIRE_CLEAR_DETAILS_SQL, job_id, subgraph_id)


async def _process_part(job_id: str, part: dict[str, Any]) -> dict[str, Any]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]
    cleanup_actions: list[dict[str, Any]] = []

    has_material_preparation = part.get("has_material_preparation")
    if has_material_preparation:
        await _cleanup_material_preparation(job_id, subgraph_id, str(has_material_preparation))
        cleanup_actions.append(
            {
                "type": "material_preparation",
                "reason": f"该物料备料于: {has_material_preparation}",
                "action": "清空全部成本与工艺相关字段",
            }
        )

    metadata = part.get("metadata")
    if not _metadata_has_valid_wire_length(metadata):
        if metadata:
            reason = "wire_cut_details 缺失或 total_length 全为 0"
        else:
            reason = "metadata 为空"
        await _clear_wire_fields(job_id, subgraph_id)
        cleanup_actions.append(
            {
                "type": "wire_data",
                "reason": reason,
                "action": "清空线切割相关字段与 calculation_steps",
            }
        )

    return {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "cleanup_actions": cleanup_actions,
    }


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_data = search_data["base_itemcode"]
    if not job_id:
        job_id = base_data.get("job_id")

    parts = _iter_parts(base_data, subgraph_ids)
    logger.info("Starting judgment cleanup for job_id: %s, parts count: %s", job_id, len(parts))

    results = await asyncio.gather(*[_process_part(job_id, part) for part in parts])
    logger.info("Completed judgment cleanup for %s parts", len(results))
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


__all__ = ["MCP_TOOL_META", "calculate", "calculate_sync"]
