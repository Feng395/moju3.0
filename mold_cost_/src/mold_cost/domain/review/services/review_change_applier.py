"""Adapters for modification and confirmation execution."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from agents.base_agent import OpResult
from shared.timezone_utils import now_shanghai

from ....application.workflows.review_state import ReviewState
from ....core.logging import get_logger
from ....infrastructure.db.repositories.review_repository_adapter import LegacyReviewRepositoryAdapter
from ...review.ports import (
    ReviewActionHandlerRegistry,
    ReviewChangeApplier,
    ReviewConfirmationExecutor,
    ReviewIntentRecognizerFactory,
    ReviewStateStore,
)

logger = get_logger(__name__)


class InteractionAgentReviewChangeApplier(ReviewChangeApplier):
    """Run review changes through isolated legacy adapters."""

    def __init__(
        self,
        agent_factory: Callable[[], Any] | None = None,
        *,
        state_store: ReviewStateStore | None = None,
        review_repository: Any | None = None,
        intent_recognizer_factory: ReviewIntentRecognizerFactory | None = None,
        action_handler_registry: ReviewActionHandlerRegistry | None = None,
        confirmation_executor: ReviewConfirmationExecutor | None = None,
    ):
        self._agent_factory = agent_factory
        self._state_store = state_store
        self._review_repo = review_repository
        self._intent_recognizer_factory = intent_recognizer_factory
        self._action_handler_registry = action_handler_registry
        self._confirmation_executor = confirmation_executor

    @property
    def review_repo(self):
        if self._review_repo is None:
            self._review_repo = LegacyReviewRepositoryAdapter()
        return self._review_repo

    async def handle_modification(
        self,
        *,
        state: ReviewState,
        modification_text: str,
        user_id: str,
        db_session,
    ) -> tuple[ReviewState, OpResult]:
        registry = self._get_action_handler_registry()
        registry.ensure_initialized()
        recognizer = self._get_intent_recognizer_factory().create()
        try:
            intent_result = await recognizer.recognize(
                modification_text,
                state.raw_data,
                job_id=state.job_id,
                db_session=db_session,
            )
            handler = registry.get_handler(intent_result.intent_type)
            if handler is None:
                return state, OpResult(
                    status="error",
                    message=f"未找到对应的处理器: {intent_result.intent_type}",
                )

            action_result = await handler.handle(
                intent_result,
                state.job_id,
                {
                    "raw_data": state.raw_data,
                    "display_view": state.display_view,
                    "data_version": state.data_version,
                    "user_id": user_id,
                },
                db_session,
            )
        finally:
            await recognizer.close()

        if action_result.status == "error":
            return state, OpResult(status="error", message=action_result.message)

        if action_result.requires_confirmation:
            modified_data = (action_result.data or {}).get("modified_data")
            modified_display_view = (action_result.data or {}).get("display_view")
            if modified_data is not None:
                state.raw_data = modified_data
            if modified_display_view is not None:
                state.display_view = modified_display_view

            current_db_data = await self.review_repo.get_all_review_data(db_session, state.job_id)
            state.data_version = self._get_state_store().calculate_data_version(current_db_data)
            state.modifications.append(
                {
                    "id": (action_result.data or {}).get("modification_id", str(uuid.uuid4())),
                    "text": modification_text,
                    "intent": intent_result.intent_type,
                    "user_id": user_id,
                    "timestamp": now_shanghai().isoformat(),
                    "parsed_changes": (action_result.data or {}).get("parsed_changes") or [],
                }
            )
            state.last_modified_at = now_shanghai().isoformat()
            state.status = "awaiting_confirmation"
            await self._get_state_store().save(state)

        return state, OpResult(
            status="ok",
            message=action_result.message,
            data={
                "intent": intent_result.intent_type,
                "requires_confirmation": action_result.requires_confirmation,
                **(action_result.data or {}),
            },
        )

    async def confirm_changes(
        self,
        *,
        state: ReviewState,
        user_id: str,
        db_session,
    ) -> tuple[ReviewState, OpResult]:
        current_data = await self.review_repo.get_all_review_data(db_session, state.job_id)
        current_version = self._get_state_store().calculate_data_version(current_data)
        conflicts = self._collect_version_conflicts(state.data_version, current_version)
        if conflicts:
            return state, OpResult(
                status="error",
                message="数据已被其他系统修改，请重新审核",
                data={"conflicts": conflicts},
            )

        result = await self._get_confirmation_executor().handle_confirmation(
            job_id=state.job_id,
            user_id=user_id,
            db_session=db_session,
        )
        if result.get("status") == "error":
            return state, OpResult(status="error", message=result.get("message", "确认修改失败"))

        state.last_confirmed_at = now_shanghai().isoformat()
        state.confirm_count += 1
        state.modifications = []
        state.status = "reviewing"
        await self._get_state_store().save(state)

        return state, OpResult(
            status="ok",
            message="操作已执行，可以继续修改",
            data={
                "job_id": state.job_id,
                "confirm_count": state.confirm_count,
                **(result.get("data") or {}),
            },
        )

    def _get_state_store(self) -> ReviewStateStore:
        if self._state_store is None:
            from .review_state_adapter import RedisReviewStateStore

            self._state_store = RedisReviewStateStore()
        return self._state_store

    def _get_intent_recognizer_factory(self) -> ReviewIntentRecognizerFactory:
        if self._intent_recognizer_factory is None:
            from ....infrastructure.review.legacy_review_handler_adapter import (
                LegacyReviewIntentRecognizerFactory,
            )

            self._intent_recognizer_factory = LegacyReviewIntentRecognizerFactory()
        return self._intent_recognizer_factory

    def _get_action_handler_registry(self) -> ReviewActionHandlerRegistry:
        if self._action_handler_registry is None:
            from ....infrastructure.review.legacy_review_handler_adapter import (
                LegacyReviewActionHandlerRegistry,
            )

            self._action_handler_registry = LegacyReviewActionHandlerRegistry()
        return self._action_handler_registry

    def _get_confirmation_executor(self) -> ReviewConfirmationExecutor:
        if self._confirmation_executor is None:
            from ....infrastructure.review.legacy_review_handler_adapter import (
                LegacyReviewConfirmationExecutor,
            )

            self._confirmation_executor = LegacyReviewConfirmationExecutor()
        return self._confirmation_executor

    @staticmethod
    def _collect_version_conflicts(
        original_version: dict[str, str],
        current_version: dict[str, str],
    ) -> list[dict[str, str]]:
        conflicts: list[dict[str, str]] = []
        for key, original_hash in original_version.items():
            current_hash = current_version.get(key)
            if current_hash and current_hash != original_hash:
                table, record_id = key.split(":", 1)
                conflicts.append(
                    {
                        "table": table,
                        "id": record_id,
                        "message": f"{record_id} 已被其他系统修改",
                    }
                )
        return conflicts
