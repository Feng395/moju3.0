"""Adapters for pushing review-side events."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from shared.timezone_utils import now_shanghai

from agents.message_persistence_manager import get_persistence_manager

from ....infrastructure.messaging.redis_client import redis_client
from ...review.ports import ReviewNotifier


class InteractionAgentReviewNotifier(ReviewNotifier):
    """Reuse the legacy message contract without routing through InteractionAgent."""

    def __init__(self):
        self._persistence_manager = None

    @property
    def redis_client(self):
        return redis_client

    @property
    def persistence_manager(self):
        if self._persistence_manager is None:
            self._persistence_manager = get_persistence_manager()
        return self._persistence_manager

    async def push_display_view(self, job_id: str, display_view: list[dict[str, Any]], db_session=None) -> None:
        # 中文注释：直接复用 legacy 消息格式，缩小对 InteractionAgent 私有方法的依赖。
        await self._publish(
            job_id=job_id,
            message={
                "type": "review_display_view",
                "job_id": job_id,
                "timestamp": now_shanghai().isoformat(),
                "data": display_view,
            },
            db_session=db_session,
        )

    async def push_completion_request(
        self,
        job_id: str,
        completion_data: dict[str, Any],
        db_session=None,
    ) -> None:
        await self._publish(
            job_id=job_id,
            message={
                "type": "completion_request",
                "job_id": job_id,
                "timestamp": now_shanghai().isoformat(),
                "data": completion_data,
            },
            db_session=db_session,
        )

    async def push_system_message(self, job_id: str, message_text: str, db_session=None) -> None:
        await self._publish(
            job_id=job_id,
            message={
                "type": "system_message",
                "job_id": job_id,
                "timestamp": now_shanghai().isoformat(),
                "message": message_text,
            },
            db_session=db_session,
        )

    async def _publish(self, *, job_id: str, message: dict[str, Any], db_session=None) -> None:
        channel = f"job:{job_id}:review"
        await self.redis_client.publish(channel, self._serialize_json(message))
        await self.persistence_manager.push_and_persist(
            job_id=job_id,
            ws_message=message,
            db_session=db_session,
        )

    @staticmethod
    def _serialize_json(data: Any) -> str:
        def default_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        return json.dumps(data, ensure_ascii=False, default=default_handler)
