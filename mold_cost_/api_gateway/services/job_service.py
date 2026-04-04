"""任务服务兼容层。

当前文件保留为 API Gateway 的稳定入口，
内部实现已经转发到 `src/mold_cost/application/use_cases`。
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.application.use_cases import (  # noqa: E402
    CreateJobFromUploadUseCase,
    GetJobStatusUseCase,
    GetPriceSnapshotsUseCase,
    GetProcessSnapshotsUseCase,
)


class JobService:
    """兼容旧接口的任务服务外壳。"""

    def __init__(self):
        # 中文注释：这里明确聚合 use case，避免 router 直接依赖 application 层细节。
        self.create_job_use_case = CreateJobFromUploadUseCase()
        self.get_status_use_case = GetJobStatusUseCase()
        self.get_price_snapshots_use_case = GetPriceSnapshotsUseCase()
        self.get_process_snapshots_use_case = GetProcessSnapshotsUseCase()

    async def create_job_from_upload(
        self,
        db: AsyncSession,
        user_id: str,
        dwg_file: Optional[UploadFile] = None,
        prt_file: Optional[UploadFile] = None,
        encryption_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """创建任务。"""
        return await self.create_job_use_case.execute(
            db=db,
            user_id=user_id,
            dwg_file=dwg_file,
            prt_file=prt_file,
            encryption_key=encryption_key,
        )

    async def get_job_status(self, db: AsyncSession, job_id: str, user_id: str) -> dict[str, Any]:
        """查询任务状态。"""
        return await self.get_status_use_case.execute(db=db, job_id=job_id, user_id=user_id)

    async def get_price_snapshots(self, db: AsyncSession, job_id: str, user_id: str) -> dict[str, Any]:
        """查询价格快照。"""
        return await self.get_price_snapshots_use_case.execute(db=db, job_id=job_id, user_id=user_id)

    async def get_process_snapshots(self, db: AsyncSession, job_id: str, user_id: str) -> dict[str, Any]:
        """查询工艺规则快照。"""
        return await self.get_process_snapshots_use_case.execute(db=db, job_id=job_id, user_id=user_id)
