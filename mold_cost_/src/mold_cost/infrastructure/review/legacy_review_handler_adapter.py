"""Infrastructure adapters that isolate legacy review handler imports."""

from __future__ import annotations

from .action_handler_runtime import SrcReviewActionHandlerRegistry
from .confirmation_executor import ReviewConfirmationExecutorAdapter
from .intent_recognizer_runtime import SrcReviewIntentRecognizerFactory


def build_default_review_change_applier(*, state_store, review_repository):
    """Build the default review change applier with legacy collaborators."""

    from ...domain.review.services.review_change_applier import InteractionAgentReviewChangeApplier

    return InteractionAgentReviewChangeApplier(
        state_store=state_store,
        review_repository=review_repository,
        intent_recognizer_factory=SrcReviewIntentRecognizerFactory(),
        action_handler_registry=SrcReviewActionHandlerRegistry(),
        confirmation_executor=ReviewConfirmationExecutorAdapter(review_repository=review_repository),
    )
