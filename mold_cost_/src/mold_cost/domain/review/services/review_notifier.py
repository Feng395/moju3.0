"""Adapters for pushing review-side events."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...review.ports import ReviewNotifier


class InteractionAgentReviewNotifier(ReviewNotifier):
    """Reuse legacy websocket / persistence push methods via a small adapter."""

    def __init__(self, agent_factory: Callable[[], Any] | None = None):
        self._agent_factory = agent_factory or self._default_agent_factory

    async def push_display_view(self, job_id: str, display_view: list[dict[str, Any]], db_session=None) -> None:
        # 推送逻辑仍复用 legacy 方法，workflow 侧只表达“何时推”。
        agent = self._agent_factory()
        await agent._push_display_view(job_id, display_view, db_session=db_session)

    async def push_completion_request(
        self,
        job_id: str,
        completion_data: dict[str, Any],
        db_session=None,
    ) -> None:
        agent = self._agent_factory()
        await agent._push_completion_request(job_id, completion_data, db_session=db_session)

    async def push_system_message(self, job_id: str, message_text: str, db_session=None) -> None:
        agent = self._agent_factory()
        await agent._push_system_message(job_id, message_text, db_session=db_session)

    @staticmethod
    def _default_agent_factory():
        from agents.interaction_agent import InteractionAgent

        return InteractionAgent()
