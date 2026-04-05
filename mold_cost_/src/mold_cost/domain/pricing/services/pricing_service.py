"""Pricing domain bridge service."""

from __future__ import annotations

from mold_cost.infrastructure.db.repositories.script_db import db


class LegacyPricingService:
    """Keep the pricing-agent compatibility entrypoint while shrinking infra bridges."""

    async def calculate(self, context: dict) -> dict:
        """Reuse the current PricingAgent as the temporary orchestration entrypoint."""
        from agents import get_pricing_agent

        agent = get_pricing_agent()
        return await agent.process(context)

    async def update_job_total_cost(self, job_id: str) -> float:
        """Aggregate `subgraphs.total_cost` and write back to `jobs.total_cost`."""
        query_sql = """
            SELECT COALESCE(SUM(total_cost), 0) AS total_cost
            FROM subgraphs
            WHERE job_id = $1::uuid
        """
        row = await db.fetch_one(query_sql, job_id)
        total_cost = float((row or {}).get("total_cost", 0) or 0)

        update_sql = """
            UPDATE jobs
            SET
                total_cost = $2,
                updated_at = NOW()
            WHERE job_id = $1::uuid
        """
        await db.execute(update_sql, job_id, total_cost)
        return total_cost


pricing_service = LegacyPricingService()
