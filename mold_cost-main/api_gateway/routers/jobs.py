"""
任务相关API路由
负责人：人员B2
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


async def _execute_continue_job(orchestrator, job_id: str):
    """
    后台执行任务继续流程
    
    Args:
        orchestrator: OrchestratorAgent 实例
        job_id: 任务ID
    """
    try:
        logger.info(f"[后台任务] 开始继续执行任务: job_id={job_id}")
        
        # 调用 continue_job 方法
        result = await orchestrator.continue_job(job_id)
        
        if result["status"] == "error":
            logger.error(f"[后台任务] 继续执行失败: {result.get('message')}")
        else:
            logger.info(f"[后台任务] 任务继续执行完成: job_id={job_id}")
        
    except Exception as e:
        logger.error(f"[后台任务] 继续执行异常: job_id={job_id}, error={e}", exc_info=True)
        
        # 发布失败消息
        try:
            from shared.progress_publisher import ProgressPublisher
            from shared.progress_stages import ProgressStage, ProgressPercent
            
            progress_publisher = ProgressPublisher()
            progress_publisher.publish_progress(
                job_id=job_id,
                stage=ProgressStage.FAILED,
                progress=0,
                message=f"任务执行失败: {str(e)}",
                details={"source": "jobs_api", "error": str(e)}
            )
        except Exception as pub_error:
            logger.error(f"[后台任务] 发布失败消息时出错: {pub_error}", exc_info=True)

@router.post("/")
async def create_job(
    dwg_file: UploadFile = File(...),
    prt_file: Optional[UploadFile] = File(None)
):
    """
    创建新任务
    - 上传DWG文件（必须）
    - 上传PRT文件（可选）
    """
    return {"job_id": "uuid", "status": "pending"}

@router.get("/{job_id}")
async def get_job(job_id: str):
    """获取任务详情（使用视图确保数据一致性）"""
    try:
        from shared.database import get_db
        from sqlalchemy import text
        
        async for db in get_db():
            # 使用视图查询，确保 total_cost 始终准确
            query = text("""
                SELECT 
                    job_id,
                    dwg_file_name,
                    prt_file_name,
                    status,
                    progress,
                    current_stage,
                    total_cost,
                    total_subgraphs as subgraph_count,
                    material_cost,
                    heat_treatment_cost,
                    processing_cost_total,
                    nc_cost,
                    grinding_cost,
                    wire_cost,
                    error_message,
                    created_at,
                    updated_at,
                    metadata
                FROM v_job_cost_summary
                WHERE job_id = :job_id
            """)
            
            result = await db.execute(query, {"job_id": job_id})
            row = result.mappings().fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
            
            return {
                "job_id": str(row['job_id']),
                "dwg_file_name": row['dwg_file_name'],
                "prt_file_name": row['prt_file_name'],
                "status": row['status'],
                "progress": row['progress'],
                "current_stage": row['current_stage'],
                "total_cost": float(row['total_cost']) if row['total_cost'] else 0.0,
                "subgraph_count": row['subgraph_count'],
                "material_cost": float(row['material_cost']) if row['material_cost'] else 0.0,
                "heat_treatment_cost": float(row['heat_treatment_cost']) if row['heat_treatment_cost'] else 0.0,
                "processing_cost_total": float(row['processing_cost_total']) if row['processing_cost_total'] else 0.0,
                "nc_cost": float(row['nc_cost']) if row['nc_cost'] else 0.0,
                "grinding_cost": float(row['grinding_cost']) if row['grinding_cost'] else 0.0,
                "wire_cost": float(row['wire_cost']) if row['wire_cost'] else 0.0,
                "error_message": row['error_message'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                "metadata": row['metadata']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")

@router.get("/")
async def list_jobs(skip: int = 0, limit: int = 20):
    """获取任务列表"""
    return {"jobs": [], "total": 0}


@router.post("/{job_id}/continue")
async def continue_job(job_id: str):
    """
    用户确认特征识别结果后，继续执行后续流程（异步后台任务）
    
    触发条件：
    - 任务状态为 waiting_for_confirmation
    - 用户在前端检查特征识别结果无误后，点击"开始计算价格"按钮
    
    执行内容：
    - 工艺决策（如果配置）
    - 价格计算
    - 完成任务
    
    立即返回，处理在后台执行，通过 WebSocket 推送进度
    
    Args:
        job_id: 任务ID
    
    Returns:
        {
            "status": "accepted",
            "message": "任务已提交，请通过 WebSocket 监听进度",
            "job_id": "xxx"
        }
    
    示例:
        ```bash
        curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/continue
        ```
    """
    try:
        logger.info(f"收到继续执行请求: job_id={job_id}")
        
        # 导入 Orchestrator
        from agents import get_orchestrator_agent
        
        # 获取 Orchestrator 实例
        orchestrator = get_orchestrator_agent()
        
        # 创建后台任务（不等待完成）
        asyncio.create_task(_execute_continue_job(orchestrator, job_id))
        
        logger.info(f"任务已提交到后台: job_id={job_id}")
        
        # 立即返回
        return {
            "status": "accepted",
            "message": "任务已提交，请通过 WebSocket 监听进度",
            "job_id": job_id
        }
        
    except Exception as e:
        logger.error(f"提交任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")
