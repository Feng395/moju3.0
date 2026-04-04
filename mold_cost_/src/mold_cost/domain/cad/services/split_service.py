"""CAD 拆图领域服务。"""

from __future__ import annotations

from typing import Any

from ..ports import CadSplitGateway


class LegacyCadSplitService:
    """兼容迁移期的 CAD 拆图服务。

    中文说明：当前仍复用旧脚本能力，但由 service 统一收口，
    这样 API / MCP / workflow 只依赖稳定服务接口。
    """

    def __init__(self, gateway: CadSplitGateway):
        self._gateway = gateway

    async def split(
        self,
        dwg_url: str | None,
        job_id: str,
        minio_client: Any | None = None,
    ) -> dict[str, Any]:
        # 中文说明：service 本身不碰脚本细节，只把请求转发给 gateway。
        return await self._gateway.split(
            dwg_url=dwg_url,
            job_id=job_id,
            minio_client=minio_client,
        )
