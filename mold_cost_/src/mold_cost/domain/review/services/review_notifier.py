"""Adapters for pushing review-side events."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from shared.timezone_utils import now_shanghai

from ....infrastructure.messaging.message_persistence_adapter import get_message_persistence_adapter
from ....infrastructure.messaging.redis_client import redis_client
from ...review.ports import MessagePersistence, ReviewNotifier


class InteractionAgentReviewNotifier(ReviewNotifier):
    """Publish review events via src-owned persistence adapters."""

    def __init__(self, *, message_persistence: MessagePersistence | None = None):
        self._message_persistence = message_persistence

    @property
    def redis_client(self):
        return redis_client

    @property
    def message_persistence(self) -> MessagePersistence:
        if self._message_persistence is None:
            self._message_persistence = get_message_persistence_adapter()
        return self._message_persistence

    async def push_display_view(self, job_id: str, display_view: list[dict[str, Any]], db_session=None) -> None:
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
        await self.message_persistence.push_and_persist(
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
