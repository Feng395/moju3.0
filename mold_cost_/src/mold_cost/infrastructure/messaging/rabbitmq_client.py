"""重构后的 RabbitMQ 客户端。"""

from __future__ import annotations

import json
from typing import Any, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection

from ...core.logging import get_logger
from ...core.settings import settings
from shared.logging_middleware import log_rabbitmq_publish

logger = get_logger(__name__)


class RabbitMQClient:
    """统一消息总线客户端。"""

    def __init__(self):
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel: Optional[AbstractRobustChannel] = None
        self.url = settings.RABBITMQ_URL
        self.queue_job_processing = settings.RABBITMQ_QUEUE_JOB_PROCESSING
        self.queue_dlx = settings.RABBITMQ_QUEUE_DLX

    async def connect(self):
        """建立连接并声明当前阶段需要的队列。"""
        if self.connection and not self.connection.is_closed:
            return
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        dlx_exchange = await self.channel.declare_exchange(
            name=f"{self.queue_dlx}_exchange",
            type=ExchangeType.DIRECT,
            durable=True,
        )
        dlx_queue = await self.channel.declare_queue(name=self.queue_dlx, durable=True)
        await dlx_queue.bind(dlx_exchange, routing_key=self.queue_dlx)
        await self.channel.declare_queue(
            name=self.queue_job_processing,
            durable=True,
            arguments={
                "x-dead-letter-exchange": f"{self.queue_dlx}_exchange",
                "x-dead-letter-routing-key": self.queue_dlx,
                "x-message-ttl": 86400000,
            },
        )

    async def publish_message(self, queue: str, message: dict[Any, Any], priority: int = 0):
        """发布通用消息。"""
        if not self.channel:
            await self.connect()
        try:
            aio_message = Message(
                body=json.dumps(message, ensure_ascii=False).encode("utf-8"),
                delivery_mode=DeliveryMode.PERSISTENT,
                priority=priority,
                content_type="application/json",
                content_encoding="utf-8",
            )
            await self.channel.default_exchange.publish(message=aio_message, routing_key=queue)
            log_rabbitmq_publish(queue, message, success=True)
        except Exception:
            log_rabbitmq_publish(queue, message, success=False)
            raise

    async def publish_job_message(self, job_id: str, user_id: str, **kwargs):
        await self.publish_message(
            self.queue_job_processing,
            {"job_id": job_id, "user_id": user_id, **kwargs},
        )

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")


rabbitmq_client = RabbitMQClient()
