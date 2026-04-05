"""Compatibility wrapper for MCP-facing pricing execution."""

from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from mold_cost.domain.pricing.services.pricing_service import pricing_service


class PricingAgent(BaseAgent):
    """Keep the historical agent contract while delegating to domain orchestration."""

    def __init__(self, price_search_mcp_client: Any, progress_publisher: Any = None):
        super().__init__("PricingAgent")
        self.version = "2.1.0"
        self.price_search_mcp = price_search_mcp_client
        self.progress_publisher = progress_publisher

    async def process(self, context: dict[str, Any]) -> dict[str, Any]:
        service_context = dict(context)
        service_context.setdefault("_progress_publisher", self.progress_publisher)
        return await pricing_service.calculate(service_context)

    async def calculate_batch(self, context: dict[str, Any]) -> dict[str, Any]:
        return await self.process(context)

