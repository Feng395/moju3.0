"""任务创建用例。"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api_gateway.repositories.audit_repository import AuditRepository
from api_gateway.repositories.chat_history_repository import ChatHistoryRepository
from api_gateway.repositories.job_repository import JobRepository
from api_gateway.repositories.snapshot_repository import SnapshotRepository
from api_gateway.utils.encryption import process_file_encryption
from api_gateway.utils.validators import validate_dwg_file, validate_prt_file
from ...core.logging import get_logger

logger = get_logger(__name__)


class CreateJobFromUploadUseCase:
    """负责“上传文件并创建任务”的应用层用例。"""

    def __init__(self):
        self.job_repo = JobRepository()
        self.audit_repo = AuditRepository()
        self.snapshot_repo = SnapshotRepository()
        self.chat_history_repo = ChatHistoryRepository()

    async def execute(
        self,
        db: AsyncSession,
        user_id: str,
        dwg_file: Optional[UploadFile] = None,
        prt_file: Optional[UploadFile] = None,
        encryption_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """创建任务，并保持现有接口返回结构不变。"""
        logger.info("开始创建任务: user_id=%s", user_id)

        # 1. 先校验上传文件，避免无效请求进入事务阶段。
        if not dwg_file and not prt_file:
            raise HTTPException(
                status_code=400,
                detail={"error": "NO_FILE_PROVIDED", "message": "至少需要上传一个文件（DWG 或 PRT）"},
            )

        if dwg_file:
            await validate_dwg_file(dwg_file)
        if prt_file:
            await validate_prt_file(prt_file)

        # 2. 保留现有加密处理入口，后续可独立替换为领域服务。
        if dwg_file:
            dwg_file = await process_file_encryption(dwg_file, encryption_key)
        if prt_file:
            prt_file = await process_file_encryption(prt_file, encryption_key)

        # 3. 文件先落 MinIO，再开始数据库事务。
        dwg_info, prt_info = await self._upload_files(dwg_file, prt_file)
        job_id = str(uuid.uuid4())

        try:
            async with db.begin():
                await self.job_repo.create_job(
                    db=db,
                    job_id=job_id,
                    user_id=user_id,
                    dwg_info=dwg_info,
                    prt_info=prt_info,
                    dwg_filename=dwg_file.filename if dwg_file else None,
                    prt_filename=prt_file.filename if prt_file else None,
                )

                session_name = self._resolve_session_name(dwg_file=dwg_file, prt_file=prt_file)
                await self._create_chat_session(
                    db=db,
                    session_id=job_id,
                    job_id=job_id,
                    user_id=user_id,
                    session_name=session_name,
                )

                snapshot_stats = await self._create_snapshots(db, job_id)
                await self._create_audit_log(
                    db=db,
                    user_id=user_id,
                    job_id=job_id,
                    dwg_file=dwg_file,
                    prt_file=prt_file,
                    dwg_info=dwg_info,
                    prt_info=prt_info,
                    snapshot_stats=snapshot_stats,
                )

            await db.commit()

            # 远端数据库场景下稍等片刻，避免后续异步消费者立刻读不到数据。
            await asyncio.sleep(0.2)
        except Exception as exc:
            logger.error("数据库写入失败: %s", exc)
            await self._rollback_files(dwg_info, prt_info)
            raise HTTPException(
                status_code=500,
                detail={"error": "DATABASE_ERROR", "message": f"数据库写入失败: {str(exc)}"},
            )

        await self._publish_job_message(job_id, user_id)
        logger.info("任务创建完成: job_id=%s", job_id)

        return {
            "job_id": job_id,
            "status": "pending",
            "message": "文件上传成功，任务已创建，正在处理中...",
            "files": {
                "dwg": {
                    "filename": dwg_file.filename if dwg_file else None,
                    "size": dwg_info["file_size"] if dwg_info else None,
                },
                "prt": {
                    "filename": prt_file.filename if prt_file else None,
                    "size": prt_info["file_size"] if prt_info else None,
                },
            },
        }

    async def _upload_files(
        self,
        dwg_file: Optional[UploadFile],
        prt_file: Optional[UploadFile],
    ) -> tuple[Optional[dict], Optional[dict]]:
        """上传文件到 MinIO。"""
        dwg_info = None
        prt_info = None
        minio_client = self._get_minio_client()

        try:
            if dwg_file:
                dwg_info = await minio_client.upload_file(dwg_file, prefix="dwg")
            if prt_file:
                prt_info = await minio_client.upload_file(prt_file, prefix="prt")
        except Exception as exc:
            logger.error("MinIO 上传失败: %s", exc)
            raise HTTPException(
                status_code=500,
                detail={"error": "MINIO_UPLOAD_FAILED", "message": f"文件上传失败: {str(exc)}"},
            )

        return dwg_info, prt_info

    async def _create_chat_session(
        self,
        db: AsyncSession,
        session_id: str,
        job_id: str,
        user_id: str,
        session_name: Optional[str],
    ) -> None:
        """创建与任务绑定的聊天会话。"""
        await self.chat_history_repo.create_session(
            db_session=db,
            session_id=session_id,
            job_id=job_id,
            user_id=user_id,
            session_name=session_name,
            metadata={"created_from": "file_upload", "file_name": session_name},
        )

    async def _create_snapshots(self, db: AsyncSession, job_id: str) -> dict[str, int]:
        """创建初始快照。当前仅保留价格快照。"""
        price_count = await self.snapshot_repo.create_price_snapshots(db, job_id)
        return {"price_items_count": price_count}

    async def _create_audit_log(
        self,
        db: AsyncSession,
        user_id: str,
        job_id: str,
        dwg_file: Optional[UploadFile],
        prt_file: Optional[UploadFile],
        dwg_info: Optional[dict],
        prt_info: Optional[dict],
        snapshot_stats: dict[str, int],
    ) -> None:
        """记录任务创建审计日志。"""
        changes = {
            "dwg_file": {
                "filename": dwg_file.filename if dwg_file else None,
                "size": dwg_info["file_size"] if dwg_info else None,
                "path": dwg_info["object_name"] if dwg_info else None,
            },
            "prt_file": {
                "filename": prt_file.filename if prt_file else None,
                "size": prt_info["file_size"] if prt_info else None,
                "path": prt_info["object_name"] if prt_info else None,
            },
            "snapshots": snapshot_stats,
        }
        await self.audit_repo.create_audit_log(
            db=db,
            user_id=user_id,
            action="file_upload",
            resource_type="job",
            resource_id=job_id,
            changes=changes,
        )

    async def _rollback_files(self, dwg_info: Optional[dict], prt_info: Optional[dict]) -> None:
        """数据库失败时，回滚已上传的文件。"""
        try:
            minio_client = self._get_minio_client()
            if dwg_info:
                minio_client.delete_file(dwg_info["object_name"])
            if prt_info:
                minio_client.delete_file(prt_info["object_name"])
        except Exception as exc:
            logger.error("回滚文件失败: %s", exc)

    async def _publish_job_message(self, job_id: str, user_id: str) -> None:
        """向 RabbitMQ 发送任务创建消息。"""
        try:
            rabbitmq_client = self._get_rabbitmq_client()
            await rabbitmq_client.publish_job_message(
                job_id=job_id,
                user_id=user_id,
                created_at=datetime.now().isoformat(),
            )
        except Exception as exc:
            logger.error("RabbitMQ 消息发送失败: %s", exc)
            logger.warning("任务已创建，但消息发送失败，需要人工补偿: %s", job_id)

    @staticmethod
    def _resolve_session_name(
        dwg_file: Optional[UploadFile],
        prt_file: Optional[UploadFile],
    ) -> Optional[str]:
        """会话名称优先使用 DWG 文件名，否则使用 PRT 文件名。"""
        source_file = dwg_file or prt_file
        if not source_file:
            return None
        filename = source_file.filename or ""
        return filename.rsplit(".", 1)[0] if "." in filename else filename

    @staticmethod
    def _get_minio_client():
        """懒加载 MinIO 客户端，避免导入 use case 时立刻触发外部连接。"""
        from ...infrastructure.storage.minio_client import minio_client

        return minio_client

    @staticmethod
    def _get_rabbitmq_client():
        """懒加载 RabbitMQ 客户端，降低模块导入副作用。"""
        from ...infrastructure.messaging.rabbitmq_client import rabbitmq_client

        return rabbitmq_client
