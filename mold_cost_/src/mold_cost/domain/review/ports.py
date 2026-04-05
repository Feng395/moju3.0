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

    # 这一层只回答“会话是否有效”，不关心审核数据内容。
    async def acquire(self, job_id: str, timeout: int = 1800) -> bool: ...

    async def ensure_active(self, job_id: str, timeout: int = 1800) -> bool: ...

    async def renew(self, job_id: str, timeout: int = 1800) -> bool: ...

    async def is_locked(self, job_id: str) -> bool: ...


class ReviewStateStore(Protocol):
    """Persist and restore workflow state."""

    # 这一层隔离 Redis / 序列化细节，避免 workflow 直接依赖具体存储实现。
    def build_state(self, job_id: str, **kwargs: Any) -> ReviewState: ...

    def calculate_data_version(self, raw_data: dict[str, Any]) -> dict[str, str]: ...

    def serialize(self, state: ReviewState) -> dict[str, Any]: ...

    async def load(self, job_id: str) -> ReviewState | None: ...

    async def save(self, state: ReviewState, ex: int = 3600) -> None: ...

    async def renew(self, job_id: str, timeout: int = 3600) -> bool: ...


class ReviewDataLoader(Protocol):
    """Load review data and derive workflow inputs."""

    # 数据加载、display view 构建、完整性检查都收敛在这个边界。
    async def load(self, job_id: str, db_session) -> dict[str, list[dict[str, Any]]]: ...

    def build_display_view(self, raw_data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]: ...

    def check_completeness(self, raw_data: dict[str, Any]) -> dict[str, Any]: ...

    def build_completion_prompt(
        self,
        missing_fields: list[dict[str, Any]],
        raw_data: dict[str, Any],
    ) -> str: ...


class ReviewDisplayViewBuilder(Protocol):
    """Build workflow-facing display views from raw review data."""

    def build_display_view(self, raw_data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]: ...


class ReviewCompletenessValidator(Protocol):
    """Validate raw review data completeness and derive completion prompts."""

    def check_data_completeness(self, raw_data: dict[str, Any]) -> dict[str, Any]: ...

    def generate_completion_prompt(
        self,
        missing_fields: list[dict[str, Any]],
        raw_data: dict[str, Any],
    ) -> str: ...


class ReviewChatExecutionAdapter(Protocol):
    """Handle LLM-backed review chat and prompt generation."""

    # 统一封装 suggestion 和 review chat，避免 workflow 混入模型调用细节。
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


class ReviewIntentRecognizer(Protocol):
    """Recognize review-side user intent."""

    async def recognize(
        self,
        message: str,
        context: dict[str, Any],
        job_id: str | None = None,
        db_session=None,
    ) -> Any: ...

    async def close(self) -> None: ...


class ReviewIntentRecognizerFactory(Protocol):
    """Build recognizers without leaking legacy imports into domain code."""

    def create(self) -> ReviewIntentRecognizer: ...


class ReviewActionHandlerRegistry(Protocol):
    """Resolve action handlers by intent type."""

    def ensure_initialized(self) -> None: ...

    def get_handler(self, intent_type: str) -> Any: ...


class ReviewConfirmationExecutor(Protocol):
    """Execute confirmation side effects for pending review actions."""

    async def handle_confirmation(
        self,
        *,
        job_id: str,
        user_id: str,
        db_session,
    ) -> dict[str, Any]: ...


class ReviewChangeApplier(Protocol):
    """Apply review changes and confirmations."""

    # 修改和确认直接接收 workflow state，便于逐步把状态推进从 InteractionAgent 挪回 review 链。
    async def handle_modification(
        self,
        *,
        state: ReviewState,
        modification_text: str,
        user_id: str,
        db_session,
    ) -> tuple[ReviewState, Any]: ...

    async def confirm_changes(
        self,
        *,
        state: ReviewState,
        user_id: str,
        db_session,
    ) -> tuple[ReviewState, Any]: ...


class ReviewNotifier(Protocol):
    """Push review-side effects to websocket / persistence channels."""

    # 所有推送副作用统一走 notifier，便于后续替换消息基础设施。
    async def push_display_view(self, job_id: str, display_view: list[dict[str, Any]], db_session=None) -> None: ...

    async def push_completion_request(
        self,
        job_id: str,
        completion_data: dict[str, Any],
        db_session=None,
    ) -> None: ...

    async def push_system_message(self, job_id: str, message_text: str, db_session=None) -> None: ...


class MessagePersistence(Protocol):
    """Persist websocket/review messages without leaking legacy imports."""

    async def push_and_persist(
        self,
        *,
        job_id: str,
        ws_message: dict[str, Any],
        db_session=None,
        ws_manager=None,
    ) -> None: ...

    def should_persist(self, ws_message: dict[str, Any]) -> bool: ...

    async def persist_message(self, *, job_id: str, ws_message: dict[str, Any], db_session) -> None: ...
