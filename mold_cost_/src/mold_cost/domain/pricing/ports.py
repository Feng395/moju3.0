"""定价领域端口定义。"""

from __future__ import annotations

from typing import Protocol


class PricingCalculationService(Protocol):
    """面向编排层暴露的定价计算入口。"""

    async def calculate(self, context: dict) -> dict: ...


class PricingJobTotalCostService(Protocol):
    """面向 bridge 期公共调用方暴露的 total_cost 汇总入口。"""

    async def update_job_total_cost(self, job_id: str) -> float: ...
