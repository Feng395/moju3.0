"""特征识别应用层用例。"""

from __future__ import annotations

import asyncio
from typing import Any

from ...core.logging import get_logger

logger = get_logger(__name__)


class ReprocessFeaturesUseCase:
    """提交特征识别重处理任务。"""

    async def submit(
        self,
        job_id: str,
        subgraph_ids: list[str],
        force_reprocess: bool = True,
    ) -> dict[str, Any]:
        """提交后台任务并立即返回。"""
        # 中文注释：应用层只负责任务投递，具体识别仍由现有 CAD agent 承接。
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
        cad_agent = self._get_cad_agent()
        result = await cad_agent.recognize_features_batch(
            {
                "job_id": job_id,
                "subgraph_ids": subgraph_ids,
                "force_reprocess": force_reprocess,
            }
        )
        logger.info(
            "[后台任务] 特征识别完成: job_id=%s, status=%s, total=%s",
            job_id,
            result.get("status"),
            result.get("total"),
        )
        return result

    @staticmethod
    def _get_cad_agent():
        """懒加载 CAD agent，避免导入路由时初始化大对象。"""
        from agents import get_cad_agent

        return get_cad_agent()
