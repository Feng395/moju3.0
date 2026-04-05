"""Legacy CAD split gateway."""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from ...domain.cad.ports import CadSplitSubgraphRecord
from .cad_split_runtime import run_cad_split


class LegacyCadSplitGateway:
    """Adapt the existing `scripts.cad_chaitu` entrypoints behind a stable gateway."""

    async def split(
        self,
        dwg_url: str | None,
        job_id: str,
        minio_client: Any | None = None,
    ) -> dict[str, Any]:
        # 中文说明：gateway 本身不再拼装 legacy 细节，统一交给 src runtime 驱动。
        return await run_cad_split(
            dwg_url=dwg_url,
            job_id=job_id,
            minio_client=minio_client,
            load_entrypoints=self._load_legacy_entrypoints,
        )

    async def list_subgraphs(self, job_id: str) -> list[CadSplitSubgraphRecord]:
        """Load persisted split results for artifact reconstruction."""

        if not self._looks_like_uuid(job_id):
            return []

        try:
            from shared.database import get_db
            from shared.models import Subgraph
            from sqlalchemy import select
        except Exception:
            return []

        job_uuid = uuid.UUID(job_id)
        async for db in get_db():
            result = await db.execute(
                select(
                    Subgraph.subgraph_id,
                    Subgraph.part_code,
                    Subgraph.part_name,
                    Subgraph.subgraph_file_url,
                )
                .where(Subgraph.job_id == job_uuid)
                .order_by(Subgraph.part_code, Subgraph.subgraph_id)
            )
            return [
                {
                    "subgraph_id": row.subgraph_id,
                    "part_code": row.part_code,
                    "part_name": row.part_name,
                    "subgraph_file_url": row.subgraph_file_url,
                }
                for row in result.fetchall()
            ]
        return []

    @staticmethod
    def _looks_like_uuid(value: str) -> bool:
        try:
            uuid.UUID(value)
        except (TypeError, ValueError, AttributeError):
            return False
        return True

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_legacy_entrypoints():
        # 中文说明：惰性导入可避免 CAD 重型依赖在应用启动阶段提前初始化。
        from scripts.cad_chaitu.main import chaitu_process, init_managers

        return chaitu_process, init_managers
