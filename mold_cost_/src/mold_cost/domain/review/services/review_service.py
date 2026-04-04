"""审核领域桥接服务。"""

from __future__ import annotations

from ...application.workflows.review_graph import review_graph


class LegacyReviewService:
    """桥接审核工作流。"""

    async def start(self, job_id: str, db_session):
        return await review_graph.start_review(job_id=job_id, db_session=db_session)

    async def modify(self, job_id: str, modification_text: str, user_id: str, db_session):
        return await review_graph.handle_modification(
            job_id=job_id,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )

    async def confirm(self, job_id: str, user_id: str, db_session):
        return await review_graph.confirm_changes(job_id=job_id, user_id=user_id, db_session=db_session)


review_service = LegacyReviewService()
