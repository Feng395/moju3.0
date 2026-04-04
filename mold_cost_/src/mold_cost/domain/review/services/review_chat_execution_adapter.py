"""Adapters for chat-oriented InteractionAgent calls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, AsyncIterator

from ....core.logging import get_logger
from ...review.ports import ReviewChatExecutionAdapter

logger = get_logger(__name__)


class InteractionAgentReviewChatExecutor(ReviewChatExecutionAdapter):
    """Keep chat execution behind a dedicated adapter boundary."""

    def __init__(self, agent_factory: Callable[[], Any] | None = None):
        self._agent_factory = agent_factory or self._default_agent_factory

    async def generate_completion_suggestion(
        self,
        prompt: str,
        context_data: dict[str, Any],
    ) -> str:
        agent = self._agent_factory()
        return await agent._generate_completion_suggestion(prompt, context_data)

    async def chat(
        self,
        job_id: str,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any] | None,
    ) -> str:
        agent = self._agent_factory()
        return await agent.chat(job_id=job_id, message=message, history=history, current_data=current_data)

    async def chat_stream(
        self,
        job_id: str,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any] | None,
    ) -> AsyncIterator[str]:
        agent = self._agent_factory()
        async for chunk in agent.chat_stream(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        ):
            yield chunk

    @staticmethod
    def _default_agent_factory():
        from agents.interaction_agent import InteractionAgent

        return InteractionAgent()
