"""CAD 领域端口定义。"""

from __future__ import annotations

from typing import Any, Protocol


class CadSplitGateway(Protocol):
    """基础设施侧拆图端口。

    中文说明：legacy 脚本的真实调用放在 gateway，domain service 只编排入口。
    """

    async def split(
        self,
        dwg_url: str | None,
        job_id: str,
        minio_client: Any | None = None,
    ) -> dict[str, Any]: ...


class CadSplitService(Protocol):
    """暴露给应用层和接口层的稳定拆图服务协议。"""

    async def split(
        self,
        dwg_url: str | None,
        job_id: str,
        minio_client: Any | None = None,
    ) -> dict[str, Any]: ...
