"""定价快照数据库仓储。"""

from __future__ import annotations

from collections.abc import Sequence

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
    """基于 asyncpg 的价格快照读取实现。"""

    async def fetch_distinct_snapshots(
        self,
        job_id: str,
        categories: Sequence[str],
        columns: Sequence[str],
    ) -> list[dict]:
        selected_columns = self._normalize_columns(columns)
        normalized_categories = self._normalize_categories(categories)
        sql = f"""
            SELECT DISTINCT {", ".join(selected_columns)}
            FROM job_price_snapshots
            WHERE job_id = $1::uuid AND category = ANY($2::text[])
        """
        rows = await db.fetch_all(sql, job_id, list(normalized_categories))
        return [dict(row) for row in rows]

    @staticmethod
    def _normalize_columns(columns: Sequence[str]) -> tuple[str, ...]:
        # 中文注释：字段名来自领域层固定枚举，先做白名单校验再拼接 SQL。
        normalized_columns = tuple(dict.fromkeys(columns))
        if not normalized_columns:
            raise ValueError("columns must not be empty")
        invalid_columns = sorted(set(normalized_columns) - _ALLOWED_COLUMNS)
        if invalid_columns:
            raise ValueError(f"unsupported columns: {', '.join(invalid_columns)}")
        return normalized_columns

    @staticmethod
    def _normalize_categories(categories: Sequence[str]) -> tuple[str, ...]:
        # 中文注释：category 作为查询值走参数绑定，避免把动态值拼进 SQL。
        normalized_categories = tuple(dict.fromkeys(categories))
        if not normalized_categories:
            raise ValueError("categories must not be empty")
        return normalized_categories
