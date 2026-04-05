"""Pricing snapshot database repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..asyncpg import db

_ALLOWED_COLUMNS = frozenset(
    {
        "category",
        "sub_category",
        "price",
        "unit",
        "min_num",
        "note",
    }
)


class AsyncpgPricingSnapshotSearchRepository:
    """Asyncpg-backed pricing snapshot repository."""

    async def fetch_distinct_snapshots(
        self,
        job_id: str,
        categories: Sequence[str],
        columns: Sequence[str],
    ) -> list[dict[str, Any]]:
        selected_columns = self._normalize_columns(columns)
        normalized_categories = self._normalize_categories(categories)
        sql = f"""
            SELECT DISTINCT {", ".join(selected_columns)}
            FROM job_price_snapshots
            WHERE job_id = $1::uuid AND category = ANY($2::text[])
        """
        rows = await db.fetch_all(sql, job_id, list(normalized_categories))
        return [dict(row) for row in rows]

    async def fetch_base_itemcode_parts(
        self,
        job_id: str,
        subgraph_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        normalized_subgraph_ids = self._normalize_ids(subgraph_ids, "subgraph_ids")
        sql = """
            SELECT
                s.subgraph_id,
                s.part_name,
                s.part_code,
                s.wire_process_note,
                s.wire_process,
                f.length_mm,
                f.width_mm,
                f.thickness_mm,
                f.metadata,
                f.water_mill,
                f.quantity,
                f.boring_num,
                f.material,
                f.has_auto_material,
                f.has_material_preparation,
                f.needs_heat_treatment,
                f.tooth_hole,
                f.nc_time_cost
            FROM subgraphs s
            LEFT JOIN features f
                ON s.job_id = f.job_id AND s.subgraph_id = f.subgraph_id
            WHERE s.job_id = $1::uuid AND s.subgraph_id = ANY($2::text[])
        """
        rows = await db.fetch_all(sql, job_id, list(normalized_subgraph_ids))
        return [dict(row) for row in rows]

    async def fetch_processing_cost_details(
        self,
        job_id: str,
        subgraph_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        normalized_subgraph_ids = self._normalize_ids(subgraph_ids, "subgraph_ids")
        sql = """
            SELECT
                subgraph_id,
                weight,
                basic_processing_cost,
                special_base_cost,
                standard_base_cost,
                material_additional_cost,
                material_cost,
                heat_treatment_cost,
                thread_ends_cost,
                hanging_table_cost,
                chamfer_cost,
                bevel_cost,
                oil_tank_cost,
                high_cost,
                grinding_cost,
                plate_cost,
                long_strip_cost,
                component_cost,
                tooth_hole_cost,
                tooth_hole_time_cost,
                nc_roughing_cost,
                nc_milling_cost,
                nc_drilling_cost,
                nc_base_roughing_cost,
                nc_base_milling_cost,
                nc_base_drilling_cost,
                calculation_steps
            FROM processing_cost_calculation_details
            WHERE job_id = $1::uuid
              AND subgraph_id = ANY($2::text[])
        """
        rows = await db.fetch_all(sql, job_id, list(normalized_subgraph_ids))
        return [self._normalize_processing_cost_row(dict(row)) for row in rows]

    async def fetch_subgraph_cost_summary(
        self,
        job_id: str,
        subgraph_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        normalized_subgraph_ids = self._normalize_ids(subgraph_ids, "subgraph_ids")
        sql = """
            SELECT
                subgraph_id,
                material_cost,
                heat_treatment_cost,
                large_grinding_cost,
                small_grinding_cost,
                slow_wire_cost,
                slow_wire_side_cost,
                mid_wire_cost,
                fast_wire_cost,
                edm_cost,
                nc_roughing_cost,
                nc_milling_cost,
                drilling_cost
            FROM subgraphs
            WHERE job_id = $1::uuid
              AND subgraph_id = ANY($2::text[])
        """
        rows = await db.fetch_all(sql, job_id, list(normalized_subgraph_ids))
        return [self._normalize_decimal_row(dict(row)) for row in rows]

    @staticmethod
    def _normalize_columns(columns: Sequence[str]) -> tuple[str, ...]:
        normalized_columns = tuple(dict.fromkeys(columns))
        if not normalized_columns:
            raise ValueError("columns must not be empty")
        invalid_columns = sorted(set(normalized_columns) - _ALLOWED_COLUMNS)
        if invalid_columns:
            raise ValueError(f"unsupported columns: {', '.join(invalid_columns)}")
        return normalized_columns

    @staticmethod
    def _normalize_categories(categories: Sequence[str]) -> tuple[str, ...]:
        normalized_categories = tuple(dict.fromkeys(categories))
        if not normalized_categories:
            raise ValueError("categories must not be empty")
        return normalized_categories

    @staticmethod
    def _normalize_ids(values: Sequence[str], field_name: str) -> tuple[str, ...]:
        normalized_values = tuple(dict.fromkeys(values))
        if not normalized_values:
            raise ValueError(f"{field_name} must not be empty")
        return normalized_values

    @classmethod
    def _normalize_processing_cost_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        normalized = cls._normalize_decimal_row(row)
        calculation_steps = normalized.get("calculation_steps")
        if calculation_steps is None:
            normalized["calculation_steps"] = []
        elif isinstance(calculation_steps, str):
            import json

            try:
                normalized["calculation_steps"] = json.loads(calculation_steps)
            except json.JSONDecodeError:
                normalized["calculation_steps"] = []
        return normalized

    @staticmethod
    def _normalize_decimal_row(row: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            if value is None:
                normalized[key] = [] if key == "calculation_steps" else 0.0
            elif hasattr(value, "as_tuple"):
                normalized[key] = float(value)
            else:
                normalized[key] = value
        return normalized
