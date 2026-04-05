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
