"""CAD 领域服务契约定义。"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict


ServiceStatus = Literal["ok", "error"]
SummaryStatus = Literal["success", "partial", "failed", "accepted"]
ArtifactStorage = Literal["minio", "database", "inline", "unknown"]


class ServiceError(TypedDict, total=False):
    """统一异常模型。"""

    code: str
    message: str
    retryable: bool
    details: dict[str, Any]


class ServiceArtifactRef(TypedDict, total=False):
    """统一 artifact 引用格式。"""

    artifact_type: str
    ref: str
    storage: ArtifactStorage
    locator: dict[str, Any]
    metadata: dict[str, Any]


class ServiceSummary(TypedDict, total=False):
    """统一 summary 结构，供 workflow 直接消费。"""

    operation: str
    job_id: str | None
    status: SummaryStatus
    total_count: int
    success_count: int
    failed_count: int
    requested_count: int
    artifact_count: int
    failed_ids: list[str]
    mode: str


class CadSplitSubgraphRecord(TypedDict, total=False):
    """拆图后可回查的子图记录。"""

    subgraph_id: str
    part_code: str | None
    part_name: str | None
    subgraph_file_url: str | None


class CadSplitResult(TypedDict, total=False):
    """CAD 拆图领域服务返回值。"""

    status: ServiceStatus
    success: bool
    message: str
    job_id: str
    operation: str
    data: dict[str, Any]
    summary: ServiceSummary
    artifacts: list[ServiceArtifactRef]
    error: ServiceError | None


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

    async def list_subgraphs(self, job_id: str) -> list[CadSplitSubgraphRecord]: ...


class CadSplitService(Protocol):
    """暴露给应用层和 workflow 的稳定拆图服务契约。"""

    async def split(
        self,
        dwg_url: str | None,
        job_id: str,
        minio_client: Any | None = None,
    ) -> CadSplitResult: ...
