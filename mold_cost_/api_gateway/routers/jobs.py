"""
任务管理路由 (Controller层)
处理HTTP请求和响应
负责人：ZZH

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost_/api_gateway/routers/jobs.py + mold_cost-main/api_gateway/routers/jobs.py
- 合并策略：保留 mold_cost_ 为基础，补充 mold_cost-main 的重要路由
- 主要功能：
  1. 文件上传和任务创建 (mold_cost_)
  2. 任务状态查询 (mold_cost_)
  3. 价格快照查询 (mold_cost_)
  4. 工艺快照查询 (mold_cost_)
  5. 文件下载和预签名URL生成 (mold_cost_)
  6. 获取任务详情（使用视图）(mold_cost-main)
  7. 任务列表查询 (mold_cost-main)
  8. 继续执行任务（异步后台）(mold_cost-main)
- 路由端点：
  - POST /jobs/upload - 上传文件创建任务
  - GET /jobs/{job_id}/status - 查询任务状态
  - GET /jobs/{job_id}/snapshots/prices - 查询价格快照
  - GET /jobs/{job_id}/snapshots/processes - 查询工艺快照
  - GET /jobs/{job_id}/files/{file_type}/download - 下载文件
  - GET /jobs/{job_id}/files/{file_type}/url - 获取预签名URL
  - GET /jobs/{job_id} - 获取任务详情（使用视图）
  - GET /jobs/ - 获取任务列表
  - POST /jobs/{job_id}/continue - 继续执行任务
"""
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
import io

from shared.database import get_db
from ..auth import get_current_user
from ..services.job_service import JobService
from ..services.file_service import FileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload")
async def upload_files(
    dwg_file: Optional[UploadFile] = File(None),
    prt_file: Optional[UploadFile] = File(None),
    encryption_key: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上传DWG/PRT文件并创建任务
    
    Args:
        dwg_file: DWG文件（可选，但至少要有一个文件）
        prt_file: PRT文件（可选）
        encryption_key: 加密密钥（预留，第一期不使用）
        current_user: 当前用户（从JWT获取）
        db: 数据库会话
    
    Returns:
        {
            "job_id": "uuid",
            "status": "pending",
            "message": "文件上传成功，任务已创建"
        }
    """
    try:
        job_service = JobService()
        
        result = await job_service.create_job_from_upload(
            db=db,
            user_id=current_user["user_id"],
            dwg_file=dwg_file,
            prt_file=prt_file,
            encryption_key=encryption_key
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 文件上传异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"服务器内部错误: {str(e)}"
            }
        )


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    查询任务状态
    
    Args:
        job_id: 任务ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        任务状态信息
    """
    try:
        job_service = JobService()
        
        result = await job_service.get_job_status(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"]
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 查询任务状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"查询失败: {str(e)}"
            }
        )


@router.get("/{job_id}/snapshots/prices")
async def get_job_price_snapshots(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    查询任务的价格快照
    
    Args:
        job_id: 任务ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        价格快照列表
    """
    try:
        job_service = JobService()
        
        result = await job_service.get_price_snapshots(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"]
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 查询价格快照失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)}
        )


@router.get("/{job_id}/snapshots/processes")
async def get_job_process_snapshots(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    查询任务的工艺规则快照
    
    Args:
        job_id: 任务ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        工艺规则快照列表
    """
    try:
        job_service = JobService()
        
        result = await job_service.get_process_snapshots(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"]
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 查询工艺规则快照失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)}
        )



@router.get("/{job_id}/files/{file_type}/download")
async def download_job_file(
    job_id: str,
    file_type: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    下载任务文件
    
    Args:
        job_id: 任务ID
        file_type: 文件类型 ("dwg" 或 "prt")
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        文件流
    """
    try:
        file_service = FileService()
        
        # 获取文件内容
        file_content = await file_service.get_job_file(
            db=db,
            job_id=job_id,
            file_type=file_type.lower(),
            user_id=current_user["user_id"]
        )
        
        # 确定文件扩展名和MIME类型
        if file_type.lower() == "dwg":
            media_type = "application/acad"
            extension = "dwg"
        elif file_type.lower() == "prt":
            media_type = "application/octet-stream"
            extension = "prt"
        else:
            raise HTTPException(400, detail="Invalid file type")
        
        # 返回文件流
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={job_id}.{extension}"
            }
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 文件下载失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "DOWNLOAD_FAILED", "message": str(e)}
        )


@router.get("/{job_id}/files/{file_type}/url")
async def get_job_file_url(
    job_id: str,
    file_type: str,
    expires_hours: int = 24,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务文件的预签名下载URL
    
    Args:
        job_id: 任务ID
        file_type: 文件类型 ("dwg" 或 "prt")
        expires_hours: URL过期时间（小时，默认24小时）
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        {
            "url": "预签名URL",
            "expires_in": 86400,
            "file_type": "dwg"
        }
    """
    try:
        file_service = FileService()
        
        url = await file_service.get_job_file_url(
            db=db,
            job_id=job_id,
            file_type=file_type.lower(),
            user_id=current_user["user_id"],
            expires_hours=expires_hours
        )
        
        return {
            "url": url,
            "expires_in": expires_hours * 3600,
            "file_type": file_type.lower()
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 获取文件URL失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "URL_GENERATION_FAILED", "message": str(e)}
        )



# 🆕 补充来自 mold_cost-main 的路由

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


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务详情（使用视图确保数据一致性）
    
    来自 mold_cost-main，使用 v_job_cost_summary 视图
    """
    try:
        from sqlalchemy import text
        
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
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务列表
    
    来自 mold_cost-main
    """
    # TODO: 实现任务列表查询
    return {"jobs": [], "total": 0}


@router.post("/{job_id}/continue")
async def continue_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    用户确认特征识别结果后，继续执行后续流程（异步后台任务）
    
    来自 mold_cost-main
    
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
        curl -X POST http://localhost:8211/jobs/{job_id}/continue
        ```
    """
    try:
        import asyncio
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
