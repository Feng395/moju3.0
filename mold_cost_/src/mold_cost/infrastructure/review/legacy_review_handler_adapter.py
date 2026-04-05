"""Infrastructure adapters that isolate legacy review handler imports."""

from __future__ import annotations

import os
from typing import Any


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() == "true"


class LegacyReviewIntentRecognizerFactory:
    """Create the existing recognizer behind a stable adapter boundary."""

    def create(self):
        from agents.intent_recognizer import IntentRecognizer

        return IntentRecognizer(
            use_llm=_env_flag("USE_LLM", default=False),
            use_chat_history=_env_flag("USE_CHAT_HISTORY", default=True),
        )


class LegacyReviewActionHandlerRegistry:
    """Wrap ActionHandlerFactory so domain code no longer imports it directly."""

    def ensure_initialized(self) -> None:
        from agents.action_handlers.base_handler import ActionHandlerFactory

        if ActionHandlerFactory.get_handler("DATA_MODIFICATION") is None:
            ActionHandlerFactory.initialize_handlers()

    def get_handler(self, intent_type: str) -> Any:
        from agents.action_handlers.base_handler import ActionHandlerFactory

        return ActionHandlerFactory.get_handler(intent_type)


class LegacyReviewConfirmationExecutor:
    """Delegate confirmation execution to the existing ConfirmHandler."""

    async def handle_confirmation(
        self,
        *,
        job_id: str,
        user_id: str,
        db_session,
    ) -> dict[str, Any]:
        from agents.confirm_handler import ConfirmHandler

        return await ConfirmHandler().handle_confirmation(
            job_id=job_id,
            user_id=user_id,
            db_session=db_session,
        )
