"""NC total pricing calculator domain implementation."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Any

from shared.unified_logging import get_logger

from mold_cost.infrastructure.db.repositories.script_db import db

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "calculate_nc_total_cost",
    "description": "Calculate final NC costs by comparing summed NC costs with corresponding NC base costs.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing total",
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
    "needs": ["total"],
}

_NC_TOTAL_UPSERT_SQL = """
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


def _to_decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _resolve_cost(original: Decimal, base: Decimal) -> tuple[Decimal, str]:
    if original <= 0:
        return Decimal("0"), "none"
    if original >= base:
        return original, "original"
    return base, "base"


def _calculate_part_nc_total(detail: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    subgraph_id = detail["subgraph_id"]

    originals = {
        "nc_roughing_cost": _to_decimal(detail.get("nc_roughing_cost", 0)),
        "nc_milling_cost": _to_decimal(detail.get("nc_milling_cost", 0)),
        "nc_drilling_cost": _to_decimal(detail.get("nc_drilling_cost", 0)),
    }
    bases = {
        "nc_roughing_cost": _to_decimal(detail.get("nc_base_roughing_cost", 0)),
        "nc_milling_cost": _to_decimal(detail.get("nc_base_milling_cost", 0)),
        "nc_drilling_cost": _to_decimal(detail.get("nc_base_drilling_cost", 0)),
    }

    final_roughing, roughing_used = _resolve_cost(originals["nc_roughing_cost"], bases["nc_roughing_cost"])
    final_milling, milling_used = _resolve_cost(originals["nc_milling_cost"], bases["nc_milling_cost"])
    final_drilling, drilling_used = _resolve_cost(originals["nc_drilling_cost"], bases["nc_drilling_cost"])

    comparisons = [
        {
            "process": "roughing",
            "has_data": originals["nc_roughing_cost"] > 0,
            "original": float(originals["nc_roughing_cost"]),
            "base": float(bases["nc_roughing_cost"]),
            "final": float(final_roughing),
            "used": roughing_used,
            "formula": (
                f"max({float(originals['nc_roughing_cost']):.2f}, {float(bases['nc_roughing_cost']):.2f})"
                if originals["nc_roughing_cost"] > 0
                else "0 (no roughing data)"
            ),
        },
        {
            "process": "milling",
            "has_data": originals["nc_milling_cost"] > 0,
            "original": float(originals["nc_milling_cost"]),
            "base": float(bases["nc_milling_cost"]),
            "final": float(final_milling),
            "used": milling_used,
            "formula": (
                f"max({float(originals['nc_milling_cost']):.2f}, {float(bases['nc_milling_cost']):.2f})"
                if originals["nc_milling_cost"] > 0
                else "0 (no milling data)"
            ),
        },
        {
            "process": "drilling",
            "has_data": originals["nc_drilling_cost"] > 0,
            "original": float(originals["nc_drilling_cost"]),
            "base": float(bases["nc_drilling_cost"]),
            "final": float(final_drilling),
            "used": drilling_used,
            "formula": (
                f"max({float(originals['nc_drilling_cost']):.2f}, {float(bases['nc_drilling_cost']):.2f})"
                if originals["nc_drilling_cost"] > 0
                else "0 (no drilling data)"
            ),
        },
    ]

    calculation_steps = [
        {
            "step": "collect_original_nc_costs",
            **{field: float(value) for field, value in originals.items()},
        },
        {
            "step": "collect_nc_base_costs",
            "nc_base_roughing_cost": float(bases["nc_roughing_cost"]),
            "nc_base_milling_cost": float(bases["nc_milling_cost"]),
            "nc_base_drilling_cost": float(bases["nc_drilling_cost"]),
        },
        {
            "step": "resolve_final_nc_costs",
            "comparisons": comparisons,
        },
        {
            "step": "summarize_final_nc_costs",
            "nc_roughing_cost": float(final_roughing),
            "nc_milling_cost": float(final_milling),
            "drilling_cost": float(final_drilling),
            "total": float(final_roughing + final_milling + final_drilling),
        },
    ]

    result = {
        "subgraph_id": subgraph_id,
        "original": {
            "nc_roughing_cost": float(originals["nc_roughing_cost"]),
            "nc_milling_cost": float(originals["nc_milling_cost"]),
            "nc_drilling_cost": float(originals["nc_drilling_cost"]),
            "nc_base_roughing_cost": float(bases["nc_roughing_cost"]),
            "nc_base_milling_cost": float(bases["nc_milling_cost"]),
            "nc_base_drilling_cost": float(bases["nc_drilling_cost"]),
        },
        "comparisons": {
            "roughing": comparisons[0],
            "milling": comparisons[1],
            "drilling": comparisons[2],
        },
        "final": {
            "nc_roughing_cost": float(final_roughing),
            "nc_milling_cost": float(final_milling),
            "drilling_cost": float(final_drilling),
        },
    }
    db_data = {
        "subgraph_id": subgraph_id,
        "nc_roughing_cost": float(final_roughing),
        "nc_milling_cost": float(final_milling),
        "drilling_cost": float(final_drilling),
        "calculation_steps": calculation_steps,
    }
    return result, db_data


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    total_data = search_data.get("total")
    if not total_data:
        logger.warning("Missing total data, skipping NC total cost calculation")
        return {
            "job_id": job_id or "unknown",
            "results": [],
            "note": "Missing total data, skipped NC total cost calculation",
        }

    if not job_id:
        job_id = total_data.get("job_id")

    allowed_subgraph_ids = set(subgraph_ids or [])
    cost_details = total_data.get("cost_details", [])
    if allowed_subgraph_ids:
        cost_details = [
            detail
            for detail in cost_details
            if detail.get("subgraph_id") in allowed_subgraph_ids
        ]

    logger.info("Calculating NC total cost for job_id=%s, parts=%s", job_id, len(cost_details))

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []
    for detail in cost_details:
        result, db_data = _calculate_part_nc_total(detail)
        results.append(result)
        db_updates.append(db_data)

    if db_updates:
        await _batch_update_subgraphs(job_id, db_updates)
        await batch_upsert_with_steps(
            [
                {
                    "job_id": job_id,
                    "subgraph_id": data["subgraph_id"],
                    "steps": data["calculation_steps"],
                }
                for data in db_updates
            ],
            "nc_total",
            None,
        )

    return {
        "job_id": job_id,
        "results": results,
    }


async def _batch_update_subgraphs(job_id: str, updates: list[dict[str, Any]]) -> None:
    sql = """
        UPDATE subgraphs
        SET
            nc_roughing_cost = $3,
            nc_milling_cost = $4,
            drilling_cost = $5,
            updated_at = NOW()
        WHERE job_id = $1::uuid AND subgraph_id = $2::text
    """
    tasks = [
        db.execute(
            sql,
            job_id,
            data["subgraph_id"],
            data["nc_roughing_cost"],
            data["nc_milling_cost"],
            data["drilling_cost"],
        )
        for data in updates
    ]
    if tasks:
        await asyncio.gather(*tasks)


async def batch_upsert_with_steps(
    updates: list[dict[str, Any]],
    category: str,
    field_name: str | None,
) -> None:
    if not updates:
        return

    tasks = [
        _upsert_single_record(
            update["job_id"],
            update["subgraph_id"],
            category,
            update["steps"],
        )
        for update in updates
    ]
    await asyncio.gather(*tasks)


async def _upsert_single_record(
    job_id: str,
    subgraph_id: str,
    category: str,
    steps: list[dict[str, Any]],
) -> bool:
    steps_json = json.dumps(steps, default=str)
    await db.execute(_NC_TOTAL_UPSERT_SQL, job_id, subgraph_id, category, steps_json)
    return True


def calculate_sync(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "batch_upsert_with_steps", "calculate", "calculate_sync"]
