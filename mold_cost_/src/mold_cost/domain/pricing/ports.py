"""定价领域端口定义。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class PricingCalculationService(Protocol):
    """面向编排层暴露的定价计算入口。"""

    async def calculate(self, context: dict) -> dict: ...


class PricingJobTotalCostService(Protocol):
    """面向 bridge 期公共调用方暴露的 total_cost 汇总入口。"""

    async def update_job_total_cost(self, job_id: str) -> float: ...


class PricingSnapshotSearchRepository(Protocol):
    """面向定价搜索模块暴露的价格快照读取端口。"""

    async def fetch_distinct_snapshots(
        self,
        job_id: str,
        categories: Sequence[str],
        columns: Sequence[str],
    ) -> list[dict[str, Any]]: ...
