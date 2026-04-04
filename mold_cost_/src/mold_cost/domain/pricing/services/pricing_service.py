"""定价领域桥接服务。"""

from __future__ import annotations


class LegacyPricingService:
    """桥接现有 PricingAgent。"""

    async def calculate(self, context: dict) -> dict:
        from agents import get_pricing_agent

        agent = get_pricing_agent()
        return await agent.process(context)


pricing_service = LegacyPricingService()
