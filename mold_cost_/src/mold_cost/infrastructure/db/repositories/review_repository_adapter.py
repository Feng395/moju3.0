"""Review repository adapter for legacy compatibility."""

from __future__ import annotations

from typing import Any

from .review_repository import SrcReviewRepository


class LegacyReviewRepositoryAdapter:
    """Compatibility wrapper that now defaults to the src-owned review repository."""

    def __init__(self):
        self._review_repo = None

    @property
    def review_repo(self):
        if self._review_repo is None:
            self._review_repo = SrcReviewRepository()
        return self._review_repo

    async def get_all_review_data(self, db_session, job_id: str) -> dict[str, list[dict[str, Any]]]:
        return await self.review_repo.get_all_review_data(db_session, job_id)

    async def update_all_review_data(self, db_session, job_id: str, data: dict[str, list[dict[str, Any]]]) -> None:
        await self.review_repo.update_all_review_data(db_session, job_id, data)
