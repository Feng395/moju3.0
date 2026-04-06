"""Src-owned job repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.timezone_utils import now_shanghai

from ....core.logging import get_logger

logger = get_logger(__name__)


class JobRepository:
    """任务相关数据库操作。"""

    async def create_job(
        self,
        db: AsyncSession,
        job_id: str,
        user_id: str,
        dwg_info: dict[str, Any] | None = None,
        prt_info: dict[str, Any] | None = None,
        dwg_filename: str | None = None,
        prt_filename: str | None = None,
    ) -> None:
        sql = text(
            """
            INSERT INTO jobs (
                job_id, user_id,
                dwg_file_id, dwg_file_name, dwg_file_path, dwg_file_size,
                prt_file_id, prt_file_name, prt_file_path, prt_file_size,
                status, current_stage, progress, created_at, updated_at
            ) VALUES (
                :job_id, :user_id,
                :dwg_file_id, :dwg_file_name, :dwg_file_path, :dwg_file_size,
                :prt_file_id, :prt_file_name, :prt_file_path, :prt_file_size,
                :status, :current_stage, :progress, :created_at, :updated_at
            )
            """
        )
        current_time = now_shanghai()
        await db.execute(
            sql,
            {
                "job_id": job_id,
                "user_id": user_id,
                "dwg_file_id": dwg_info["file_id"] if dwg_info else None,
                "dwg_file_name": dwg_filename,
                "dwg_file_path": dwg_info["object_name"] if dwg_info else None,
                "dwg_file_size": dwg_info["file_size"] if dwg_info else None,
                "prt_file_id": prt_info["file_id"] if prt_info else None,
                "prt_file_name": prt_filename,
                "prt_file_path": prt_info["object_name"] if prt_info else None,
                "prt_file_size": prt_info["file_size"] if prt_info else None,
                "status": "pending",
                "current_stage": "initializing",
                "progress": 0,
                "created_at": current_time,
                "updated_at": current_time,
            },
        )
        logger.info("Job record created: %s", job_id)

    async def get_job_by_id(self, db: AsyncSession, job_id: str):
        sql = text(
            """
            SELECT
                job_id, user_id, status, current_stage, progress,
                dwg_file_id, dwg_file_name, dwg_file_path, dwg_file_size,
                prt_file_id, prt_file_name, prt_file_path, prt_file_size,
                total_cost, created_at, updated_at, completed_at
            FROM jobs
            WHERE job_id = :job_id
            """
        )
        result = await db.execute(sql, {"job_id": job_id})
        return result.fetchone()

    async def get_job_summary(self, db: AsyncSession, job_id: str) -> dict[str, Any] | None:
        # 中文注释：详情接口继续经由汇总视图读取，避免把聚合 SQL 散落回 use case/route 层。
        sql = text(
            """
            SELECT
                job_id,
                dwg_file_name,
                prt_file_name,
                status,
                progress,
                current_stage,
                total_cost,
                total_subgraphs AS subgraph_count,
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
            """
        )
        result = await db.execute(sql, {"job_id": job_id})
        row = result.mappings().fetchone()
        return dict(row) if row else None

    async def update_job_status(
        self,
        db: AsyncSession,
        job_id: str,
        status: str,
        current_stage: str | None = None,
        progress: int | None = None,
    ) -> None:
        sql = text(
            """
            UPDATE jobs
            SET status = :status,
                current_stage = COALESCE(:current_stage, current_stage),
                progress = COALESCE(:progress, progress),
                updated_at = :updated_at
            WHERE job_id = :job_id
            """
        )
        await db.execute(
            sql,
            {
                "job_id": job_id,
                "status": status,
                "current_stage": current_stage,
                "progress": progress,
                "updated_at": now_shanghai(),
            },
        )
        logger.info("Job status updated: %s -> %s", job_id, status)
