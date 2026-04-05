"""Subgraph total cost summary search domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_subgraphs_cost_by_job_id",
    "description": "Query final subgraph cost summary after pricing calculations.",
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
    "depends_on": ["price_wire_total", "price_water_mill_total"],
}


async def search_by_job_id(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Query aggregated subgraph-level cost summary."""
    normalized_subgraph_ids = list(subgraph_ids or [])
    logger.info(
        "Searching subgraph cost summary for job_id: %s, subgraph_ids: %s",
        job_id,
        normalized_subgraph_ids,
    )
    cost_summary = await pricing_snapshot_search_service.fetch_subgraph_cost_summary(
        job_id=job_id,
        subgraph_ids=normalized_subgraph_ids,
    )
    logger.info("Completed subgraph cost summary search, matched %s subgraphs", len(cost_summary))
    return {
        "data_type": "subgraphs_cost",
        "job_id": job_id,
        "cost_summary": cost_summary,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "search_by_job_id", "search_by_job_id_sync"]
