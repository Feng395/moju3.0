"""任务管理路由。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.unified_logging import get_logger

from ....application.use_cases import (
    ContinueJobUseCase,
    CreateJobFromUploadUseCase,
    GetJobDetailUseCase,
    GetJobFileUseCase,
    GetJobStatusUseCase,
    GetPriceSnapshotsUseCase,
    GetProcessSnapshotsUseCase,
)
from ..dependencies.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])
router_legacy = APIRouter(prefix="/api/jobs", tags=["jobs-legacy"])


class JobService:
    """兼容旧路由 monkeypatch 方式的 src-owned 任务服务外壳。"""

    async def create_job_from_upload(self, *, db, user_id, dwg_file=None, prt_file=None, encryption_key=None):
        return await CreateJobFromUploadUseCase().execute(
            db=db,
            user_id=user_id,
            dwg_file=dwg_file,
            prt_file=prt_file,
            encryption_key=encryption_key,
        )

    async def get_job_status(self, *, db, job_id: str, user_id: str):
        return await GetJobStatusUseCase().execute(db=db, job_id=job_id, user_id=user_id)

    async def get_price_snapshots(self, *, db, job_id: str, user_id: str):
        return await GetPriceSnapshotsUseCase().execute(db=db, job_id=job_id, user_id=user_id)

    async def get_process_snapshots(self, *, db, job_id: str, user_id: str):
        return await GetProcessSnapshotsUseCase().execute(db=db, job_id=job_id, user_id=user_id)

    async def get_job_detail(self, *, db, job_id: str, user_id: str):
        return await GetJobDetailUseCase().execute(db=db, job_id=job_id, user_id=user_id)

    async def submit_continue_job(self, job_id: str):
        return await ContinueJobUseCase().submit(job_id)


@router.post("/upload")
async def upload_files(
    dwg_file: Optional[UploadFile] = File(None),
    prt_file: Optional[UploadFile] = File(None),
    encryption_key: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文件并创建任务。"""
    try:
        return await JobService().create_job_from_upload(
            db=db,
            user_id=current_user["user_id"],
            dwg_file=dwg_file,
            prt_file=prt_file,
            encryption_key=encryption_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("文件上传异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"服务器内部错误: {exc}",
            },
        ) from exc


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询任务状态。"""
    try:
        return await JobService().get_job_status(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("查询任务状态失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"查询失败: {exc}",
            },
        ) from exc


@router.get("/{job_id}/snapshots/prices")
async def get_job_price_snapshots(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询任务价格快照。"""
    try:
        return await JobService().get_price_snapshots(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("查询价格快照失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(exc)},
        ) from exc


@router.get("/{job_id}/snapshots/processes")
async def get_job_process_snapshots(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询任务工艺快照。"""
    try:
        return await JobService().get_process_snapshots(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("查询工艺快照失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(exc)},
        ) from exc


@router.get("/{job_id}/files/{file_type}/download")
async def download_job_file(
    job_id: str,
    file_type: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下载任务文件。"""
    try:
        file_content = await GetJobFileUseCase().get_file(
            db=db,
            job_id=job_id,
            file_type=file_type.lower(),
            user_id=current_user["user_id"],
        )

        if file_type.lower() == "dwg":
            media_type = "application/acad"
            extension = "dwg"
        elif file_type.lower() == "prt":
            media_type = "application/octet-stream"
            extension = "prt"
        else:
            raise HTTPException(400, detail="Invalid file type")

        return Response(
            content=file_content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={job_id}.{extension}"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("文件下载失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "DOWNLOAD_FAILED", "message": str(exc)},
        ) from exc


@router.get("/{job_id}/files/{file_type}/url")
async def get_job_file_url(
    job_id: str,
    file_type: str,
    expires_hours: int = 24,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务文件预签名下载链接。"""
    try:
        url = await GetJobFileUseCase().get_presigned_url(
            db=db,
            job_id=job_id,
            file_type=file_type.lower(),
            user_id=current_user["user_id"],
            expires_hours=expires_hours,
        )

        return {
            "url": url,
            "expires_in": expires_hours * 3600,
            "file_type": file_type.lower(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("获取文件 URL 失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "URL_GENERATION_FAILED", "message": str(exc)},
        ) from exc


@router.get("/{job_id}")
@router_legacy.get("/{job_id}")
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """读取任务详情。"""
    try:
        return await JobService().get_job_detail(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("获取任务详情失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {exc}") from exc


@router.get("/")
@router_legacy.get("/")
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表。"""
    del skip, limit, current_user, db
    return {"jobs": [], "total": 0}


@router.post("/")
@router_legacy.post("/")
async def create_job(
    dwg_file: UploadFile = File(...),
    prt_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标准 REST 风格的创建任务入口。"""
    try:
        return await JobService().create_job_from_upload(
            db=db,
            user_id=current_user["user_id"],
            dwg_file=dwg_file,
            prt_file=prt_file,
            encryption_key=None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("创建任务失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"创建任务失败: {exc}",
            },
        ) from exc


@router.post("/{job_id}/continue")
@router_legacy.post("/{job_id}/continue")
async def continue_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """用户确认后继续执行任务。"""
    try:
        del current_user
        logger.info("收到继续执行请求: job_id=%s", job_id)
        return await JobService().submit_continue_job(job_id)
    except Exception as exc:
        logger.error("提交继续执行任务失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交任务失败: {exc}") from exc


def get_jobs_router():
    """Return the primary jobs router."""
    return router


def get_legacy_jobs_router():
    """Return the legacy-compatible jobs router."""
    return router_legacy


__all__ = [
    "JobService",
    "continue_job",
    "get_jobs_router",
    "get_legacy_jobs_router",
    "router",
    "router_legacy",
]
