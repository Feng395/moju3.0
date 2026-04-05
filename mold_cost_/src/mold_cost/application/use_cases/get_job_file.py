"""任务文件访问用例。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logging import get_logger
from ...infrastructure.db.repositories.job_repository import JobRepository

logger = get_logger(__name__)


class GetJobFileUseCase:
    """负责任务文件下载和签名链接生成。"""

    def __init__(self):
        self.job_repo = JobRepository()

    async def get_file(self, db: AsyncSession, job_id: str, file_type: str, user_id: str) -> bytes:
        """读取任务文件内容。"""
        job = await self._get_authorized_job(db, job_id, user_id)
        file_path = self._resolve_file_path(job, file_type)
        minio_client = self._get_minio_client()

        try:
            return minio_client.get_file(file_path)
        except Exception as exc:
            logger.error("文件下载失败: %s", exc)
            raise HTTPException(
                status_code=500,
                detail={"error": "FILE_DOWNLOAD_FAILED", "message": f"文件下载失败: {str(exc)}"},
            )

    async def get_presigned_url(
        self,
        db: AsyncSession,
        job_id: str,
        file_type: str,
        user_id: str,
        expires_hours: int = 24,
    ) -> str:
        """生成任务文件下载链接。"""
        job = await self._get_authorized_job(db, job_id, user_id)
        file_path = self._resolve_file_path(job, file_type)
        minio_client = self._get_minio_client()

        try:
            return minio_client.generate_presigned_url(
                object_name=file_path,
                expires=timedelta(hours=expires_hours),
            )
        except Exception as exc:
            logger.error("预签名 URL 生成失败: %s", exc)
            raise HTTPException(
                status_code=500,
                detail={"error": "URL_GENERATION_FAILED", "message": f"URL 生成失败: {str(exc)}"},
            )

    async def get_file_by_path(self, file_path: str) -> bytes:
        """内部场景下按对象路径直接取文件。"""
        try:
            minio_client = self._get_minio_client()
            return minio_client.get_file(file_path)
        except Exception as exc:
            logger.error("按路径下载文件失败: %s", exc)
            raise Exception(f"文件下载失败: {str(exc)}")

    async def _get_authorized_job(self, db: AsyncSession, job_id: str, user_id: str):
        """统一封装任务存在性与权限检查。"""
        job = await self.job_repo.get_job_by_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND", "message": "任务不存在"})
        if str(job.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail={"error": "PERMISSION_DENIED", "message": "无权访问此文件"})
        return job

    @staticmethod
    def _resolve_file_path(job, file_type: str) -> str:
        """根据文件类型解析任务上的对象路径。"""
        if file_type == "dwg":
            file_path = job.dwg_file_path
        elif file_type == "prt":
            file_path = job.prt_file_path
        else:
            raise HTTPException(
                status_code=400,
                detail={"error": "INVALID_FILE_TYPE", "message": "文件类型必须是 dwg 或 prt"},
            )

        if not file_path:
            raise HTTPException(
                status_code=404,
                detail={"error": "FILE_NOT_FOUND", "message": f"任务中没有 {file_type.upper()} 文件"},
            )
        return file_path

    @staticmethod
    def _get_minio_client():
        """懒加载 MinIO 客户端，避免模块导入即连接外部服务。"""
        from ...infrastructure.storage.minio_client import minio_client

        return minio_client
