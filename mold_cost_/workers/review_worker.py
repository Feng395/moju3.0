"""
Review worker for RabbitMQ review_queue messages.
"""

import asyncio
import json
from typing import Optional

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractIncomingMessage

from agents.interaction_agent import InteractionAgent
from api_gateway.config import settings
from shared.database import get_db
from shared.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


class ReviewWorker:
    """Consume review workflow messages from RabbitMQ."""

    def __init__(self):
        # 长驻 worker 复用同一个连接和 Agent，避免重复初始化开销。
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractRobustChannel] = None
        self.queue_name = "review_queue"
        self.rabbitmq_url = settings.RABBITMQ_URL
        self.max_retries = 3
        self.retry_delay = 5
        self.agent = InteractionAgent()

    async def connect(self):
        """Connect to RabbitMQ and declare the queue."""
        try:
            logger.info(
                "Connecting to RabbitMQ: %s:%s",
                settings.RABBITMQ_HOST,
                settings.RABBITMQ_PORT,
            )
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            # review_queue 处理的是长任务，限制并发避免单个 worker 抢占过多消息。
            await self.channel.set_qos(prefetch_count=5)

            # 队列由 worker 启动时幂等声明，确保单独启动 review worker 也能直接消费。
            queue = await self.channel.declare_queue(
                name=self.queue_name,
                durable=True,
                arguments={"x-message-ttl": 3600000},
            )

            logger.info("RabbitMQ connected")
            logger.info("Queue declared: %s", self.queue_name)
            return queue
        except Exception as exc:
            logger.error("RabbitMQ connection failed: %s", exc, exc_info=True)
            raise

    async def start_consuming(self):
        """Start the long-running review consumer loop."""
        try:
            queue = await self.connect()
            logger.info("Start consuming queue: %s", self.queue_name)
            print(f"ReviewWorker started, queue: {self.queue_name}")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await self._process_message(message)
        except asyncio.CancelledError:
            logger.info("Review worker cancelled")
            print("ReviewWorker stopped")
        except Exception as exc:
            logger.error("Review worker failed: %s", exc, exc_info=True)
            print(f"ReviewWorker failed: {exc}")

    async def _process_message(self, message: AbstractIncomingMessage):
        """Process a single review message."""
        async with message.process():
            try:
                # 统一按 UTF-8 JSON 协议解析消息体，失败直接记录并丢弃。
                data = json.loads(message.body.decode("utf-8"))
                logger.info("Received review message: %s", data)

                # 先做结构校验，避免非法消息进入业务层。
                if not self._validate_message(data):
                    logger.error("Invalid review message: %s", data)
                    return

                retry_count = data.get("_retry_count", 0)
                success = await self._handle_message(data)

                if success:
                    logger.info("Review message handled: job_id=%s", data.get("job_id"))
                    return

                if retry_count < self.max_retries:
                    logger.warning(
                        "Review message failed, retrying (%s/%s)",
                        retry_count + 1,
                        self.max_retries,
                    )
                    await self._retry_message(data, retry_count + 1)
                else:
                    logger.error("Review message exhausted retries: %s", data)
            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON in review message: %s", exc)
            except Exception as exc:
                logger.error("Unexpected review message error: %s", exc, exc_info=True)
                raise

    def _validate_message(self, data: dict) -> bool:
        """Validate the expected review message shape."""
        required_fields = ["action", "job_id"]
        for field in required_fields:
            if field not in data:
                logger.error("Missing required field: %s", field)
                return False

        if data["action"] not in ["start_review"]:
            logger.error("Unsupported action: %s", data["action"])
            return False

        return True

    async def _handle_message(self, data: dict) -> bool:
        """Dispatch the review action."""
        try:
            action = data["action"]
            job_id = data["job_id"]
            logger.info("Handling review action=%s job_id=%s", action, job_id)

            if action != "start_review":
                logger.error("Unknown review action: %s", action)
                return False

            # 复用共享数据库 session 生成器，把审核启动动作委托给 InteractionAgent。
            async for db in get_db():
                result = await self.agent.start_review(job_id=job_id, db_session=db)
                if result.status == "ok":
                    logger.info("Review started successfully: job_id=%s", job_id)
                    return True

                logger.error("Review start failed: %s", result.message)
                return False
        except Exception as exc:
            logger.error("Review message handling failed: %s", exc, exc_info=True)
            return False

    async def _retry_message(self, data: dict, retry_count: int):
        """Requeue a failed review message after a short delay."""
        try:
            data["_retry_count"] = retry_count
            # 简单延迟重试，避免瞬时异常导致消息立刻反复回队。
            await asyncio.sleep(self.retry_delay)

            message = Message(
                body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                content_encoding="utf-8",
            )
            await self.channel.default_exchange.publish(message=message, routing_key=self.queue_name)
            logger.info("Review message requeued: retry_count=%s", retry_count)
        except Exception as exc:
            logger.error("Failed to requeue review message: %s", exc, exc_info=True)

    async def close(self):
        """Close the RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")


# 保留类名别名，便于旧代码平滑切换到新的 worker 命名。
ReviewConsumer = ReviewWorker
review_worker = ReviewWorker()


async def main():
    """Run the review worker as a standalone process."""
    worker = ReviewWorker()
    try:
        await worker.start_consuming()
    except KeyboardInterrupt:
        logger.info("Stop signal received")
        print("\nStopping ReviewWorker...")
    finally:
        await worker.close()


if __name__ == "__main__":
    setup_logging(level="INFO")
    print("=" * 60)
    print("Review Worker")
    print("=" * 60)
    print("Queue: review_queue")
    print(f"RabbitMQ: {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60)
    asyncio.run(main())
