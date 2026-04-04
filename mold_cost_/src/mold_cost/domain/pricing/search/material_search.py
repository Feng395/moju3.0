"""材料搜索领域实现。"""

from __future__ import annotations

import asyncio
from typing import Any

from shared.unified_logging import get_logger

from ..services.price_snapshot_search_service import pricing_snapshot_search_service

logger = get_logger(__name__)

MCP_TOOL_META = {
    "name": "search_material_by_job_id",
    "description": "按job_id查询材料价格数据：从job_price_snapshots获取material价格（注意：subgraph_ids参数被忽略，因为材料价格是全局配置）",
    "inputSchema": {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "任务ID (UUID)",
            },
            "subgraph_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "此参数被忽略（为保持接口一致性）",
            },
        },
        "required": ["job_id", "subgraph_ids"],
    },
    "handler": "search_by_job_id",
}


async def search_by_job_id(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """按 job_id 查询材料价格数据。"""
    # 中文注释：material 快照是全局配置，兼容期继续忽略 subgraph_ids。
    logger.info(f"Searching material prices for job_id: {job_id} (subgraph_ids ignored)")
    material_prices = await pricing_snapshot_search_service.fetch_snapshots(
        job_id=job_id,
        categories=("material",),
        columns=("sub_category", "price", "unit"),
    )
    logger.info(f"Found {len(material_prices)} material prices")
    return {
        "data_type": "material",
        "job_id": job_id,
        "material_prices": material_prices,
    }


def search_by_job_id_sync(job_id: str, subgraph_ids: list[str] | None = None) -> dict[str, Any]:
    """同步版本的查询接口。"""
    return asyncio.run(search_by_job_id(job_id, subgraph_ids))
