"""快照数据访问适配层。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class SnapshotRepository:
    """将快照仓储从 application/use_cases 中剥离出来的适配器。"""

    async def create_price_snapshots(self, db: AsyncSession, job_id: str) -> int:
        from api_gateway.repositories.snapshot_repository import SnapshotRepository as LegacySnapshotRepository

        return await LegacySnapshotRepository.create_price_snapshots(db, job_id)

    async def create_process_snapshots(self, db: AsyncSession, job_id: str) -> int:
        from api_gateway.repositories.snapshot_repository import SnapshotRepository as LegacySnapshotRepository

        return await LegacySnapshotRepository.create_process_snapshots(db, job_id)

    async def get_price_snapshots(self, db: AsyncSession, job_id: str):
        from api_gateway.repositories.snapshot_repository import SnapshotRepository as LegacySnapshotRepository

        return await LegacySnapshotRepository.get_price_snapshots(db, job_id)

    async def get_process_snapshots(self, db: AsyncSession, job_id: str):
        from api_gateway.repositories.snapshot_repository import SnapshotRepository as LegacySnapshotRepository

        return await LegacySnapshotRepository.get_process_snapshots(db, job_id)

