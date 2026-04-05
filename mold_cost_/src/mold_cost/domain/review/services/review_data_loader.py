"""Review data loading helpers."""

from __future__ import annotations

from typing import Any

from ....core.logging import get_logger
from ....infrastructure.db.repositories.review_repository_adapter import LegacyReviewRepositoryAdapter
from ....infrastructure.review.legacy_review_support_adapter import (
    LegacyReviewCompletenessValidator,
    LegacyReviewDisplayViewBuilder,
)
from ...review.ports import (
    ReviewCompletenessValidator,
    ReviewDataLoader,
    ReviewDisplayViewBuilder,
)

logger = get_logger(__name__)


class LegacyReviewDataLoader(ReviewDataLoader):
    """Load review data while keeping legacy helpers behind adapters."""

    def __init__(
        self,
        review_repository: Any | None = None,
        *,
        display_view_builder: ReviewDisplayViewBuilder | None = None,
        completeness_validator: ReviewCompletenessValidator | None = None,
    ):
        self._review_repo = review_repository
        self._display_view_builder = display_view_builder
        self._completeness_validator = completeness_validator

    @property
    def review_repo(self):
        if self._review_repo is None:
            self._review_repo = LegacyReviewRepositoryAdapter()
        return self._review_repo

    @property
    def display_view_builder(self) -> ReviewDisplayViewBuilder:
        if self._display_view_builder is None:
            self._display_view_builder = LegacyReviewDisplayViewBuilder()
        return self._display_view_builder

    @property
    def completeness_validator(self) -> ReviewCompletenessValidator:
        if self._completeness_validator is None:
            self._completeness_validator = LegacyReviewCompletenessValidator()
        return self._completeness_validator

    async def load(self, job_id: str, db_session) -> dict[str, list[dict[str, Any]]]:
        logger.info("Loading review data: job_id=%s", job_id)
        return await self.review_repo.get_all_review_data(db_session, job_id)

    def build_display_view(self, raw_data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        return self.display_view_builder.build_display_view(raw_data)

    def check_completeness(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        return self.completeness_validator.check_data_completeness(raw_data)

    def build_completion_prompt(
        self,
        missing_fields: list[dict[str, Any]],
        raw_data: dict[str, Any],
    ) -> str:
        return self.completeness_validator.generate_completion_prompt(missing_fields, raw_data)
