"""Review use cases backed by the workflow graph."""

from __future__ import annotations

from typing import Any

from ...application.workflows.review_graph import review_graph


class StartReviewUseCase:
    """Advance the review workflow through load/check/prompt nodes."""
    # use case 保持极薄，只负责把 HTTP / worker 入口导向 workflow。

    async def execute(self, job_id: str, db_session):
        return await review_graph.start_review(job_id=job_id, db_session=db_session)


class ModifyReviewUseCase:
    """Resume the workflow from wait_user_message into apply_review_change."""

    async def execute(self, job_id: str, modification_text: str, user_id: str, db_session):
        return await review_graph.handle_modification(
            job_id=job_id,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )


class ConfirmReviewUseCase:
    """Confirm staged changes and resume the review session."""

    async def execute(self, job_id: str, user_id: str, db_session):
        return await review_graph.confirm_changes(
            job_id=job_id,
            user_id=user_id,
            db_session=db_session,
        )


class RefreshReviewDataUseCase:
    """Reload review data and rerun the start-of-review nodes."""

    async def execute(self, job_id: str, db_session):
        return await review_graph.refresh_data(job_id=job_id, db_session=db_session)


class GetReviewStateUseCase:
    """Expose persisted review state without changing route payloads."""

    async def execute(self, job_id: str) -> dict[str, Any] | None:
        return await review_graph.get_review_state(job_id=job_id)

    async def execute_with_lock(self, job_id: str) -> dict[str, Any] | None:
        state = await review_graph.get_review_state(job_id=job_id)
        if not state:
            return None
        return {
            "state": state,
            "is_locked": await review_graph.check_lock(job_id=job_id),
        }


class ReviewChatUseCase:
    """Keep chat routes on top of the chat execution adapter."""
    # 聊天路由不直接碰 session/store 细节，统一经由 review_graph 进入适配层。

    async def get_state(self, job_id: str):
        return await review_graph.get_review_state(job_id=job_id)

    async def chat(self, job_id: str, message: str, history: list[dict], current_data):
        return await review_graph.chat(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        )

    async def chat_stream(self, job_id: str, message: str, history: list[dict], current_data):
        async for chunk in review_graph.chat_stream(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        ):
            yield chunk
