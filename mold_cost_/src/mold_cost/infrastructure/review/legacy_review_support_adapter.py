"""Infrastructure adapters for legacy review-side data helpers."""

from __future__ import annotations

from typing import Any


class LegacyReviewDisplayViewBuilder:
    """Expose the legacy display-view builder behind a src-owned adapter."""

    def build_display_view(self, raw_data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        from agents.data_view_builder import DataViewBuilder

        return DataViewBuilder.build_display_view(raw_data)


class LegacyReviewCompletenessValidator:
    """Expose completeness validation behind a src-owned adapter."""

    def check_data_completeness(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        from shared.validators.completeness_validator import CompletenessValidator

        return CompletenessValidator.check_data_completeness(raw_data)

    def generate_completion_prompt(
        self,
        missing_fields: list[dict[str, Any]],
        raw_data: dict[str, Any],
    ) -> str:
        from shared.validators.completeness_validator import CompletenessValidator

        return CompletenessValidator.generate_completion_prompt(missing_fields, raw_data)
