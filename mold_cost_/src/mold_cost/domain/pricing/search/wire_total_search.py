"""Wire-total cost detail search domain implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_total_by_job_id",
    "description": "Query wire-related processing cost details by job_id.",
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

_WIRE_TOTAL_FIELDS = (
    "subgraph_id",
    "weight",
    "basic_processing_cost",
    "special_base_cost",
    "standard_base_cost",
    "material_additional_cost",
    "material_cost",
    "heat_treatment_cost",
    "calculation_steps",
)


async def search_by_job_id(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Query the reduced cost detail shape used by wire-total calculations."""
    normalized_subgraph_ids = list(subgraph_ids or [])
    logger.info(
        "Searching wire total cost details for job_id: %s, subgraph_ids: %s",
        job_id,
        normalized_subgraph_ids,
    )
    raw_cost_details = await pricing_snapshot_search_service.fetch_processing_cost_details(
        job_id=job_id,
        subgraph_ids=normalized_subgraph_ids,
    )
    cost_details = [
        {field: item.get(field, [] if field == "calculation_steps" else 0.0) for field in _WIRE_TOTAL_FIELDS}
        for item in raw_cost_details
    ]
    logger.info("Completed wire total cost detail search, matched %s rows", len(cost_details))
    return {
        "data_type": "total",
        "job_id": job_id,
        "cost_details": cost_details,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """Sync compatibility wrapper."""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))


__all__ = ["MCP_TOOL_META", "search_by_job_id", "search_by_job_id_sync"]
