"""Adapters for modification and confirmation execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...review.ports import ReviewChangeApplier


class InteractionAgentReviewChangeApplier(ReviewChangeApplier):
    """Delegate stateful change execution to the legacy InteractionAgent."""

    def __init__(self, agent_factory: Callable[[], Any] | None = None):
        self._agent_factory = agent_factory or self._default_agent_factory

    async def handle_modification(
        self,
        job_id: str,
        modification_text: str,
        user_id: str,
        db_session,
    ) -> Any:
        # 变更执行仍是 legacy 强项，这里只做边界隔离，不改内部算法。
        agent = self._agent_factory()
        return await agent.handle_modification(
            job_id=job_id,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )

    async def confirm_changes(self, job_id: str, user_id: str, db_session) -> Any:
        agent = self._agent_factory()
        return await agent.confirm_changes(job_id=job_id, user_id=user_id, db_session=db_session)

    @staticmethod
    def _default_agent_factory():
        from agents.interaction_agent import InteractionAgent

        return InteractionAgent()
