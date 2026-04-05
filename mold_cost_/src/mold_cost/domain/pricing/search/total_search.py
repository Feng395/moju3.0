"""Full processing cost detail search domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_total_by_job_id",
    "description": "Query full processing cost detail rows by job_id.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID (UUID)"},
            "subgraph_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subgraph ID list (UUID array)",
            },
        },
        "required": ["job_id", "subgraph_ids"],
    },
    "handler": "search_by_job_id",
}


async def search_by_job_id(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Query full cost detail rows for pricing calculations."""
    normalized_subgraph_ids = list(subgraph_ids or [])
    logger.info(
        "Searching total cost details for job_id: %s, subgraph_ids: %s",
        job_id,
        normalized_subgraph_ids,
    )
    cost_details = await pricing_snapshot_search_service.fetch_processing_cost_details(
        job_id=job_id,
        subgraph_ids=normalized_subgraph_ids,
    )
    logger.info("Completed total cost detail search, matched %s rows", len(cost_details))
    return {
        "data_type": "total",
        "job_id": job_id,
        "cost_details": cost_details,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "search_by_job_id", "search_by_job_id_sync"]
