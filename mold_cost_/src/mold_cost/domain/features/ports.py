"""特征识别领域端口定义。"""

from __future__ import annotations

from typing import Any, Callable, Protocol


ProgressCallback = Callable[[int, int, int, int], None]


class FeatureRecognitionService(Protocol):
    """特征识别服务协议。"""

    async def recognize(self, context: dict[str, Any]) -> dict[str, Any]: ...

    def batch_recognize(
        self,
        job_id: str,
        subgraph_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]: ...

    def analyze_dxf(self, dxf_path: str) -> dict[str, Any] | None: ...

    def get_subgraphs(self, job_id: str, subgraph_id: str | None = None) -> list[dict[str, Any]]: ...

    def save_features(self, subgraph_id: str, job_id: str, features: dict[str, Any]) -> bool: ...
