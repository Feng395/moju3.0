"""Continue-job application use case."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from ...core.logging import get_logger
from ..workflows.job_graph import job_graph

logger = get_logger(__name__)


class ContinueJobUseCase:
    """Submit a continue-job request onto the unified workflow path."""

    async def submit(self, job_id: str) -> dict[str, Any]:
        asyncio.create_task(self._execute_continue_job(job_id))
        logger.info("Continue-job request accepted: job_id=%s", job_id)
        return {
            "status": "accepted",
            "message": "任务已提交，请通过 WebSocket 监听进度",
            "job_id": job_id,
        }

    async def _execute_continue_job(self, job_id: str) -> None:
        """Enqueue continue action; fall back to direct workflow execution if needed."""
        try:
            # 中文注释：continue 优先走统一 job queue，和 start 共用同一条 workflow 入口。
            await self._publish_continue_message(job_id)
            logger.info("[后台任务] Continue action queued: job_id=%s", job_id)
        except Exception as exc:
            logger.warning(
                "[后台任务] Queue publish failed, falling back to local workflow: job_id=%s, error=%s",
                job_id,
                exc,
                exc_info=True,
            )
            try:
                # 中文注释：只有消息发送失败时才退回本地执行，避免在 use case 层重新分叉编排逻辑。
                result = await job_graph.handle_message({"job_id": job_id, "action": "continue"})
                if result.get("status") == "error":
                    logger.error("[后台任务] Continue execution failed: %s", result.get("message"))
                else:
                    logger.info("[后台任务] Continue execution completed locally: job_id=%s", job_id)
            except Exception as workflow_exc:
                await self._publish_failure(job_id, workflow_exc)

    async def _publish_continue_message(self, job_id: str) -> None:
        rabbitmq_client = self._get_rabbitmq_client()
        await rabbitmq_client.publish_message(
            rabbitmq_client.queue_job_processing,
            {
                "job_id": job_id,
                "action": "continue",
                "requested_at": datetime.utcnow().isoformat(),
            },
        )

    async def _publish_failure(self, job_id: str, exc: Exception) -> None:
        logger.error("[后台任务] Continue execution crashed: job_id=%s, error=%s", job_id, exc, exc_info=True)
        try:
            from shared.progress_publisher import ProgressPublisher
            from shared.progress_stages import ProgressStage

            ProgressPublisher().publish_progress(
                job_id=job_id,
                stage=ProgressStage.FAILED,
                progress=0,
                message=f"任务执行失败: {str(exc)}",
                details={"source": "continue_job_use_case", "error": str(exc)},
            )
        except Exception as publish_error:
            logger.error("[后台任务] Failed to publish failure progress: %s", publish_error, exc_info=True)

    @staticmethod
    def _get_rabbitmq_client():
        from ...infrastructure.messaging.rabbitmq_client import rabbitmq_client

        return rabbitmq_client
