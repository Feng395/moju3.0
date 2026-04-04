"""定价领域 bridge 服务。"""

from __future__ import annotations

from datetime import datetime


class LegacyPricingService:
    """桥接现有 PricingAgent，同时收口 bridge 期共享的定价操作。"""

    async def calculate(self, context: dict) -> dict:
        """复用现有 PricingAgent 作为兼容期的统一计算入口。"""
        from agents import get_pricing_agent

        agent = get_pricing_agent()
        return await agent.process(context)

    async def update_job_total_cost(self, job_id: str) -> float:
        """统一汇总 `subgraphs.total_cost`，并回写 `jobs.total_cost`。"""
        from shared.database import get_db
        from shared.models import Job, Subgraph
        from sqlalchemy import func, select, update

        async for db in get_db():
            result = await db.execute(
                select(func.coalesce(func.sum(Subgraph.total_cost), 0)).where(
                    Subgraph.job_id == job_id
                )
            )
            total_cost = float(result.scalar() or 0)

            await db.execute(
                update(Job).where(Job.job_id == job_id).values(
                    total_cost=total_cost,
                    updated_at=datetime.utcnow(),
                )
            )
            await db.commit()
            return total_cost

        raise RuntimeError("shared.database.get_db() did not yield a session")


pricing_service = LegacyPricingService()
