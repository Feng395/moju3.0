"""继续执行任务用例。"""

from __future__ import annotations

import asyncio
from typing import Any

from ...core.logging import get_logger

logger = get_logger(__name__)


class ContinueJobUseCase:
    """负责提交“继续执行任务”的后台请求。"""

    async def submit(self, job_id: str) -> dict[str, Any]:
        """将继续执行动作投递到后台协程。"""
        from agents import get_orchestrator_agent

        orchestrator = get_orchestrator_agent()
        asyncio.create_task(self._execute_continue_job(orchestrator, job_id))
        logger.info("继续执行任务已提交到后台: job_id=%s", job_id)
        return {
            "status": "accepted",
            "message": "任务已提交，请通过 WebSocket 监听进度",
            "job_id": job_id,
        }

    async def _execute_continue_job(self, orchestrator, job_id: str) -> None:
        """后台真正执行 continue_job，并在失败时回推进度消息。"""
        try:
            result = await orchestrator.continue_job(job_id)
            if result["status"] == "error":
                logger.error("[后台任务] 继续执行失败: %s", result.get("message"))
            else:
                logger.info("[后台任务] 继续执行完成: job_id=%s", job_id)
        except Exception as exc:
            logger.error("[后台任务] 继续执行异常: job_id=%s, error=%s", job_id, exc, exc_info=True)
            try:
                from shared.progress_publisher import ProgressPublisher
                from shared.progress_stages import ProgressStage

                progress_publisher = ProgressPublisher()
                progress_publisher.publish_progress(
                    job_id=job_id,
                    stage=ProgressStage.FAILED,
                    progress=0,
                    message=f"任务执行失败: {str(exc)}",
                    details={"source": "continue_job_use_case", "error": str(exc)},
                )
            except Exception as publish_error:
                logger.error("[后台任务] 发布失败消息时出错: %s", publish_error, exc_info=True)
