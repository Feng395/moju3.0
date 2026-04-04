"""
特征识别相关接口
负责人：后端同事

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/api_gateway/routers/features.py
- 合并策略：复制 mold_cost-main 版本（mold_cost_ 无此文件）
- 主要功能：
  1. 重新执行特征识别（异步后台任务）
  2. 查询特征识别状态
  3. 支持批量处理指定子图
  4. 通过 WebSocket 推送进度
"""
from shared.unified_logging import get_logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import logging

from mold_cost.application.use_cases.features import ReprocessFeaturesUseCase

logger = get_logger(__name__)

router = APIRouter(prefix="/api/features", tags=["features"])

class ReprocessRequest(BaseModel):
    """重新执行特征识别请求"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "4fada577-6d86-4b8f-8c2e-0f991fd65a3c",
                "subgraph_ids": ["sub_001", "sub_002"],
                "force_reprocess": True,
            }
        }
    )

    job_id: str
    subgraph_ids: List[str]
    force_reprocess: Optional[bool] = True


@router.post("/reprocess")
async def reprocess_features(request: ReprocessRequest):
    """
    重新执行特征识别（异步后台任务）
    
    用于用户修改参数后重新处理部分子图
    立即返回，处理在后台执行，通过 WebSocket 推送进度
    
    Args:
        request: 包含 job_id 和 subgraph_ids 的请求体
    
    Returns:
        {
            "status": "accepted",
            "message": "特征识别任务已提交，请通过 WebSocket 监听进度",
            "job_id": "xxx",
            "subgraph_count": 2
        }
    
    示例:
        ```bash
        curl -X POST http://localhost:8000/api/features/reprocess \
          -H "Content-Type: application/json" \
          -d '{
            "job_id": "xxx",
            "subgraph_ids": ["sub_001", "sub_002"]
          }'
        ```
    """
    try:
        logger.info(
            f"收到特征识别请求: job_id={request.job_id}, "
            f"子图数量={len(request.subgraph_ids)}, "
            f"强制重新处理={request.force_reprocess}"
        )
        
        # 中文注释：路由层只负责参数校验与转发，后台调度统一交给应用层用例。
        result = await ReprocessFeaturesUseCase().submit(
            job_id=request.job_id,
            subgraph_ids=request.subgraph_ids,
            force_reprocess=request.force_reprocess,
        )
        logger.info(f"特征识别任务已提交到后台: job_id={request.job_id}")
        return result
        
    except Exception as e:
        logger.error(f"提交特征识别任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")


@router.get("/status/{job_id}")
async def get_features_status(job_id: str):
    """
    查询特征识别状态
    
    Args:
        job_id: 任务ID
    
    Returns:
        所有子图的特征识别状态
    """
    try:
        from shared.database import get_db
        from shared.models import Subgraph, Feature
        from sqlalchemy import select
        
        async for db in get_db():
            # 查询所有子图及其特征
            result = await db.execute(
                select(Subgraph, Feature)
                .outerjoin(Feature, Subgraph.subgraph_id == Feature.subgraph_id)
                .where(Subgraph.job_id == job_id)
            )
            
            rows = result.all()
            
            subgraphs_data = []
            for subgraph, feature in rows:
                subgraphs_data.append({
                    "subgraph_id": subgraph.subgraph_id,
                    "part_code": subgraph.part_code,
                    "has_features": feature is not None,
                    "features": {
                        "length_mm": feature.length_mm if feature else None,
                        "width_mm": feature.width_mm if feature else None,
                        "thickness_mm": feature.thickness_mm if feature else None,
                        "top_view_wire_length": feature.top_view_wire_length if feature else None,
                    } if feature else None
                })
            
            return {
                "status": "ok",
                "job_id": job_id,
                "total": len(subgraphs_data),
                "subgraphs": subgraphs_data
            }
            
    except Exception as e:
        logger.error(f"查询特征状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
