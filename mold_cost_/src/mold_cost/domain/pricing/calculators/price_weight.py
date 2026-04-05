"""Weight pricing calculator domain implementation."""

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
    "name": "calculate_weight",
    "description": "Calculate weight from base itemcode and density data.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "search_data": {
                "type": "object",
                "description": "Search payload containing base_itemcode and density results",
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
    "needs": ["base_itemcode", "density"],
}

_WEIGHT_UPSERT_SQL = """
    INSERT INTO processing_cost_calculation_details
        (job_id, subgraph_id, weight, calculation_steps)
    VALUES
        ($1::uuid, $2::text, $3, jsonb_build_array(jsonb_build_object('category', $4::text, 'steps', $5::jsonb)))
    ON CONFLICT (job_id, subgraph_id)
    DO UPDATE SET
        weight = EXCLUDED.weight,
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
    logger.info("Built density map with %s materials", len(density_map))
    return density_map


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
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = {
        "subgraph_id": subgraph_id,
        "part_name": part_name,
        "weight": 0.0,
        "note": note,
    }
    db_data = {
        "job_id": job_id,
        "subgraph_id": subgraph_id,
        "weight": 0.0,
        "calculation_steps": calculation_steps,
    }
    return result, db_data


async def _calculate_part_weight(
    job_id: str,
    part: Mapping[str, Any],
    density_map: Mapping[str, Decimal],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    subgraph_id = part["subgraph_id"]
    part_name = part["part_name"]

    try:
        material = part.get("material", "")
        length_mm = part.get("length_mm")
        width_mm = part.get("width_mm")
        thickness_mm = part.get("thickness_mm")

        if not all([length_mm, width_mm, thickness_mm]):
            missing = []
            if not length_mm:
                missing.append("length_mm")
            if not width_mm:
                missing.append("width_mm")
            if not thickness_mm:
                missing.append("thickness_mm")

            logger.warning(
                "Missing required fields for %s: %s, skipping calculation",
                part_name,
                ", ".join(missing),
            )

            calculation_steps = [
                {
                    "step": "数据验证",
                    "status": "failed",
                    "reason": f"缺少必需字段: {', '.join(missing)}",
                    "missing_fields": missing,
                    "weight": 0.0,
                }
            ]

            return _failure_result(
                job_id=job_id,
                subgraph_id=subgraph_id,
                part_name=part_name,
                note=f"缺少必需字段: {', '.join(missing)}",
                calculation_steps=calculation_steps,
            )

        density, matched_material = _get_material_density(material, density_map)

        length = Decimal(str(length_mm))
        width = Decimal(str(width_mm))
        thickness = Decimal(str(thickness_mm))

        weight = (density * length * width * thickness).quantize(Decimal("0.001"), ROUND_HALF_UP)

        calculation_steps = [
            {
                "step": "获取零件信息",
                "material": material,
                "length_mm": float(length_mm),
                "width_mm": float(width_mm),
                "thickness_mm": float(thickness_mm),
            },
            {
                "step": "匹配材料密度",
                "material": material,
                "matched_material": matched_material,
                "density": float(density),
                "unit": "g/cm3",
            },
            {
                "step": "计算重量",
                "formula": f"{density} * {length_mm} * {width_mm} * {thickness_mm}",
                "weight": float(weight),
            },
        ]

        logger.info(
            "[%s] %s: length=%s, width=%s, thickness=%s, weight=%s",
            subgraph_id,
            part_name,
            length_mm,
            width_mm,
            thickness_mm,
            weight,
        )

        result = {
            "subgraph_id": subgraph_id,
            "part_name": part_name,
            "length_mm": float(length_mm),
            "width_mm": float(width_mm),
            "thickness_mm": float(thickness_mm),
            "weight": float(weight),
        }
        db_data = {
            "job_id": job_id,
            "subgraph_id": subgraph_id,
            "weight": float(weight),
            "calculation_steps": calculation_steps,
        }
        return result, db_data
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Calculate weight error for %s: %s", part_name, exc)
        return (
            {
                "subgraph_id": subgraph_id,
                "part_name": part_name,
                "error": str(exc),
            },
            None,
        )


async def batch_upsert_with_steps(
    updates: Sequence[Mapping[str, Any]],
    category: str,
    field_name: str,
) -> None:
    """Batch upsert calculation steps for the weight calculator."""
    if not updates:
        return

    if field_name != "weight":
        raise ValueError(f"Unsupported field_name for weight calculator: {field_name}")

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
    weight: Any,
    category: str,
    steps: Sequence[Mapping[str, Any]],
) -> bool:
    steps_json = json.dumps(list(steps), default=str)
    await db.execute(_WEIGHT_UPSERT_SQL, job_id, subgraph_id, weight, category, steps_json)
    return True


async def _batch_update_weight_tables(updates: Sequence[Mapping[str, Any]]) -> None:
    logger.info("Batch updating weight for %s records in subgraphs and features tables", len(updates))

    tasks = []
    for data in updates:
        job_id = data["job_id"]
        subgraph_id = data["subgraph_id"]
        weight = data["weight"]

        sql_subgraphs = """
            UPDATE subgraphs SET
                weight_kg = $3,
                updated_at = NOW()
            WHERE job_id = $1::uuid AND subgraph_id = $2
        """
        tasks.append(db.execute(sql_subgraphs, job_id, subgraph_id, weight))

        sql_features = """
            UPDATE features SET
                calculated_weight_kg = $3
            WHERE job_id = $1::uuid AND subgraph_id = $2
        """
        tasks.append(db.execute(sql_features, job_id, subgraph_id, weight))

    if tasks:
        await asyncio.gather(*tasks)


async def calculate(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate weight for each part in the base itemcode search results."""
    base_data = search_data["base_itemcode"]
    density_data = search_data["density"]

    if not job_id:
        job_id = base_data.get("job_id")

    logger.info(
        "Calculating weight for job_id: %s, parts count: %s",
        job_id,
        len(base_data.get("parts", [])),
    )

    density_map = _build_density_map(density_data.get("density_data", []))

    results: list[dict[str, Any]] = []
    db_updates: list[dict[str, Any]] = []

    for part in base_data["parts"]:
        result, db_data = await _calculate_part_weight(job_id, part, density_map)
        results.append(result)
        if db_data:
            db_updates.append(db_data)

    if db_updates:
        updates_for_batch = [
            {
                "job_id": item["job_id"],
                "subgraph_id": item["subgraph_id"],
                "value": item["weight"],
                "steps": item["calculation_steps"],
            }
            for item in db_updates
        ]
        await batch_upsert_with_steps(updates_for_batch, "weight", "weight")
        await _batch_update_weight_tables(db_updates)

    logger.info("Completed calculation for %s parts", len(results))
    return {"job_id": job_id, "results": results}


def calculate_sync(
    search_data: dict[str, Any],
    job_id: str | None = None,
    subgraph_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Sync wrapper for compatibility."""
    return asyncio.run(calculate(search_data, job_id, subgraph_ids))


__all__ = [
    "MCP_TOOL_META",
    "MATERIAL_ALIASES",
    "DEFAULT_DENSITY",
    "batch_upsert_with_steps",
    "calculate",
    "calculate_sync",
]
