"""特征识别领域端口定义。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Callable, Protocol


ProgressCallback = Callable[[int, int, int, int], None]


class FeatureRecognitionGateway(Protocol):
    """基础设施侧端口。

    中文说明：这里约束 legacy 脚本、MinIO 上传等外部能力，
    让 domain service 不再直接 import scripts 或依赖具体实现。
    """

    def batch_recognize(
        self,
        job_id: str,
        subgraph_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]: ...

    def analyze_dxf(self, dxf_path: str) -> dict[str, Any] | None: ...

    def get_subgraphs(self, job_id: str, subgraph_id: str | None = None) -> list[dict[str, Any]]: ...

    def save_features(self, subgraph_id: str, job_id: str, features: dict[str, Any]) -> bool: ...

    def upload_feature_database(self, database: dict[str, Any], minio_path: str) -> None: ...


class FeatureRecognitionService(Protocol):
    """暴露给应用层和接口层的稳定服务协议。"""

    async def recognize(self, context: dict[str, Any]) -> dict[str, Any]: ...

    async def reprocess(
        self,
        job_id: str,
        subgraph_ids: Sequence[str] | None = None,
        force_reprocess: bool = True,
    ) -> dict[str, Any]: ...

    def batch_recognize(
        self,
        job_id: str,
        subgraph_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]: ...

    def analyze_dxf(self, dxf_path: str) -> dict[str, Any] | None: ...

    def get_subgraphs(self, job_id: str, subgraph_id: str | None = None) -> list[dict[str, Any]]: ...

    def save_features(self, subgraph_id: str, job_id: str, features: dict[str, Any]) -> bool: ...

    def upload_feature_database(self, csv_folder: str, minio_path: str | None = None) -> dict[str, Any]: ...
