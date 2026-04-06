"""Src-owned snapshot repository."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.logging import get_logger

logger = get_logger(__name__)


class SnapshotRepository:
    """快照数据访问层。"""

    async def create_price_snapshots(self, db: AsyncSession, job_id: str) -> int:
        sql = text(
            """
            INSERT INTO job_price_snapshots (
                job_id, original_price_id, version_id,
                category, sub_category,
                price, unit, work_hours,
                min_num, add_price, weight_num,
                note, instruction, is_modified,
                snapshot_created_at, metadata
            )
            SELECT
                :job_id,
                id,
                COALESCE(version_id, 'v1.0'),
                category,
                sub_category,
                price,
                unit,
                work_hours,
                min_num,
                add_price,
                weight_num,
                note,
                instruction,
                false,
                NOW(),
                NULL
            FROM price_items
            WHERE is_active = true
            """
        )
        result = await db.execute(sql, {"job_id": job_id})
        logger.info("Price snapshots created: job_id=%s, count=%s", job_id, result.rowcount)
        return result.rowcount

    async def create_process_snapshots(self, db: AsyncSession, job_id: str) -> int:
        sql = text(
            """
            INSERT INTO job_process_snapshots (
                job_id, original_rule_id, version_id,
                feature_type, name, description,
                priority, conditions, output_params,
                is_modified, snapshot_created_at, metadata
            )
            SELECT
                :job_id,
                id,
                COALESCE(version_id, 'v1.0'),
                feature_type,
                name,
                description,
                priority,
                conditions,
                output_params,
                false,
                NOW(),
                NULL
            FROM process_rules
            WHERE is_active = true
            """
        )
        result = await db.execute(sql, {"job_id": job_id})
        logger.info("Process snapshots created: job_id=%s, count=%s", job_id, result.rowcount)
        return result.rowcount

    async def get_price_snapshots(self, db: AsyncSession, job_id: str):
        sql = text(
            """
            SELECT
                snapshot_id, job_id, original_price_id, version_id,
                category, sub_category,
                price, unit, work_hours,
                min_num, add_price, weight_num,
                note, instruction,
                is_modified, modified_at, modified_by,
                modification_reason, snapshot_created_at, metadata
            FROM job_price_snapshots
            WHERE job_id = :job_id
            ORDER BY category, sub_category
            """
        )
        result = await db.execute(sql, {"job_id": job_id})
        return result.fetchall()

    async def get_process_snapshots(self, db: AsyncSession, job_id: str):
        sql = text(
            """
            SELECT
                snapshot_id, job_id, original_rule_id, version_id,
                feature_type, name, description,
                priority, conditions, output_params,
                is_modified, modified_at, modified_by,
                modification_reason, snapshot_created_at, metadata
            FROM job_process_snapshots
            WHERE job_id = :job_id
            ORDER BY feature_type, priority DESC
            """
        )
        result = await db.execute(sql, {"job_id": job_id})
        return result.fetchall()
