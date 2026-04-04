"""特征识别应用层用例。"""

from __future__ import annotations

import asyncio
from typing import Any

from ...core.logging import get_logger
from ...domain.features.ports import FeatureRecognitionService

logger = get_logger(__name__)


class ReprocessFeaturesUseCase:
    """提交特征识别重处理任务。"""

    def __init__(self, feature_service: FeatureRecognitionService | None = None):
        self._feature_service = feature_service

    async def submit(
        self,
        job_id: str,
        subgraph_ids: list[str],
        force_reprocess: bool = True,
    ) -> dict[str, Any]:
        """提交后台任务并立即返回。"""
        # 中文说明：应用层只负责任务投递，实际识别实现统一走 domain service。
        asyncio.create_task(
            self._execute(
                job_id=job_id,
                subgraph_ids=subgraph_ids,
                force_reprocess=force_reprocess,
            )
        )
        logger.info("特征识别任务已提交到后台: job_id=%s, subgraph_count=%s", job_id, len(subgraph_ids))
        return {
            "status": "accepted",
            "message": "特征识别任务已提交，请通过 WebSocket 监听进度",
            "job_id": job_id,
            "subgraph_count": len(subgraph_ids),
        }

    async def _execute(
        self,
        job_id: str,
        subgraph_ids: list[str],
        force_reprocess: bool,
    ) -> dict[str, Any]:
        """实际执行后台任务。"""
        logger.info("[后台任务] 开始执行特征识别: job_id=%s", job_id)
        # 中文说明：这里不再绕到 CAD agent，直接调用稳定的 feature service。
        result = await self._get_feature_service().reprocess(
            job_id=job_id,
            subgraph_ids=subgraph_ids,
            force_reprocess=force_reprocess,
        )
        logger.info(
            "[后台任务] 特征识别完成: job_id=%s, status=%s, total=%s",
            job_id,
            result.get("status"),
            result.get("total"),
        )
        return result

    def _get_feature_service(self) -> FeatureRecognitionService:
        """懒加载特征服务，避免导入路由时初始化重型依赖。"""
        if self._feature_service is None:
            from ...domain.features.services import feature_recognition_service

            self._feature_service = feature_recognition_service
        return self._feature_service
