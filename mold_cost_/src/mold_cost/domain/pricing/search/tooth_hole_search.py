"""Tooth hole search domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_tooth_hole_by_job_id",
    "description": "Query tooth_hole, screw, and stop_screw prices by job_id.",
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
    """Query tooth hole and screw prices."""
    logger.info("Searching tooth_hole/screw prices for job_id: %s", job_id)
    all_prices = await pricing_snapshot_search_service.fetch_snapshots(
        job_id=job_id,
        categories=("tooth_hole", "screw", "stop_screw"),
        columns=("category", "sub_category", "price", "unit", "min_num"),
    )
    tooth_hole_prices = [item for item in all_prices if item.get("category") == "tooth_hole"]
    screw_prices = [item for item in all_prices if item.get("category") == "screw"]
    stop_screw_prices = [item for item in all_prices if item.get("category") == "stop_screw"]
    return {
        "data_type": "tooth_hole",
        "job_id": job_id,
        "tooth_hole_prices": tooth_hole_prices,
        "screw_prices": screw_prices,
        "stop_screw_prices": stop_screw_prices,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "search_by_job_id", "search_by_job_id_sync"]
