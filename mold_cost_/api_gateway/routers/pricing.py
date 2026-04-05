"""Pricing related legacy API routes."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from mold_cost.domain.pricing.services.pricing_service import pricing_service
from shared.database import get_db
from shared.message_queue import MessageQueue, QUEUE_PRICING_RECALCULATE
from shared.unified_logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


async def _execute_pricing_calculation(
    job_id: str,
    subgraph_ids: List[str],
    user_params: Dict[str, Any],
):
    """Fallback background execution when the queue is unavailable."""
    try:
        logger.info("Background pricing started: job_id=%s", job_id)
        result = await pricing_service.calculate_batch(
            {
                "job_id": job_id,
                "subgraph_ids": subgraph_ids,
                "user_params": user_params,
            }
        )
        logger.info(
            "Background pricing finished: job_id=%s status=%s total_cost=%s",
            job_id,
            result.get("status"),
            result.get("total_cost"),
        )
    except Exception as exc:
        logger.error("Background pricing failed: job_id=%s error=%s", job_id, exc, exc_info=True)


class RecalculateRequest(BaseModel):
    """Pricing recalculation request payload."""

    job_id: str
    subgraph_ids: List[str]
    user_params: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "4fada577-6d86-4b8f-8c2e-0f991fd65a3c",
                "subgraph_ids": ["sub_001"],
                "user_params": {"material": "SKD11", "material_price_override": 50.0},
            }
        }


@router.post("/recalculate")
async def recalculate_pricing(request: RecalculateRequest):
    """Submit pricing recalculation through the queue, with local fallback."""
    logger.info(
        "Received pricing request: job_id=%s subgraph_count=%s",
        request.job_id,
        len(request.subgraph_ids),
    )

    try:
        mq = MessageQueue()
        await mq.publish(
            queue_name=QUEUE_PRICING_RECALCULATE,
            message={
                "job_id": request.job_id,
                "subgraph_ids": request.subgraph_ids,
                "user_params": request.user_params or {},
                "timestamp": datetime.now().isoformat(),
            },
        )
        return {
            "status": "accepted",
            "message": "价格计算任务已提交到队列，请通过 WebSocket 监听进度",
            "job_id": request.job_id,
            "subgraph_count": len(request.subgraph_ids),
        }
    except Exception as exc:
        logger.error("Queue pricing submission failed: %s", exc, exc_info=True)
        logger.warning("Queue unavailable, falling back to local pricing execution")

        try:
            asyncio.create_task(
                _execute_pricing_calculation(
                    job_id=request.job_id,
                    subgraph_ids=request.subgraph_ids,
                    user_params=request.user_params or {},
                )
            )
            return {
                "status": "accepted",
                "message": "价格计算任务已提交（直接执行模式），请通过 WebSocket 监听进度",
                "job_id": request.job_id,
                "subgraph_count": len(request.subgraph_ids),
            }
        except Exception as fallback_error:
            logger.error("Local fallback pricing submission failed: %s", fallback_error, exc_info=True)
            raise HTTPException(status_code=500, detail=f"提交任务失败: {exc}") from fallback_error


@router.get("/status/{job_id}")
async def get_pricing_status(job_id: str):
    """Query pricing status by job."""
    try:
        async for db in get_db():
            query = text(
                """
                SELECT
                    s.subgraph_id,
                    s.part_code,
                    pr.total_cost,
                    pr.material_cost,
                    pr.nc_cost,
                    pr.wire_cost,
                    pr.created_at
                FROM subgraphs s
                LEFT JOIN pricing_results pr ON s.subgraph_id = pr.subgraph_id
                WHERE s.job_id = :job_id
                ORDER BY s.part_code
                """
            )
            result = await db.execute(query, {"job_id": job_id})
            rows = result.fetchall()

            subgraphs_data = []
            total_cost = 0.0
            for row in rows:
                has_pricing = row.total_cost is not None
                if has_pricing:
                    total_cost += row.total_cost
                subgraphs_data.append(
                    {
                        "subgraph_id": row.subgraph_id,
                        "part_code": row.part_code,
                        "has_pricing": has_pricing,
                        "pricing": {
                            "total_cost": row.total_cost,
                            "material_cost": row.material_cost,
                            "nc_cost": row.nc_cost,
                            "wire_cost": row.wire_cost,
                            "calculated_at": row.created_at.isoformat() if row.created_at else None,
                        }
                        if has_pricing
                        else None,
                    }
                )

            return {
                "status": "ok",
                "job_id": job_id,
                "total": len(subgraphs_data),
                "total_cost": total_cost,
                "subgraphs": subgraphs_data,
            }
    except Exception as exc:
        logger.error("Pricing status query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {exc}") from exc


@router.get("/summary/{job_id}")
async def get_pricing_summary(job_id: str):
    """Query pricing summary by job."""
    try:
        async for db in get_db():
            query = text(
                """
                SELECT
                    COUNT(*) as total_subgraphs,
                    COUNT(pr.subgraph_id) as priced_subgraphs,
                    SUM(pr.total_cost) as total_cost,
                    SUM(pr.material_cost) as total_material_cost,
                    SUM(pr.nc_cost) as total_nc_cost,
                    SUM(pr.wire_cost) as total_wire_cost
                FROM subgraphs s
                LEFT JOIN pricing_results pr ON s.subgraph_id = pr.subgraph_id
                WHERE s.job_id = :job_id
                """
            )
            result = await db.execute(query, {"job_id": job_id})
            row = result.fetchone()

            return {
                "status": "ok",
                "job_id": job_id,
                "summary": {
                    "total_subgraphs": row.total_subgraphs,
                    "priced_subgraphs": row.priced_subgraphs,
                    "pending_subgraphs": row.total_subgraphs - row.priced_subgraphs,
                    "total_cost": float(row.total_cost) if row.total_cost else 0.0,
                    "breakdown": {
                        "material_cost": float(row.total_material_cost) if row.total_material_cost else 0.0,
                        "nc_cost": float(row.total_nc_cost) if row.total_nc_cost else 0.0,
                        "wire_cost": float(row.total_wire_cost) if row.total_wire_cost else 0.0,
                    },
                },
            }
    except Exception as exc:
        logger.error("Pricing summary query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {exc}") from exc

