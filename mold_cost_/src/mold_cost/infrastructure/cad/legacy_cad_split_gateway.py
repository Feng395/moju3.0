"""legacy CAD 拆图 gateway。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any


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

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_legacy_entrypoints():
        # 中文说明：懒加载避免在模块导入阶段拉起旧脚本的重型依赖。
        from scripts.cad_chaitu.main import chaitu_process, init_managers

        return chaitu_process, init_managers
