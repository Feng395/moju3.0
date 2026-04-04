"""Review data loading helpers."""

from __future__ import annotations

from typing import Any

from ....core.logging import get_logger
from ...review.ports import ReviewDataLoader

logger = get_logger(__name__)


class LegacyReviewDataLoader(ReviewDataLoader):
    """Reuse existing repository, view builder and completeness validator."""

    def __init__(self):
        self._review_repo = None

    @property
    def review_repo(self):
        if self._review_repo is None:
            from api_gateway.repositories.review_repository import ReviewRepository

            self._review_repo = ReviewRepository()
        return self._review_repo

    async def load(self, job_id: str, db_session) -> dict[str, list[dict[str, Any]]]:
        logger.info("Loading review data: job_id=%s", job_id)
        return await self.review_repo.get_all_review_data(db_session, job_id)

    def build_display_view(self, raw_data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        from agents.data_view_builder import DataViewBuilder

        return DataViewBuilder.build_display_view(raw_data)

    def check_completeness(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        from shared.validators.completeness_validator import CompletenessValidator

        return CompletenessValidator.check_data_completeness(raw_data)

    def build_completion_prompt(
        self,
        missing_fields: list[dict[str, Any]],
        raw_data: dict[str, Any],
    ) -> str:
        from shared.validators.completeness_validator import CompletenessValidator

        return CompletenessValidator.generate_completion_prompt(missing_fields, raw_data)
