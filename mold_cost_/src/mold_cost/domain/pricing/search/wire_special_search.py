"""Wire special search domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_wire_special_by_job_id",
    "description": "Query special and rule prices by job_id.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID (UUID)"},
            "subgraph_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ignored; kept for interface compatibility.",
            },
        },
        "required": ["job_id", "subgraph_ids"],
    },
    "handler": "search_by_job_id",
}


async def search_by_job_id(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Query wire special prices."""
    logger.info("Searching wire special prices for job_id: %s", job_id)
    price_data = await pricing_snapshot_search_service.fetch_snapshots(
        job_id=job_id,
        categories=("special", "rule"),
        columns=("category", "sub_category", "price", "unit"),
    )
    special_prices = [item for item in price_data if item.get("category") == "special"]
    rule_prices = [item for item in price_data if item.get("category") == "rule"]
    return {
        "data_type": "wire_special",
        "job_id": job_id,
        "special_prices": special_prices,
        "rule_prices": rule_prices,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "search_by_job_id", "search_by_job_id_sync"]
