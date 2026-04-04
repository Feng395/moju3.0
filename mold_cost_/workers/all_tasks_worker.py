"""统一后台任务 worker。

本阶段将实际执行入口切换到 application workflow，
从而把旧 agent 编排逐步收口到 `job_graph`。
"""

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
    """处理任务编排和价格重算两类后台消息。"""

    def __init__(self):
        self.mq = MessageQueue()
        self.pricing_agent = None
        logger.info("AllTasksWorker 初始化完成")

    async def start(self):
        """启动所有后台消费循环。"""
        logger.info("开始启动 AllTasksWorker")
        await self.mq.connect()
        self.pricing_agent = get_pricing_agent()

        tasks = [
            asyncio.create_task(self._consume_job_processing_queue()),
            asyncio.create_task(self._consume_pricing_queue()),
        ]
        await asyncio.gather(*tasks)

    async def _consume_job_processing_queue(self):
        """监听任务主队列。"""
        await self.mq.consume(
            queue_name=QUEUE_JOB_PROCESSING,
            callback=self.handle_job_processing_message,
            early_ack=True,
            max_concurrent=JOB_PROCESSING_CONCURRENCY,
        )

    async def _consume_pricing_queue(self):
        """监听价格重算队列。"""
        await self.mq.consume(
            queue_name=QUEUE_PRICING_RECALCULATE,
            callback=self.handle_pricing_message,
            early_ack=True,
            max_concurrent=PRICING_RECALCULATE_CONCURRENCY,
        )

    async def handle_job_processing_message(self, message: dict):
        """处理任务开始/继续执行消息。"""
        job_id = message.get("job_id")
        action = message.get("action", "start")
        logger.info("收到任务消息: job_id=%s, action=%s", job_id, action)

        try:
            if action == "start":
                result = await job_graph.start_job(job_id)
            elif action == "continue":
                result = await job_graph.continue_job(job_id)
            else:
                logger.error("未知任务动作: %s", action)
                return

            if result.get("status") == "ok":
                logger.info("任务处理成功: job_id=%s", job_id)
            else:
                logger.error("任务处理失败: job_id=%s, message=%s", job_id, result.get("message"))
        except Exception as exc:
            logger.error("任务消息处理异常: job_id=%s, error=%s", job_id, exc, exc_info=True)

    async def handle_pricing_message(self, message: dict):
        """处理价格重算消息。"""
        job_id = message.get("job_id")
        subgraph_ids = message.get("subgraph_ids", [])
        user_params = message.get("user_params", {})
        logger.info("收到价格重算消息: job_id=%s, subgraph_count=%s", job_id, len(subgraph_ids))

        try:
            self.pricing_agent = get_pricing_agent()
            result = await self.pricing_agent.process(
                {"job_id": job_id, "subgraph_ids": subgraph_ids, "user_params": user_params}
            )
            if result.get("status") in ["ok", "partial"]:
                logger.info("价格重算成功: job_id=%s", job_id)
            else:
                logger.error("价格重算失败: job_id=%s, message=%s", job_id, result.get("message"))
        except Exception as exc:
            logger.error("价格重算处理异常: job_id=%s, error=%s", job_id, exc, exc_info=True)


async def main():
    """worker 独立启动入口。"""
    worker = AllTasksWorker()
    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到中断信号，worker 即将关闭")
    except Exception as exc:
        logger.error("Worker 异常退出: %s", exc, exc_info=True)
        sys.exit(1)
