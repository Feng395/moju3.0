"""审核任务 worker。

当前 worker 通过 `review_graph` 触发审核流程，
不再直接依赖具体的 InteractionAgent 实现细节。
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractIncomingMessage

from api_gateway.config import settings
from refactor_bootstrap import ensure_src_path
from shared.database import get_db
from shared.logging_config import get_logger, setup_logging

ensure_src_path()

from mold_cost.application.workflows.review_graph import review_graph

logger = get_logger(__name__)


class ReviewWorker:
    """消费 review_queue 并启动审核工作流。"""

    def __init__(self):
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractRobustChannel] = None
        self.queue_name = "review_queue"
        self.rabbitmq_url = settings.RABBITMQ_URL
        self.max_retries = 3
        self.retry_delay = 5

    async def connect(self):
        """连接 RabbitMQ 并声明审核队列。"""
        logger.info("连接 RabbitMQ: %s:%s", settings.RABBITMQ_HOST, settings.RABBITMQ_PORT)
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=5)
        return await self.channel.declare_queue(
            name=self.queue_name,
            durable=True,
            arguments={"x-message-ttl": 3600000},
        )

    async def start_consuming(self):
        """持续消费审核消息。"""
        queue = await self.connect()
        logger.info("开始监听审核队列: %s", self.queue_name)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await self._process_message(message)

    async def _process_message(self, message: AbstractIncomingMessage):
        """处理单条审核消息。"""
        async with message.process():
            try:
                data = json.loads(message.body.decode("utf-8"))
                logger.info("收到审核消息: %s", data)

                if not self._validate_message(data):
                    logger.error("非法审核消息: %s", data)
                    return

                retry_count = data.get("_retry_count", 0)
                success = await self._handle_message(data)

                if success:
                    logger.info("审核消息处理完成: job_id=%s", data.get("job_id"))
                    return

                if retry_count < self.max_retries:
                    await self._retry_message(data, retry_count + 1)
                else:
                    logger.error("审核消息重试次数耗尽: %s", data)
            except json.JSONDecodeError as exc:
                logger.error("审核消息 JSON 非法: %s", exc)
            except Exception as exc:
                logger.error("审核消息处理异常: %s", exc, exc_info=True)
                raise

    def _validate_message(self, data: dict) -> bool:
        """校验审核消息结构。"""
        required_fields = ["action", "job_id"]
        for field in required_fields:
            if field not in data:
                return False
        return data["action"] in ["start_review"]

    async def _handle_message(self, data: dict) -> bool:
        """将审核消息委托给 review_graph。"""
        action = data["action"]
        job_id = data["job_id"]
        if action != "start_review":
            logger.error("未知审核动作: %s", action)
            return False

        async for db in get_db():
            result = await review_graph.start_review(job_id=job_id, db_session=db)
            return result.status == "ok"
        return False

    async def _retry_message(self, data: dict, retry_count: int):
        """失败后短暂延迟并重新入队。"""
        data["_retry_count"] = retry_count
        await asyncio.sleep(self.retry_delay)

        message = Message(
            body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
            content_encoding="utf-8",
        )
        await self.channel.default_exchange.publish(message=message, routing_key=self.queue_name)
        logger.warning("审核消息重新入队: retry_count=%s", retry_count)

    async def close(self):
        """关闭 RabbitMQ 连接。"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ 连接已关闭")


ReviewConsumer = ReviewWorker
review_worker = ReviewWorker()


async def main():
    """独立进程启动入口。"""
    worker = ReviewWorker()
    try:
        await worker.start_consuming()
    finally:
        await worker.close()


if __name__ == "__main__":
    setup_logging(level="INFO")
    asyncio.run(main())
