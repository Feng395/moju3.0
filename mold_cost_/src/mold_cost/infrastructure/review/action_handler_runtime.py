"""Src-owned runtime for review action handler registration."""

from __future__ import annotations

from typing import Any

from ...core.logging import get_logger
from .review_action_handlers import (
    FeatureRecognitionReviewActionHandler,
    GeneralChatReviewActionHandler,
    PriceCalculationReviewActionHandler,
    WeightPriceCalculationReviewActionHandler,
)
from .weight_price_query_handler import WeightPriceQueryReviewActionHandler

logger = get_logger(__name__)


class SrcReviewActionHandlerRegistry:
    """Own the review handler mapping from src while legacy handlers are still being migrated."""

    def ensure_initialized(self) -> None:
        # 中文注释：默认只预热已迁入 src 的轻量 handler，复杂 legacy handler 继续按需加载。
        self._src_owned_handlers()

    def get_handler(self, intent_type: str) -> Any:
        handler = self._src_owned_handlers().get(intent_type)
        if handler is not None:
            return handler
        return self._legacy_handler_fallbacks().get(intent_type)

    @classmethod
    def _src_owned_handlers(cls) -> dict[str, Any]:
        if not hasattr(cls, "_cached_src_handlers"):
            # 中文注释：这三类 intent 只负责准备待确认动作，已经可以完全脱离旧 handler 工厂。
            cls._cached_src_handlers = {
                "FEATURE_RECOGNITION": FeatureRecognitionReviewActionHandler(),
                "GENERAL_CHAT": GeneralChatReviewActionHandler(),
                "PRICE_CALCULATION": PriceCalculationReviewActionHandler(),
                "WEIGHT_PRICE_CALCULATION": WeightPriceCalculationReviewActionHandler(),
                "WEIGHT_PRICE_QUERY": WeightPriceQueryReviewActionHandler(),
            }
            logger.info(
                "Initialized src-owned review handlers: intents=%s",
                ", ".join(sorted(cls._cached_src_handlers.keys())),
            )
        return cls._cached_src_handlers

    @classmethod
    def _legacy_handler_fallbacks(cls) -> dict[str, Any]:
        if not hasattr(cls, "_cached_legacy_handlers"):
            from agents.action_handlers.data_modification_handler import DataModificationHandler
            from agents.action_handlers.query_details_handler import QueryDetailsHandler

            # 中文注释：剩余复杂交互类 handler 先保留旧实现，但实例化与映射关系改由 src 控制。
            cls._cached_legacy_handlers = {
                "DATA_MODIFICATION": DataModificationHandler(),
                "QUERY_DETAILS": QueryDetailsHandler(),
            }
            logger.info(
                "Initialized fallback review handlers: intents=%s",
                ", ".join(sorted(cls._cached_legacy_handlers.keys())),
            )
        return cls._cached_legacy_handlers


def initialize_review_action_handlers() -> None:
    """Warm up the default review action handler registry during API startup."""

    SrcReviewActionHandlerRegistry().ensure_initialized()
