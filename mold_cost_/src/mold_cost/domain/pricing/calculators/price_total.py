"""Final total pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from shared.unified_logging import get_logger

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

PROCESS_DESCRIPTION_FIELDS = [
    ("nc_roughing_time", "S"),
    ("nc_milling_time", "SS"),
    ("drilling_time", "Z"),
    ("milling_machine_time", "X"),
    ("large_grinding_time", "M"),
    ("small_grinding_time", "YM"),
    ("slow_wire_length", "WE"),
    ("mid_wire_length", "WZ"),
    ("fast_wire_length", "WC"),
    ("edm_time", "EDM"),
    ("engraving_cost", "DK"),
]

PROCESSING_COST_FIELDS = [
    ("large_grinding_cost", "large_grinding"),
    ("small_grinding_cost", "small_grinding"),
    ("slow_wire_cost", "slow_wire"),
    ("slow_wire_side_cost", "slow_wire_side"),
    ("mid_wire_cost", "mid_wire"),
    ("fast_wire_cost", "fast_wire"),
    ("edm_cost", "edm"),
    ("nc_roughing_cost", "nc_roughing"),
    ("nc_milling_cost", "nc_milling"),
    ("drilling_cost", "drilling"),
]

_TOTAL_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, total_cost, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        total_cost = EXCLUDED.total_cost,
        calculation_steps = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(
                COALESCE(processing_cost_calculation_details.calculation_steps, '[]'::jsonb)
            ) AS elem
            WHERE elem->>'category' != $4::text
        ) || jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb))
"""

MCP_TOOL_META = {
    "name": "calculate_final_total_cost",
    "description": "Calculate the final part total and aggregated job total from subgraphs_cost.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing subgraphs_cost",
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
    "needs": ["subgraphs_cost"],
    "depends_on": ["search_subgraphs_cost_by_job_id", "judgment_cleanup"],
}


def _as_decimal(summary: dict[str, Any], field_name: str) -> Decimal:
    return Decimal(str(summary.get(field_name, 0) or 0))


def _build_processing_formula(processing_values: list[str], total_value: float) -> str:
    if processing_values:
        return " + ".join(processing_values) + f" = {total_value:.2f}"
    return "0 (no processing cost)"


def _build_total_formula(total_values: list[str], total_value: float) -> str:
    if total_values:
        return " + ".join(total_values) + f" = {total_value:.2f}"
    return "0 (no total cost)"


def _calculate_part_total(summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    subgraph_id = summary["subgraph_id"]

    try:
        material_cost = _as_decimal(summary, "material_cost")
        heat_treatment_cost = _as_decimal(summary, "heat_treatment_cost")
        parsed_processing_costs = {
            field_name: _as_decimal(summary, field_name)
            for field_name, _label in PROCESSING_COST_FIELDS
        }
    except (ValueError, TypeError, InvalidOperation) as exc:
        logger.error("Failed to convert cost values for %s: %s", subgraph_id, exc)
        calculation_steps = [
            {
                "step": "convert_cost_values",
                "status": "failed",
                "reason": f"Failed to convert cost values: {exc}",
                "total_cost": 0.0,
                "processing_cost_total": 0.0,
            }
        ]
        return (
            {
                "subgraph_id": subgraph_id,
                "total_cost": 0.0,
                "processing_cost_total": 0.0,
                "note": f"Failed to convert cost values: {exc}",
            },
            {
                "subgraph_id": subgraph_id,
                "total_cost": 0.0,
                "processing_cost_total": 0.0,
                "calculation_steps": calculation_steps,
            },
        )

    processing_cost_total = sum(parsed_processing_costs.values(), Decimal("0"))
    total_cost = material_cost + heat_treatment_cost + processing_cost_total

    total_cost_float = float(total_cost)
    processing_cost_total_float = float(processing_cost_total)
    cost_items = {
        "material_cost": float(material_cost),
        "heat_treatment_cost": float(heat_treatment_cost),
        **{field_name: float(value) for field_name, value in parsed_processing_costs.items()},
    }

    processing_items: list[str] = []
    processing_values: list[str] = []
    for field_name, label in PROCESSING_COST_FIELDS:
        value = float(parsed_processing_costs[field_name])
        if value > 0:
            processing_items.append(label)
            processing_values.append(f"{value:.2f}")

    total_items: list[str] = []
    total_values: list[str] = []
    if float(material_cost) > 0:
        total_items.append("material")
        total_values.append(f"{float(material_cost):.2f}")
    if float(heat_treatment_cost) > 0:
        total_items.append("heat_treatment")
        total_values.append(f"{float(heat_treatment_cost):.2f}")
    if processing_cost_total_float > 0:
        total_items.append("processing")
        total_values.append(f"{processing_cost_total_float:.2f}")

    calculation_steps = [
        {
            "step": "collect_cost_items",
            **cost_items,
        },
        {
            "step": "calculate_processing_cost_total",
            "items": processing_items or ["none"],
            "formula": _build_processing_formula(processing_values, processing_cost_total_float),
            "processing_cost_total": processing_cost_total_float,
        },
        {
            "step": "calculate_total_cost",
            "items": total_items or ["none"],
            "formula": _build_total_formula(total_values, total_cost_float),
            "total_cost": total_cost_float,
        },
    ]

    logger.info(
        "[%s] total_cost=%.2f processing_cost_total=%.2f",
        subgraph_id,
        total_cost_float,
        processing_cost_total_float,
    )

    result = {
        "subgraph_id": subgraph_id,
        "total_cost": total_cost_float,
        "processing_cost_total": processing_cost_total_float,
        "breakdown": cost_items,
    }
    db_data = {
        "subgraph_id": subgraph_id,
        "total_cost": total_cost_float,
        "processing_cost_total": processing_cost_total_float,
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

    if field_name != "total_cost":
        raise ValueError(f"Unsupported field_name for total calculator: {field_name}")

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
    total_cost: Any,
    category: str,
    steps: list[dict[str, Any]],
) -> bool:
    steps_json = json.dumps(steps, default=str)
    await db.execute(_TOTAL_UPSERT_SQL, job_id, subgraph_id, total_cost, category, steps_json)
    return True


async def _batch_update_subgraphs(job_id: str, updates: list[dict[str, Any]]) -> None:
    logger.info("Batch updating %s total records", len(updates))

    sql = """
        UPDATE subgraphs
        SET
            total_cost = $3,
            processing_cost_total = $4,
            updated_at = NOW()
        WHERE job_id = $1::uuid AND subgraph_id = $2::text
    """

    update_tasks = [
        db.execute(
            sql,
            job_id,
            data["subgraph_id"],
            data["total_cost"],
            data["processing_cost_total"],
        )
        for data in updates
    ]
    if update_tasks:
        await asyncio.gather(*update_tasks)

    await batch_upsert_with_steps(
        [
            {
                "job_id": job_id,
                "subgraph_id": data["subgraph_id"],
                "value": data["total_cost"],
                "steps": data["calculation_steps"],
            }
            for data in updates
        ],
        "total",
        "total_cost",
    )


async def _update_job_total_cost(job_id: str, total_cost: float) -> None:
    sql = """
        UPDATE jobs
        SET
            total_cost = $2,
            updated_at = NOW()
        WHERE job_id = $1::uuid
    """
    await db.execute(sql, job_id, total_cost)


def _read_row_value(row: Any, field_name: str) -> Any:
    if hasattr(row, "get"):
        return row.get(field_name)
    try:
        return row[field_name]
    except Exception:
        return None


async def _update_process_descriptions(job_id: str, subgraph_ids: list[str]) -> None:
    if not subgraph_ids:
        return

    field_names = [field_name for field_name, _abbr in PROCESS_DESCRIPTION_FIELDS]
    field_list = ", ".join(field_names)
    query_sql = f"""
        SELECT subgraph_id, {field_list}
        FROM subgraphs
        WHERE job_id = $1::uuid AND subgraph_id = ANY($2::text[])
    """

    rows = await db.fetch_all(query_sql, job_id, subgraph_ids)
    update_tasks = []
    for row in rows:
        subgraph_id = _read_row_value(row, "subgraph_id")
        processes = [
            abbr
            for field_name, abbr in PROCESS_DESCRIPTION_FIELDS
            if (_read_row_value(row, field_name) not in (None, 0, 0.0, "0", "0.0"))
        ]
        processes.append("QC")
        update_tasks.append(
            _update_single_process_description(job_id, subgraph_id, "-".join(processes))
        )

    if update_tasks:
        await asyncio.gather(*update_tasks)


async def _update_single_process_description(
    job_id: str,
    subgraph_id: str,
    process_description: str,
) -> None:
    sql = """
        UPDATE subgraphs
        SET
            process_description = $3,
            updated_at = NOW()
        WHERE job_id = $1::uuid AND subgraph_id = $2::text
    """
    await db.execute(sql, job_id, subgraph_id, process_description)


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    subgraphs_cost_data = search_data.get("subgraphs_cost")
    if not subgraphs_cost_data:
        logger.warning("Missing subgraphs_cost data, skipping final total cost calculation")
        return {
            "job_id": job_id if job_id else "unknown",
            "job_total_cost": 0.0,
            "parts_count": 0,
            "results": [],
            "note": "Missing subgraphs_cost data, skipped final total cost calculation",
        }

    if not job_id:
        job_id = subgraphs_cost_data.get("job_id")

    allowed_subgraph_ids = set(subgraph_ids or [])
    cost_summary = subgraphs_cost_data.get("cost_summary", [])
    if allowed_subgraph_ids:
        cost_summary = [
            summary
            for summary in cost_summary
            if summary.get("subgraph_id") in allowed_subgraph_ids
        ]

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []
    job_total_cost = Decimal("0")

    for summary in cost_summary:
        result, db_data = _calculate_part_total(summary)
        results.append(result)
        if db_data:
            db_updates.append(db_data)
            job_total_cost += Decimal(str(db_data["total_cost"]))

    if db_updates:
        await _batch_update_subgraphs(job_id, db_updates)
        await _update_process_descriptions(job_id, [data["subgraph_id"] for data in db_updates])

    job_total_cost_float = float(job_total_cost)
    await _update_job_total_cost(job_id, job_total_cost_float)
    logger.info(
        "Completed final total calculation for %s parts, job_total_cost=%.2f",
        len(results),
        job_total_cost_float,
    )
    return {
        "job_id": job_id,
        "job_total_cost": job_total_cost_float,
        "parts_count": len(results),
        "results": results,
    }


def calculate_sync(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = [
    "MCP_TOOL_META",
    "PROCESS_DESCRIPTION_FIELDS",
    "PROCESSING_COST_FIELDS",
    "batch_upsert_with_steps",
    "calculate",
    "calculate_sync",
]
