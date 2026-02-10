"""
重算相关API路由
负责人：人员B2

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost_/api_gateway/routers/recalculations.py + mold_cost-main/api_gateway/routers/recalculations.py
- 合并策略：使用 mold_cost_ 为基础，补充 mold_cost-main 的 batch_recalculate 实现
- 主要功能：
  1. 单个子图重算
  2. 批量子图重算（通过消息队列异步处理）
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter(prefix="/api/v1", tags=["recalculations"])

class RecalculationRequest(BaseModel):
    subgraph_id: str
    reason: str
    modifications: Dict[str, Any]

class BatchRecalculationRequest(BaseModel):
    subgraph_ids: List[str]
    reason: str
    apply_new_version: bool = False

@router.post("/jobs/{job_id}/subgraphs/{subgraph_id}/recalculate")
async def recalculate_subgraph(
    job_id: str,
    subgraph_id: str,
    request: RecalculationRequest
):
    """单个子图重算"""
    return {"recalc_id": "uuid", "status": "pending"}

@router.post("/jobs/{job_id}/recalculate/batch")
async def batch_recalculate(
    job_id: str,
    request: BatchRecalculationRequest
):
    """
    批量子图重算
    
    Args:
        job_id: 任务ID
        request: 包含 subgraph_ids, reason, apply_new_version
    
    Returns:
        重算任务状态
    """
    try:
        # 导入必要的模块
        from shared.message_queue import MessageQueue, QUEUE_PRICING_RECALCULATE
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        logger.info(
            f"收到批量重算请求: job_id={job_id}, "
            f"子图数量={len(request.subgraph_ids)}, "
            f"原因={request.reason}"
        )
        
        # 创建消息队列实例
        mq = MessageQueue()
        
        # 发布消息到队列
        await mq.publish(
            queue_name=QUEUE_PRICING_RECALCULATE,
            message={
                "job_id": job_id,
                "subgraph_ids": request.subgraph_ids,
                "user_params": {},
                "reason": request.reason,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        logger.info(f"批量重算任务已发布到队列: job_id={job_id}")
        
        return {
            "status": "accepted",
            "message": "批量重算任务已提交到队列",
            "job_id": job_id,
            "subgraph_count": len(request.subgraph_ids)
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"提交批量重算任务失败: {e}", exc_info=True)
        
        return {
            "status": "error",
            "message": f"提交任务失败: {str(e)}"
        }
