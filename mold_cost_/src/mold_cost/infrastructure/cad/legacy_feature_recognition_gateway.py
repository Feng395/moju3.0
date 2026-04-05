"""Legacy feature-recognition gateway."""

from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from typing import Any

from ...core.settings import settings
from .feature_analysis_runtime import analyze_dxf_features
from .feature_batch_runtime import batch_feature_recognition


class LegacyFeatureRecognitionGateway:
    """Isolate legacy DB helpers and upload side effects behind a stable gateway."""

    def batch_recognize(
        self,
        job_id: str,
        subgraph_id: str | None = None,
        progress_callback=None,
    ) -> dict[str, Any]:
        from scripts.feature_recognition.slider_red_face_updater import update_slider_red_face_data
        from scripts.minio_client import minio_client as legacy_minio_client

        # 中文说明：批处理编排已迁到 src runtime，这里只注入 legacy 侧仍在使用的 DB/MinIO 辅助。
        return batch_feature_recognition(
            job_id,
            subgraph_id=subgraph_id,
            progress_callback=progress_callback,
            get_subgraphs=self.get_subgraphs,
            save_features=self.save_features,
            minio_client=legacy_minio_client,
            slider_red_face_updater=update_slider_red_face_data,
            db_config={
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "user": settings.DB_USER,
                "password": settings.DB_PASSWORD,
                "database": settings.DB_NAME,
            },
        )

    def analyze_dxf(self, dxf_path: str) -> dict[str, Any] | None:
        # 中文说明：单文件 DXF 分析直接走 src runtime，避免再次回到旧脚本总入口。
        return analyze_dxf_features(dxf_path)

    def get_subgraphs(self, job_id: str, subgraph_id: str | None = None) -> list[dict[str, Any]]:
        return self._load_legacy_module().get_subgraphs_from_db(job_id, subgraph_id)

    def save_features(self, subgraph_id: str, job_id: str, features: dict[str, Any]) -> bool:
        return self._load_legacy_module().save_features_to_db(subgraph_id, job_id, features)

    def upload_feature_database(self, database: dict[str, Any], minio_path: str) -> None:
        from mold_cost.infrastructure.storage.minio_client import minio_client
        from scripts.feature_recognition.slider_red_face_lookup import invalidate_cache

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
        # 中文说明：仅在需要 DB 辅助方法时才加载 legacy 模块，减少导入副作用。
        from scripts.feature_recognition import feature_recognition as legacy_module

        return legacy_module
