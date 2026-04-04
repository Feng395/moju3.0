"""任务查询相关用例。"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api_gateway.repositories.job_repository import JobRepository
from api_gateway.repositories.snapshot_repository import SnapshotRepository


class GetJobStatusUseCase:
    """负责任务状态查询。"""

    def __init__(self):
        self.job_repo = JobRepository()

    async def execute(self, db: AsyncSession, job_id: str, user_id: str) -> dict[str, Any]:
        job = await self.job_repo.get_job_by_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND", "message": f"任务不存在: {job_id}"})
        if str(job.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail={"error": "PERMISSION_DENIED", "message": "无权访问此任务"})
        return {
            "job_id": job.job_id,
            "status": job.status,
            "current_stage": job.current_stage,
            "progress": job.progress,
            "files": {"dwg": job.dwg_file_name, "prt": job.prt_file_name},
            "total_cost": float(job.total_cost) if job.total_cost else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }


class GetPriceSnapshotsUseCase:
    """负责价格快照查询。"""

    def __init__(self):
        self.job_repo = JobRepository()
        self.snapshot_repo = SnapshotRepository()

    async def execute(self, db: AsyncSession, job_id: str, user_id: str) -> dict[str, Any]:
        await self._check_job_permission(db, job_id, user_id)
        snapshots = await self.snapshot_repo.get_price_snapshots(db, job_id)
        return {
            "job_id": job_id,
            "count": len(snapshots),
            "snapshots": [
                {
                    "snapshot_id": int(snapshot.snapshot_id),
                    "original_price_id": snapshot.original_price_id,
                    "version_id": snapshot.version_id,
                    "category": snapshot.category,
                    "sub_category": snapshot.sub_category,
                    "description": snapshot.description,
                    "price": snapshot.price,
                    "unit": snapshot.unit,
                    "work_hours": snapshot.work_hours,
                    "min_num": snapshot.min_num,
                    "add_price": snapshot.add_price,
                    "weight_num": snapshot.weight_num,
                    "note": snapshot.note,
                    "instruction": snapshot.instruction,
                    "is_modified": snapshot.is_modified,
                    "modified_at": snapshot.modified_at.isoformat() if snapshot.modified_at else None,
                    "modified_by": snapshot.modified_by,
                    "modification_reason": snapshot.modification_reason,
                    "snapshot_created_at": snapshot.snapshot_created_at.isoformat()
                    if snapshot.snapshot_created_at
                    else None,
                    "metadata": snapshot.metadata,
                }
                for snapshot in snapshots
            ],
        }

    async def _check_job_permission(self, db: AsyncSession, job_id: str, user_id: str) -> None:
        """统一校验任务是否存在以及访问权限。"""
        job = await self.job_repo.get_job_by_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND", "message": "任务不存在"})
        if str(job.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail={"error": "PERMISSION_DENIED", "message": "无权访问"})


class GetProcessSnapshotsUseCase:
    """负责工艺规则快照查询。"""

    def __init__(self):
        self.job_repo = JobRepository()
        self.snapshot_repo = SnapshotRepository()

    async def execute(self, db: AsyncSession, job_id: str, user_id: str) -> dict[str, Any]:
        await self._check_job_permission(db, job_id, user_id)
        snapshots = await self.snapshot_repo.get_process_snapshots(db, job_id)
        return {
            "job_id": job_id,
            "count": len(snapshots),
            "snapshots": [
                {
                    "snapshot_id": int(snapshot.snapshot_id),
                    "original_rule_id": snapshot.original_rule_id,
                    "version_id": snapshot.version_id,
                    "feature_type": snapshot.feature_type,
                    "name": snapshot.name,
                    "description": snapshot.description,
                    "priority": snapshot.priority,
                    "conditions": snapshot.conditions,
                    "output_params": snapshot.output_params,
                    "is_modified": snapshot.is_modified,
                    "modified_at": snapshot.modified_at.isoformat() if snapshot.modified_at else None,
                    "modified_by": snapshot.modified_by,
                    "modification_reason": snapshot.modification_reason,
                    "snapshot_created_at": snapshot.snapshot_created_at.isoformat()
                    if snapshot.snapshot_created_at
                    else None,
                    "metadata": snapshot.metadata,
                }
                for snapshot in snapshots
            ],
        }

    async def _check_job_permission(self, db: AsyncSession, job_id: str, user_id: str) -> None:
        """统一校验任务是否存在以及访问权限。"""
        job = await self.job_repo.get_job_by_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND", "message": "任务不存在"})
        if str(job.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail={"error": "PERMISSION_DENIED", "message": "无权访问"})
