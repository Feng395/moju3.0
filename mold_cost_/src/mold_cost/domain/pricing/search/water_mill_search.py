"""Water mill search domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_water_mill_by_job_id",
    "description": "Query S_water_mill and L_water_mill prices by job_id.",
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
    """Query water mill prices."""
    logger.info("Searching water mill prices for job_id: %s", job_id)
    all_prices = await pricing_snapshot_search_service.fetch_snapshots(
        job_id=job_id,
        categories=("S_water_mill", "L_water_mill"),
        columns=("category", "sub_category", "price", "unit", "min_num"),
    )
    s_water_mill_prices = [item for item in all_prices if item.get("category") == "S_water_mill"]
    l_water_mill_prices = [item for item in all_prices if item.get("category") == "L_water_mill"]
    return {
        "data_type": "water_mill",
        "job_id": job_id,
        "s_water_mill_prices": s_water_mill_prices,
        "l_water_mill_prices": l_water_mill_prices,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "search_by_job_id", "search_by_job_id_sync"]
