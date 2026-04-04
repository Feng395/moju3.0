"""重构后的 Redis 客户端。"""

from __future__ import annotations

import redis.asyncio as redis

from ...core.logging import get_logger
from ...core.settings import settings
from shared.logging_middleware import log_redis_operation

logger = get_logger(__name__)


class RedisClient:
    """统一缓存与发布订阅客户端。"""

    def __init__(self):
        self.client = None
        self.pubsub = None

    async def connect(self):
        """建立 Redis 连接。"""
        self.client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await self.client.ping()
        logger.info("Redis connected")

    async def close(self):
        if self.pubsub:
            await self.pubsub.close()
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def publish(self, channel: str, message: str):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        try:
            await self.client.publish(channel, message)
            log_redis_operation("publish", channel, f"<message_len={len(message)}>", success=True)
        except Exception:
            log_redis_operation("publish", channel, success=False)
            raise

    async def subscribe(self, *patterns: str):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        self.pubsub = self.client.pubsub()
        await self.pubsub.psubscribe(*patterns)
        return self.pubsub

    async def lpush(self, key: str, value: str):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        await self.client.lpush(key, value)

    async def ltrim(self, key: str, start: int, end: int):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        await self.client.ltrim(key, start, end)

    async def expire(self, key: str, seconds: int):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        await self.client.expire(key, seconds)

    async def lrange(self, key: str, start: int, end: int):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        return await self.client.lrange(key, start, end)

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        try:
            result = await self.client.set(key, value, ex=ex, nx=nx)
            log_redis_operation("set", key, f"<len={len(value)}, ex={ex}>", success=True)
            return result
        except Exception:
            log_redis_operation("set", key, success=False)
            raise

    async def get(self, key: str):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        try:
            result = await self.client.get(key)
            payload = f"<len={len(result)}>" if result else "<not_found>"
            log_redis_operation("get", key, payload, success=True)
            return result
        except Exception:
            log_redis_operation("get", key, success=False)
            raise

    async def delete(self, key: str):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        try:
            result = await self.client.delete(key)
            log_redis_operation("delete", key, success=True)
            return result
        except Exception:
            log_redis_operation("delete", key, success=False)
            raise

    async def exists(self, key: str):
        if not self.client:
            raise RuntimeError("Redis is not connected")
        return await self.client.exists(key)


redis_client = RedisClient()
