"""legacy CAD 拆图 gateway。"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from ...domain.cad.ports import CadSplitSubgraphRecord


class LegacyCadSplitGateway:
    """适配历史 ``scripts.cad_chaitu`` 入口。"""

    async def split(
        self,
        dwg_url: str | None,
        job_id: str,
        minio_client: Any | None = None,
    ) -> dict[str, Any]:
        # 中文说明：脚本 import 和 manager 初始化都收敛在 infrastructure 层。
        chaitu_process, init_managers = self._load_legacy_entrypoints()
        init_managers(minio_client=minio_client)
        return await chaitu_process(
            dwg_url=dwg_url,
            job_id=job_id,
            minio_client=minio_client,
        )

    async def list_subgraphs(self, job_id: str) -> list[CadSplitSubgraphRecord]:
        """回查拆图结果，补足稳定 artifact 引用。"""
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
        # 中文说明：懒加载避免在模块导入阶段拉起旧脚本的重型依赖。
        from scripts.cad_chaitu.main import chaitu_process, init_managers

        return chaitu_process, init_managers
