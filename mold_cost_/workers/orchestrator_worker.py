"""Legacy orchestrator worker entrypoint.

The queue consumer is kept for compatibility, while orchestration logic now
flows through the application-level job workflow facade.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from refactor_bootstrap import ensure_src_path
from shared.message_queue import MessageQueue, QUEUE_JOB_PROCESSING
from shared.unified_logging import get_logger, init_logging

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
ensure_src_path()

from mold_cost.application.workflows.job_graph import job_graph

load_dotenv()
init_logging()
logger = get_logger("workers.orchestrator_worker")


class OrchestratorWorker:
    """Legacy worker shell that delegates orchestration to JobGraph."""

    def __init__(self, enable_retry: bool = False):
        self.mq = MessageQueue()
        self.running = False
        self.enable_retry = enable_retry

    async def start(self):
        """Start queue consumption."""
        logger.info("Starting OrchestratorWorker")
        await self.mq.connect()
        self.running = True
        # 中文注释：保留旧 worker 进程形态，但实际业务入口统一收口到 job_graph。
        await self.mq.consume(QUEUE_JOB_PROCESSING, self.handle_message, early_ack=True)

    async def handle_message(self, message: dict):
        """Pass job messages to the workflow facade."""
        job_id = message.get("job_id")
        action = message.get("action", "start")
        logger.info("Received orchestrator message: job_id=%s, action=%s", job_id, action)

        try:
            # 中文注释：worker 不再直接展开校验、编排和状态推进，只负责把消息交给 workflow。
            result = await job_graph.handle_message(message)
            status = result.get("status")

            if status == "ok":
                logger.info("Workflow finished successfully: job_id=%s", job_id)
            elif status == "ignored":
                logger.warning("Workflow skipped message: job_id=%s, reason=%s", job_id, result.get("message"))
            else:
                logger.error("Workflow returned failure: job_id=%s, message=%s", job_id, result.get("message"))
        except Exception as exc:
            logger.error("Workflow crashed while handling job_id=%s: %s", job_id, exc, exc_info=True)

    async def stop(self):
        """Stop the worker."""
        logger.info("Stopping OrchestratorWorker")
        self.running = False
        await self.mq.close()


async def main():
    """Standalone worker entrypoint."""
    enable_retry = os.getenv("ENABLE_MESSAGE_RETRY", "false").lower() == "true"
    worker = OrchestratorWorker(enable_retry=enable_retry)

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
