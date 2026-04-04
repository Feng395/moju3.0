"""任务服务兼容层。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.application.use_cases import (  # noqa: E402
    ContinueJobUseCase,
    CreateJobFromUploadUseCase,
    GetJobStatusUseCase,
    GetPriceSnapshotsUseCase,
    GetProcessSnapshotsUseCase,
)

from ..repositories.job_repository import JobRepository


class JobService:
    """兼容旧接口的任务服务外壳。"""

    def __init__(self):
        self.create_job_use_case = CreateJobFromUploadUseCase()
        self.get_status_use_case = GetJobStatusUseCase()
        self.get_price_snapshots_use_case = GetPriceSnapshotsUseCase()
        self.get_process_snapshots_use_case = GetProcessSnapshotsUseCase()
        self.continue_job_use_case = ContinueJobUseCase()

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
        """查询工艺快照。"""
        return await self.get_process_snapshots_use_case.execute(db=db, job_id=job_id, user_id=user_id)

    async def get_job_detail(self, db: AsyncSession, job_id: str, user_id: str) -> dict[str, Any]:
        """读取任务详情。"""
        del user_id
        summary = await JobRepository.get_job_summary(db, job_id)
        if not summary:
            raise ValueError(f"JOB_NOT_FOUND:{job_id}")

        return {
            "job_id": str(summary["job_id"]),
            "dwg_file_name": summary["dwg_file_name"],
            "prt_file_name": summary["prt_file_name"],
            "status": summary["status"],
            "progress": summary["progress"],
            "current_stage": summary["current_stage"],
            "total_cost": float(summary["total_cost"]) if summary["total_cost"] else 0.0,
            "subgraph_count": summary["subgraph_count"],
            "material_cost": float(summary["material_cost"]) if summary["material_cost"] else 0.0,
            "heat_treatment_cost": float(summary["heat_treatment_cost"]) if summary["heat_treatment_cost"] else 0.0,
            "processing_cost_total": float(summary["processing_cost_total"]) if summary["processing_cost_total"] else 0.0,
            "nc_cost": float(summary["nc_cost"]) if summary["nc_cost"] else 0.0,
            "grinding_cost": float(summary["grinding_cost"]) if summary["grinding_cost"] else 0.0,
            "wire_cost": float(summary["wire_cost"]) if summary["wire_cost"] else 0.0,
            "error_message": summary["error_message"],
            "created_at": summary["created_at"].isoformat() if summary["created_at"] else None,
            "updated_at": summary["updated_at"].isoformat() if summary["updated_at"] else None,
            "metadata": summary["metadata"],
        }

    async def submit_continue_job(self, job_id: str) -> dict[str, Any]:
        """提交 continue-job 请求。"""
        return await self.continue_job_use_case.submit(job_id)
