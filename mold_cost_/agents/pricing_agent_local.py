"""Compatibility wrapper for the local pricing runtime."""

from __future__ import annotations

import logging
from typing import Any

from mold_cost.domain.pricing.services.pricing_service import pricing_service


class PricingAgentLocal:
    """Keep the legacy agent contract while delegating to the pricing service."""

    def __init__(self, progress_publisher: Any | None = None):
        self.name = "PricingAgentLocal"
        self.logger = logging.getLogger(f"Agent.{self.name}")
        self.progress_publisher = progress_publisher
        self.logger.info("PricingAgentLocal initialized in compatibility-wrapper mode")

    async def process(self, context: dict[str, Any]) -> dict[str, Any]:
        request_context = dict(context)
        request_context.setdefault("_progress_publisher", self.progress_publisher)
        return await pricing_service.calculate(request_context)

    async def calculate_batch(self, context: dict[str, Any]) -> dict[str, Any]:
        return await self.process(context)
