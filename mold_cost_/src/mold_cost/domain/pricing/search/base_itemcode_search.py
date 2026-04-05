"""Base itemcode search domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_base_itemcode_by_job_id",
    "description": "Query base itemcode info by job_id and subgraph_ids from subgraphs + features.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "Job ID (UUID)",
            },
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
    """Query base itemcode information."""
    normalized_subgraph_ids = list(subgraph_ids or [])
    logger.info(
        "Searching base itemcode info for job_id: %s, subgraph_ids: %s",
        job_id,
        normalized_subgraph_ids,
    )
    parts = await pricing_snapshot_search_service.fetch_base_itemcode_parts(
        job_id=job_id,
        subgraph_ids=normalized_subgraph_ids,
    )
    logger.info("Completed base itemcode search, matched %s parts", len(parts))
    return {
        "data_type": "base_itemcode",
        "job_id": job_id,
        "parts": parts,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "search_by_job_id", "search_by_job_id_sync"]
