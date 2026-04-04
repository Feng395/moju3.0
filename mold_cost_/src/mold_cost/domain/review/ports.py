"""Review domain ports."""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol

from ...application.workflows.review_state import ReviewState


class ReviewService(Protocol):
    """Facade used by the application layer."""

    async def start(self, job_id: str, db_session) -> Any: ...

    async def modify(self, job_id: str, modification_text: str, user_id: str, db_session) -> Any: ...

    async def confirm(self, job_id: str, user_id: str, db_session) -> Any: ...

    async def refresh(self, job_id: str, db_session) -> Any: ...


class ReviewSessionService(Protocol):
    """Manage review-session locking semantics."""

    async def acquire(self, job_id: str, timeout: int = 1800) -> bool: ...

    async def ensure_active(self, job_id: str, timeout: int = 1800) -> bool: ...

    async def renew(self, job_id: str, timeout: int = 1800) -> bool: ...

    async def is_locked(self, job_id: str) -> bool: ...


class ReviewStateStore(Protocol):
    """Persist and restore workflow state."""

    def build_state(self, job_id: str, **kwargs: Any) -> ReviewState: ...

    def calculate_data_version(self, raw_data: dict[str, Any]) -> dict[str, str]: ...

    def serialize(self, state: ReviewState) -> dict[str, Any]: ...

    async def load(self, job_id: str) -> ReviewState | None: ...

    async def save(self, state: ReviewState, ex: int = 3600) -> None: ...

    async def renew(self, job_id: str, timeout: int = 3600) -> bool: ...


class ReviewDataLoader(Protocol):
    """Load review data and derive workflow inputs."""

    async def load(self, job_id: str, db_session) -> dict[str, list[dict[str, Any]]]: ...

    def build_display_view(self, raw_data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]: ...

    def check_completeness(self, raw_data: dict[str, Any]) -> dict[str, Any]: ...

    def build_completion_prompt(
        self,
        missing_fields: list[dict[str, Any]],
        raw_data: dict[str, Any],
    ) -> str: ...


class ReviewChatExecutionAdapter(Protocol):
    """Handle LLM-backed review chat and prompt generation."""

    async def generate_completion_suggestion(
        self,
        prompt: str,
        context_data: dict[str, Any],
    ) -> str: ...

    async def chat(
        self,
        job_id: str,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any] | None,
    ) -> str: ...

    async def chat_stream(
        self,
        job_id: str,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any] | None,
    ) -> AsyncIterator[str]: ...


class ReviewChangeApplier(Protocol):
    """Apply review changes and confirmations."""

    async def handle_modification(
        self,
        job_id: str,
        modification_text: str,
        user_id: str,
        db_session,
    ) -> Any: ...

    async def confirm_changes(self, job_id: str, user_id: str, db_session) -> Any: ...


class ReviewNotifier(Protocol):
    """Push review-side effects to websocket / persistence channels."""

    async def push_display_view(self, job_id: str, display_view: list[dict[str, Any]], db_session=None) -> None: ...

    async def push_completion_request(
        self,
        job_id: str,
        completion_data: dict[str, Any],
        db_session=None,
    ) -> None: ...

    async def push_system_message(self, job_id: str, message_text: str, db_session=None) -> None: ...
