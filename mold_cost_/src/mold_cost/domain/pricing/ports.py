"""定价领域端口定义。"""

from __future__ import annotations

from typing import Protocol


class PricingCalculationService(Protocol):
    async def calculate(self, context: dict) -> dict: ...


class PricingJobTotalCostService(Protocol):
    async def update_job_total_cost(self, job_id: str) -> float: ...
