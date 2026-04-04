"""Review session service backed by Redis locks."""

from __future__ import annotations

from ...review.ports import ReviewSessionService
from ....core.logging import get_logger

logger = get_logger(__name__)


class RedisReviewSessionService(ReviewSessionService):
    """Manage review lock lifecycle without embedding workflow logic."""

    def __init__(self):
        self._redis_client = None

    @property
    def redis_client(self):
        if self._redis_client is None:
            from api_gateway.utils.redis_client import redis_client

            self._redis_client = redis_client
        return self._redis_client

    @staticmethod
    def _lock_key(job_id: str) -> str:
        # review 锁与 review state 分开存，避免状态重建时误判会话是否有效。
        return f"review:lock:{job_id}"

    async def acquire(self, job_id: str, timeout: int = 1800) -> bool:
        lock_key = self._lock_key(job_id)
        try:
            result = await self.redis_client.set(lock_key, "locked", ex=timeout, nx=True)
            if result:
                logger.info("Review lock acquired: job_id=%s", job_id)
                return True
            logger.warning("Review lock already held: job_id=%s", job_id)
            return False
        except Exception:
            logger.exception("Failed to acquire review lock: job_id=%s", job_id)
            return False

    async def ensure_active(self, job_id: str, timeout: int = 1800) -> bool:
        # 修改入口优先续租已有锁；锁丢失时才尝试重新建立。
        if await self.is_locked(job_id):
            return await self.renew(job_id, timeout=timeout)
        return await self.acquire(job_id, timeout=timeout)

    async def renew(self, job_id: str, timeout: int = 1800) -> bool:
        lock_key = self._lock_key(job_id)
        try:
            if not await self.redis_client.exists(lock_key):
                logger.warning("Review lock missing during renew: job_id=%s", job_id)
                return False
            await self.redis_client.expire(lock_key, timeout)
            return True
        except Exception:
            logger.exception("Failed to renew review lock: job_id=%s", job_id)
            return False

    async def is_locked(self, job_id: str) -> bool:
        try:
            return bool(await self.redis_client.exists(self._lock_key(job_id)))
        except Exception:
            logger.exception("Failed to inspect review lock: job_id=%s", job_id)
            return False
