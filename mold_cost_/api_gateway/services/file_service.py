"""文件服务兼容层。

当前文件保留旧导入路径，内部改为调用应用层 use case。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.application.use_cases import GetJobFileUseCase  # noqa: E402


class FileService:
    """兼容旧接口的文件服务外壳。"""

    def __init__(self):
        self.use_case = GetJobFileUseCase()

    async def get_job_file(self, db: AsyncSession, job_id: str, file_type: str, user_id: str) -> bytes:
        """读取任务文件内容。"""
        return await self.use_case.get_file(db=db, job_id=job_id, file_type=file_type, user_id=user_id)

    async def get_job_file_url(
        self,
        db: AsyncSession,
        job_id: str,
        file_type: str,
        user_id: str,
        expires_hours: int = 24,
    ) -> str:
        """获取任务文件的预签名下载地址。"""
        return await self.use_case.get_presigned_url(
            db=db,
            job_id=job_id,
            file_type=file_type,
            user_id=user_id,
            expires_hours=expires_hours,
        )

    async def get_file_by_path(self, file_path: str) -> bytes:
        """内部按对象路径直接读取文件。"""
        return await self.use_case.get_file_by_path(file_path)
