"""Review pending-action storage adapters."""

from __future__ import annotations

import json
from typing import Any

from ..messaging.redis_client import redis_client


class RedisReviewPendingActionStore:
    """Load and clear review pending actions without exposing raw Redis usage."""

    def __init__(self, client=None):
        self._client = client or redis_client

    @property
    def client(self):
        return self._client

    async def save(self, job_id: str, payload: dict[str, Any], *, ex: int = 3600) -> None:
        # 中文注释：统一在这里做 JSON 序列化，避免 handler 侧重复关心 Redis 写入格式。
        await self.client.set(
            self._key(job_id),
            json.dumps(payload, ensure_ascii=False),
            ex=ex,
        )

    async def load(self, job_id: str) -> dict[str, Any] | None:
        payload = await self.client.get(self._key(job_id))
        if not payload:
            return None
        return json.loads(payload)

    async def delete(self, job_id: str) -> None:
        await self.client.delete(self._key(job_id))

    @staticmethod
    def _key(job_id: str) -> str:
        return f"review:pending_action:{job_id}"
