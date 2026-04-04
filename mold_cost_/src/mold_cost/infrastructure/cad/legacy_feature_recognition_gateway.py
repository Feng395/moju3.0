"""legacy 特征识别 gateway。"""

from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from typing import Any


class LegacyFeatureRecognitionGateway:
    """隔离脚本调用和 MinIO 上传细节的适配器。"""

    def batch_recognize(
        self,
        job_id: str,
        subgraph_id: str | None = None,
        progress_callback=None,
    ) -> dict[str, Any]:
        # 中文说明：旧批处理算法仍保留在脚本内，这里只做适配转发。
        module = self._load_legacy_module()
        return module.batch_feature_recognition_process(
            job_id,
            subgraph_id,
            progress_callback=progress_callback,
        )

    def analyze_dxf(self, dxf_path: str) -> dict[str, Any] | None:
        return self._load_legacy_module().analyze_dxf_features(dxf_path)

    def get_subgraphs(self, job_id: str, subgraph_id: str | None = None) -> list[dict[str, Any]]:
        return self._load_legacy_module().get_subgraphs_from_db(job_id, subgraph_id)

    def save_features(self, subgraph_id: str, job_id: str, features: dict[str, Any]) -> bool:
        return self._load_legacy_module().save_features_to_db(subgraph_id, job_id, features)

    def upload_feature_database(self, database: dict[str, Any], minio_path: str) -> None:
        from mold_cost.infrastructure.storage.minio_client import minio_client
        from scripts.feature_recognition.slider_red_face_lookup import invalidate_cache

        # 中文说明：上传前先落临时 JSON，复用既有 MinIO 客户端与缓存失效逻辑。
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".json",
            delete=False,
            mode="w",
            encoding="utf-8",
        )
        try:
            json.dump(database, temp_file, ensure_ascii=False, indent=2)
            temp_file.close()

            uploaded = minio_client.upload_file_from_path(
                minio_path,
                temp_file.name,
                content_type="application/json",
            )
            if not uploaded:
                raise RuntimeError("上传 MinIO 失败")

            invalidate_cache(minio_path)
        finally:
            try:
                os.unlink(temp_file.name)
            except OSError:
                pass

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_legacy_module():
        # 中文说明：懒加载 feature_recognition，避免 domain/service 导入时直接触发脚本初始化。
        from scripts.feature_recognition import feature_recognition as legacy_module

        return legacy_module
