"""任务数据访问适配层。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class JobRepository:
    """将任务仓储从 application/use_cases 中剥离出来的适配器。"""

    async def create_job(
        self,
        db: AsyncSession,
        job_id: str,
        user_id: str,
        dwg_info: Optional[Dict[str, Any]] = None,
        prt_info: Optional[Dict[str, Any]] = None,
        dwg_filename: Optional[str] = None,
        prt_filename: Optional[str] = None,
    ) -> None:
        from api_gateway.repositories.job_repository import JobRepository as LegacyJobRepository

        return await LegacyJobRepository.create_job(
            db=db,
            job_id=job_id,
            user_id=user_id,
            dwg_info=dwg_info,
            prt_info=prt_info,
            dwg_filename=dwg_filename,
            prt_filename=prt_filename,
        )

    async def get_job_by_id(self, db: AsyncSession, job_id: str):
        from api_gateway.repositories.job_repository import JobRepository as LegacyJobRepository

        return await LegacyJobRepository.get_job_by_id(db, job_id)

    async def get_job_summary(self, db: AsyncSession, job_id: str) -> Optional[Dict[str, Any]]:
        from api_gateway.repositories.job_repository import JobRepository as LegacyJobRepository

        return await LegacyJobRepository.get_job_summary(db, job_id)

    async def update_job_status(
        self,
        db: AsyncSession,
        job_id: str,
        status: str,
        current_stage: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> None:
        from api_gateway.repositories.job_repository import JobRepository as LegacyJobRepository

        return await LegacyJobRepository.update_job_status(
            db=db,
            job_id=job_id,
            status=status,
            current_stage=current_stage,
            progress=progress,
        )

