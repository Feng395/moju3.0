"""Pricing snapshot search service."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..ports import PricingSnapshotSearchRepository
from ....infrastructure.db.repositories.pricing_snapshot_repository import (
    AsyncpgPricingSnapshotSearchRepository,
)


class PricingSnapshotSearchService:
    """Domain service for pricing snapshot queries."""

    def __init__(self, repository: PricingSnapshotSearchRepository | None = None):
        self._repository = repository or AsyncpgPricingSnapshotSearchRepository()

    async def fetch_snapshots(
        self,
        *,
        job_id: str,
        categories: Sequence[str],
        columns: Sequence[str],
    ) -> list[dict[str, Any]]:
        return await self._repository.fetch_distinct_snapshots(
            job_id=job_id,
            categories=categories,
            columns=columns,
        )

    async def fetch_base_itemcode_parts(
        self,
        *,
        job_id: str,
        subgraph_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        return await self._repository.fetch_base_itemcode_parts(
            job_id=job_id,
            subgraph_ids=subgraph_ids,
        )

    async def fetch_processing_cost_details(
        self,
        *,
        job_id: str,
        subgraph_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        return await self._repository.fetch_processing_cost_details(
            job_id=job_id,
            subgraph_ids=subgraph_ids,
        )

    async def fetch_subgraph_cost_summary(
        self,
        *,
        job_id: str,
        subgraph_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        return await self._repository.fetch_subgraph_cost_summary(
            job_id=job_id,
            subgraph_ids=subgraph_ids,
        )


pricing_snapshot_search_service = PricingSnapshotSearchService()
