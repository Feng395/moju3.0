"""Compatibility names for review-side data helpers now owned by src."""

from __future__ import annotations

from .completeness_validator import SrcReviewCompletenessValidator
from .display_view_builder import SrcReviewDisplayViewBuilder


class LegacyReviewDisplayViewBuilder(SrcReviewDisplayViewBuilder):
    """兼容类名：默认 display-view 实现已迁入 src。"""


class LegacyReviewCompletenessValidator(SrcReviewCompletenessValidator):
    """兼容类名：默认完整性校验实现已迁入 src。"""
