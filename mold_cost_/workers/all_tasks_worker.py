"""Unified background worker entrypoints."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from refactor_bootstrap import ensure_src_path
from shared.message_queue import MessageQueue, QUEUE_JOB_PROCESSING, QUEUE_PRICING_RECALCULATE
from shared.unified_logging import get_logger, init_logging

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
ensure_src_path()

from agents import get_pricing_agent
from mold_cost.application.workflows.job_graph import job_graph

init_logging()
logger = get_logger("workers.all_tasks_worker")

JOB_PROCESSING_CONCURRENCY = int(os.getenv("JOB_PROCESSING_CONCURRENCY", "1"))
PRICING_RECALCULATE_CONCURRENCY = int(os.getenv("PRICING_RECALCULATE_CONCURRENCY", "3"))


class AllTasksWorker:
    """Consume job-processing and pricing-recalculation queues."""

    def __init__(self):
        self.mq = MessageQueue()
        self.pricing_agent = None
        logger.info("AllTasksWorker initialized")

    async def start(self):
        """Start all queue consumers."""
        logger.info("Starting AllTasksWorker")
        await self.mq.connect()
        self.pricing_agent = get_pricing_agent()

        tasks = [
            asyncio.create_task(self._consume_job_processing_queue()),
            asyncio.create_task(self._consume_pricing_queue()),
        ]
        await asyncio.gather(*tasks)

    async def _consume_job_processing_queue(self):
        """Consume the unified job-processing queue."""
        await self.mq.consume(
            queue_name=QUEUE_JOB_PROCESSING,
            callback=self.handle_job_processing_message,
            early_ack=True,
            max_concurrent=JOB_PROCESSING_CONCURRENCY,
        )

    async def _consume_pricing_queue(self):
        """Consume pricing recalculation requests."""
        await self.mq.consume(
            queue_name=QUEUE_PRICING_RECALCULATE,
            callback=self.handle_pricing_message,
            early_ack=True,
            max_concurrent=PRICING_RECALCULATE_CONCURRENCY,
        )

    async def handle_job_processing_message(self, message: dict):
        """Delegate job orchestration to the workflow facade."""
        job_id = message.get("job_id")
        action = message.get("action", "start")
        logger.info("Received job message: job_id=%s, thread_id=%s, action=%s", job_id, job_id, action)

        try:
            # 中文注释：start / continue 在 worker 层不再分叉，
            # 统一由 job_graph 根据 action 和 checkpoint 决定真实运行路径。
            result = await job_graph.handle_message(message)
            status = result.get("status")

            if status == "ok":
                logger.info("Job processed successfully: job_id=%s", job_id)
            elif status == "ignored":
                logger.warning("Job skipped by workflow: job_id=%s, message=%s", job_id, result.get("message"))
            else:
                logger.error("Job processing failed: job_id=%s, message=%s", job_id, result.get("message"))
        except Exception as exc:
            logger.error("Job message handling crashed: job_id=%s, error=%s", job_id, exc, exc_info=True)

    async def handle_pricing_message(self, message: dict):
        """Handle pricing recalculation messages."""
        job_id = message.get("job_id")
        subgraph_ids = message.get("subgraph_ids", [])
        user_params = message.get("user_params", {})
        logger.info("Received pricing message: job_id=%s, subgraph_count=%s", job_id, len(subgraph_ids))

        try:
            self.pricing_agent = get_pricing_agent()
            result = await self.pricing_agent.process(
                {"job_id": job_id, "subgraph_ids": subgraph_ids, "user_params": user_params}
            )
            if result.get("status") in ["ok", "partial"]:
                logger.info("Pricing recalculation succeeded: job_id=%s", job_id)
            else:
                logger.error("Pricing recalculation failed: job_id=%s, message=%s", job_id, result.get("message"))
        except Exception as exc:
            logger.error("Pricing message handling crashed: job_id=%s, error=%s", job_id, exc, exc_info=True)


async def main():
    """Standalone worker entrypoint."""
    worker = AllTasksWorker()
    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by keyboard signal")
    except Exception as exc:
        logger.error("Worker exited with error: %s", exc, exc_info=True)
        sys.exit(1)
