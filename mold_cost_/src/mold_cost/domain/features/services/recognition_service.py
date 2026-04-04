"""特征识别领域桥接服务。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable


ProgressCallback = Callable[[int, int, int, int], None]


class LegacyFeatureRecognitionService:
    """桥接现有 `scripts.feature_recognition` 实现。

    当前阶段仍复用旧脚本中的成熟识别逻辑，
    但外部调用统一收口到领域服务，避免继续从各层直接 import legacy 脚本。
    """

    async def recognize(self, context: dict[str, Any]) -> dict[str, Any]:
        """兼容领域协议的异步入口。"""
        job_id = context.get("job_id")
        subgraph_id = context.get("subgraph_id")
        progress_callback = context.get("progress_callback")
        return self.batch_recognize(
            job_id=job_id,
            subgraph_id=subgraph_id,
            progress_callback=progress_callback,
        )

    def batch_recognize(
        self,
        job_id: str,
        subgraph_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """执行批量特征识别。"""
        module = self._load_legacy_module()
        return module.batch_feature_recognition_process(
            job_id,
            subgraph_id,
            progress_callback=progress_callback,
        )

    def analyze_dxf(self, dxf_path: str) -> dict[str, Any] | None:
        """分析单个 DXF 文件的特征。"""
        module = self._load_legacy_module()
        return module.analyze_dxf_features(dxf_path)

    def get_subgraphs(self, job_id: str, subgraph_id: str | None = None) -> list[dict[str, Any]]:
        """查询待处理子图。"""
        module = self._load_legacy_module()
        return module.get_subgraphs_from_db(job_id, subgraph_id)

    def save_features(self, subgraph_id: str, job_id: str, features: dict[str, Any]) -> bool:
        """保存识别结果。"""
        module = self._load_legacy_module()
        return module.save_features_to_db(subgraph_id, job_id, features)

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_legacy_module():
        """懒加载 legacy 模块，避免导入时初始化重型依赖。"""
        from scripts.feature_recognition import feature_recognition as legacy_module

        return legacy_module


feature_recognition_service = LegacyFeatureRecognitionService()
