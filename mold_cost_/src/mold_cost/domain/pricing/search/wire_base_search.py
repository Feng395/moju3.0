"""Wire base search domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_wire_by_job_id",
    "description": "Query wire and rule pricing by job_id.",
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
    """Query wire base prices and normalize wire rows to wire_parts."""
    logger.info("Searching wire base prices for job_id: %s", job_id)
    price_data = await pricing_snapshot_search_service.fetch_snapshots(
        job_id=job_id,
        categories=("wire", "rule"),
        columns=("category", "sub_category", "price", "unit", "note", "min_num"),
    )
    wire_prices = [item for item in price_data if item.get("category") == "wire"]
    rule_prices = [item for item in price_data if item.get("category") == "rule"]
    wire_parts = []
    for price_info in wire_prices:
        sub_category = price_info.get("sub_category")
        note = price_info.get("note") or sub_category
        wire_parts.append(
            {
                "name": note,
                "conditions": sub_category,
                "description": note,
                "price": price_info.get("price"),
                "unit": price_info.get("unit"),
                "min_num": price_info.get("min_num"),
            }
        )
    return {
        "data_type": "wire_base",
        "job_id": job_id,
        "wire_parts": wire_parts,
        "rule_prices": rule_prices,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "search_by_job_id", "search_by_job_id_sync"]
