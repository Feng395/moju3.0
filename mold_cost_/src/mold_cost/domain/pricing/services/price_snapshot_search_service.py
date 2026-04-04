"""定价快照搜索领域服务。"""

from __future__ import annotations

from collections.abc import Sequence

from ..ports import PricingSnapshotSearchRepository
from ....infrastructure.db.repositories.pricing_snapshot_repository import (
    AsyncpgPricingSnapshotSearchRepository,
)


class PricingSnapshotSearchService:
    """收口价格快照搜索的领域服务。"""

    def __init__(self, repository: PricingSnapshotSearchRepository | None = None):
        # 中文注释：默认接到基础设施仓储，测试时可以替换为 stub。
        self._repository = repository or AsyncpgPricingSnapshotSearchRepository()

    async def fetch_snapshots(
        self,
        *,
        job_id: str,
        categories: Sequence[str],
        columns: Sequence[str],
    ) -> list[dict]:
        return await self._repository.fetch_distinct_snapshots(
            job_id=job_id,
            categories=categories,
            columns=columns,
        )


pricing_snapshot_search_service = PricingSnapshotSearchService()
