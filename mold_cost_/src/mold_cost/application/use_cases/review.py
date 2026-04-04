"""审核流程用例集合。"""

from __future__ import annotations

from typing import Any

from ...application.workflows.review_graph import review_graph


class StartReviewUseCase:
    """启动审核流程。"""

    async def execute(self, job_id: str, db_session):
        return await review_graph.start_review(job_id=job_id, db_session=db_session)


class ModifyReviewUseCase:
    """处理审核修改。"""

    async def execute(self, job_id: str, modification_text: str, user_id: str, db_session):
        return await review_graph.handle_modification(
            job_id=job_id,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )


class ConfirmReviewUseCase:
    """确认审核修改。"""

    async def execute(self, job_id: str, user_id: str, db_session):
        return await review_graph.confirm_changes(
            job_id=job_id,
            user_id=user_id,
            db_session=db_session,
        )


class RefreshReviewDataUseCase:
    """刷新审核数据。"""

    async def execute(self, job_id: str, db_session):
        return await review_graph.refresh_data(job_id=job_id, db_session=db_session)


class GetReviewStateUseCase:
    """查询审核状态。"""

    async def execute(self, job_id: str) -> dict[str, Any] | None:
        return await review_graph.get_review_state(job_id=job_id)

    async def execute_with_lock(self, job_id: str) -> dict[str, Any] | None:
        """同时返回审核状态和锁状态，供路由直接响应。"""
        state = await review_graph.get_review_state(job_id=job_id)
        if not state:
            return None
        return {
            "state": state,
            "is_locked": await review_graph.check_lock(job_id=job_id),
        }


class ReviewChatUseCase:
    """审核聊天用例。"""

    async def get_state(self, job_id: str):
        """获取审核状态供聊天上下文使用。"""
        return await review_graph.get_review_state(job_id=job_id)

    async def chat(self, job_id: str, message: str, history: list[dict], current_data):
        """执行非流式聊天。"""
        return await review_graph.chat(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        )

    async def chat_stream(self, job_id: str, message: str, history: list[dict], current_data):
        """执行流式聊天。"""
        async for chunk in review_graph.chat_stream(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        ):
            yield chunk
