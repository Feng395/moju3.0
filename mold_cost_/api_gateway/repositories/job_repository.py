"""任务数据访问层。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.timezone_utils import now_shanghai
from shared.unified_logging import get_logger

logger = get_logger(__name__)


class JobRepository:
    """任务相关数据库操作。"""

    @staticmethod
    async def create_job(
        db: AsyncSession,
        job_id: str,
        user_id: str,
        dwg_info: Optional[Dict[str, Any]] = None,
        prt_info: Optional[Dict[str, Any]] = None,
        dwg_filename: Optional[str] = None,
        prt_filename: Optional[str] = None,
    ) -> None:
        """创建任务记录。"""
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
                "created_at": now_shanghai(),
                "updated_at": now_shanghai(),
            },
        )

        logger.info("Job record created: %s", job_id)

    @staticmethod
    async def get_job_by_id(db: AsyncSession, job_id: str):
        """根据 ID 查询任务。"""
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

    @staticmethod
    async def get_job_summary(db: AsyncSession, job_id: str) -> Optional[Dict[str, Any]]:
        """
        从汇总视图读取任务详情。

        中文注释：router 不再直接操作 SQL，视图查询统一沉到 repository。
        """
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

    @staticmethod
    async def update_job_status(
        db: AsyncSession,
        job_id: str,
        status: str,
        current_stage: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> None:
        """更新任务状态。"""
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
