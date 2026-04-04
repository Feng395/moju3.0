"""Review workflow orchestration facade."""

from __future__ import annotations

from typing import Any

from agents.base_agent import OpResult
from shared.timezone_utils import now_shanghai

from ...core.logging import get_logger
from ...domain.review.ports import (
    ReviewChangeApplier,
    ReviewChatExecutionAdapter,
    ReviewDataLoader,
    ReviewNotifier,
    ReviewSessionService,
    ReviewStateStore,
)
from ...domain.review.services.review_change_applier import InteractionAgentReviewChangeApplier
from ...domain.review.services.review_chat_execution_adapter import InteractionAgentReviewChatExecutor
from ...domain.review.services.review_data_loader import LegacyReviewDataLoader
from ...domain.review.services.review_notifier import InteractionAgentReviewNotifier
from ...domain.review.services.review_session_service import RedisReviewSessionService
from ...domain.review.services.review_state_adapter import RedisReviewStateStore
from .review_state import ReviewState

logger = get_logger(__name__)


class ReviewGraph:
    """Workflow-level coordinator for review start / modify / confirm / chat."""

    def __init__(
        self,
        *,
        session_service: ReviewSessionService | None = None,
        state_store: ReviewStateStore | None = None,
        data_loader: ReviewDataLoader | None = None,
        chat_executor: ReviewChatExecutionAdapter | None = None,
        change_applier: ReviewChangeApplier | None = None,
        notifier: ReviewNotifier | None = None,
    ):
        self._compiled_graph = None
        self._session_service = session_service
        self._state_store = state_store
        self._data_loader = data_loader
        self._chat_executor = chat_executor
        self._change_applier = change_applier
        self._notifier = notifier

    def invoke(self, state: ReviewState) -> ReviewState:
        """Sync compatibility hook for future LangGraph execution."""
        return state

    async def start_review(self, job_id: str, db_session):
        """Start a review session and persist its initial workflow state."""
        logger.info("Start review via ReviewGraph: job_id=%s", job_id)

        if not await self._get_session_service().acquire(job_id, timeout=1800):
            return OpResult(status="error", message="该任务正在被其他用户审核中")

        state = await self.load_review_data(job_id=job_id, db_session=db_session)
        state = self.check_completeness(state)
        return await self.generate_review_prompt_or_suggestion(
            state=state,
            db_session=db_session,
            refresh=False,
            reloaded=False,
        )

    async def handle_modification(self, job_id: str, modification_text: str, user_id: str, db_session):
        """Validate session, restore state if needed, then apply a review change."""
        logger.info("Handle review modification via ReviewGraph: job_id=%s", job_id)
        state, error = await self.wait_user_message(
            job_id=job_id,
            db_session=db_session,
            allow_reacquire=True,
            allow_reload=True,
            missing_state_message="审核会话已过期，请重新启动审核",
        )
        if error is not None:
            return error
        return await self.apply_review_change(
            state=state,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )

    async def confirm_changes(self, job_id: str, user_id: str, db_session):
        """Confirm staged review changes and keep the review session alive."""
        logger.info("Confirm review changes via ReviewGraph: job_id=%s", job_id)
        state, error = await self.wait_user_message(
            job_id=job_id,
            db_session=db_session,
            allow_reacquire=False,
            allow_reload=False,
            missing_state_message="未找到审核会话",
        )
        if error is not None:
            return error
        return await self.confirm_and_resume(state=state, user_id=user_id, db_session=db_session)

    async def refresh_data(self, job_id: str, db_session):
        """Refresh review data while keeping the existing route contract."""
        logger.info("Refresh review data via ReviewGraph: job_id=%s", job_id)
        session_service = self._get_session_service()
        state_store = self._get_state_store()

        if not await session_service.ensure_active(job_id, timeout=1800):
            return OpResult(status="error", message="该任务正在被其他用户审核中，无法刷新")

        current_state = await state_store.load(job_id)
        if current_state and current_state.modifications:
            return OpResult(
                status="error",
                message=f"存在 {len(current_state.modifications)} 个未确认的修改，请先确认或取消修改后再刷新",
            )

        state = await self.load_review_data(
            job_id=job_id,
            db_session=db_session,
            previous_state=current_state,
            mark_reloaded=current_state is None,
        )
        state = self.check_completeness(state)
        state.refresh_count = (current_state.refresh_count if current_state else 0) + 1
        state.last_refreshed_at = now_shanghai().isoformat()

        return await self.generate_review_prompt_or_suggestion(
            state=state,
            db_session=db_session,
            refresh=True,
            reloaded=current_state is None,
        )

    async def get_review_state(self, job_id: str):
        """Load persisted review state in route-compatible dict format."""
        state = await self._get_state_store().load(job_id)
        return None if state is None else self.serialize_state(state)

    async def check_lock(self, job_id: str) -> bool:
        """Return whether the review lock still exists."""
        return await self._get_session_service().is_locked(job_id)

    async def chat(self, job_id: str, message: str, history: list[dict], current_data):
        """Non-streaming review chat."""
        return await self._get_chat_executor().chat(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        )

    async def chat_stream(self, job_id: str, message: str, history: list[dict], current_data):
        """Streaming review chat."""
        async for chunk in self._get_chat_executor().chat_stream(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        ):
            yield chunk

    async def load_review_data(
        self,
        *,
        job_id: str,
        db_session,
        previous_state: ReviewState | None = None,
        mark_reloaded: bool = False,
    ) -> ReviewState:
        """Workflow node: load raw review data and normalize it into ReviewState."""
        raw_data = await self._get_data_loader().load(job_id=job_id, db_session=db_session)
        display_view = self._get_data_loader().build_display_view(raw_data)
        state_store = self._get_state_store()

        created_at = previous_state.created_at if previous_state else now_shanghai().isoformat()
        extra = dict(previous_state.extra) if previous_state else {}
        extra.pop("last_completion_prompt", None)

        state = state_store.build_state(
            job_id=job_id,
            status=previous_state.status if previous_state else "pending",
            raw_data=raw_data,
            display_view=display_view,
            completeness={},
            data_version=state_store.calculate_data_version(raw_data),
            modifications=[],
            suggestions=[],
            messages=list(previous_state.messages) if previous_state else [],
            created_at=created_at,
            last_modified_at=previous_state.last_modified_at if previous_state else None,
            last_confirmed_at=previous_state.last_confirmed_at if previous_state else None,
            last_refreshed_at=previous_state.last_refreshed_at if previous_state else None,
            reloaded_at=now_shanghai().isoformat() if mark_reloaded else None,
            refresh_count=previous_state.refresh_count if previous_state else 0,
            confirm_count=previous_state.confirm_count if previous_state else 0,
            extra=extra,
        )
        return state

    def check_completeness(self, state: ReviewState) -> ReviewState:
        """Workflow node: evaluate completeness and derive status."""
        completeness = self._get_data_loader().check_completeness(state.raw_data)
        state.completeness = completeness
        state.status = "reviewing" if completeness.get("is_complete") else "pending_completion"
        return state

    async def generate_review_prompt_or_suggestion(
        self,
        *,
        state: ReviewState,
        db_session,
        refresh: bool,
        reloaded: bool,
    ) -> OpResult:
        """Workflow node: persist state and optionally generate completion guidance."""
        await self._get_state_store().save(state)
        await self._get_notifier().push_display_view(state.job_id, state.display_view, db_session=db_session)

        if not state.completeness.get("is_complete", True):
            missing_fields = state.completeness.get("missing_fields", [])
            completion_prompt = self._get_data_loader().build_completion_prompt(missing_fields, state.raw_data)
            completion_suggestion = await self._get_chat_executor().generate_completion_suggestion(
                completion_prompt,
                state.raw_data,
            )
            state.suggestions = [
                {
                    "kind": "completion",
                    "prompt": completion_prompt,
                    "suggestion": completion_suggestion,
                    "created_at": now_shanghai().isoformat(),
                }
            ]
            state.extra["last_completion_prompt"] = completion_prompt
            await self._get_state_store().save(state)
            await self._get_notifier().push_completion_request(
                state.job_id,
                {
                    "missing_fields": missing_fields,
                    "suggestion": completion_suggestion,
                    "message": self._build_completion_message(refresh=refresh, reloaded=reloaded),
                },
                db_session=db_session,
            )
            if refresh:
                return OpResult(
                    status="ok",
                    message="数据已刷新",
                    data={
                        "job_id": state.job_id,
                        "refresh_count": state.refresh_count,
                        "features_count": len(state.raw_data.get("features", [])),
                        "job_price_snapshots_count": len(
                            state.raw_data.get("job_price_snapshots") or state.raw_data.get("price_snapshots", [])
                        ),
                        "subgraphs_count": len(state.raw_data.get("subgraphs", [])),
                        "is_complete": False,
                        "missing_fields_count": len(missing_fields),
                        "suggestion": completion_suggestion,
                    },
                )
            return OpResult(
                status="pending_completion",
                message="数据不完整，需要先补全必填字段",
                data={
                    "job_id": state.job_id,
                    "completeness": state.completeness,
                    "suggestion": completion_suggestion,
                },
            )

        message = "数据已刷新" if refresh else "审核流程已启动"
        data = {
            "job_id": state.job_id,
            "features_count": len(state.raw_data.get("features", [])),
            "job_price_snapshots_count": len(
                state.raw_data.get("job_price_snapshots") or state.raw_data.get("price_snapshots", [])
            ),
            "subgraphs_count": len(state.raw_data.get("subgraphs", [])),
        }
        if refresh:
            data.update(
                {
                    "refresh_count": state.refresh_count,
                    "is_complete": True,
                    "missing_fields_count": 0,
                }
            )
        return OpResult(status="ok", message=message, data=data)

    async def wait_user_message(
        self,
        *,
        job_id: str,
        db_session,
        allow_reacquire: bool,
        allow_reload: bool,
        missing_state_message: str,
    ) -> tuple[ReviewState | None, OpResult | None]:
        """Workflow node: establish review session boundaries before processing user input."""
        session_service = self._get_session_service()
        state_store = self._get_state_store()

        if allow_reacquire:
            if not await session_service.ensure_active(job_id, timeout=1800):
                return None, OpResult(status="error", message="会话已被其他用户占用或已过期，请重新启动审核")
        else:
            if not await session_service.is_locked(job_id):
                return None, OpResult(status="error", message="审核会话已过期或被释放")
            await session_service.renew(job_id, timeout=1800)

        await state_store.renew(job_id, timeout=3600)
        state = await state_store.load(job_id)
        if state is not None:
            return state, None

        if allow_reload and db_session is not None:
            reloaded_state = await self.load_review_data(
                job_id=job_id,
                db_session=db_session,
                mark_reloaded=True,
            )
            reloaded_state = self.check_completeness(reloaded_state)
            await self.generate_review_prompt_or_suggestion(
                state=reloaded_state,
                db_session=db_session,
                refresh=False,
                reloaded=True,
            )
            await self._get_notifier().push_system_message(
                job_id,
                "已自动重新加载历史数据。",
                db_session=db_session,
            )
            return reloaded_state, None

        return None, OpResult(status="error", message=missing_state_message)

    async def apply_review_change(
        self,
        *,
        state: ReviewState,
        modification_text: str,
        user_id: str,
        db_session,
    ):
        """Workflow node: delegate actual modification execution through the adapter boundary."""
        return await self._get_change_applier().handle_modification(
            job_id=state.job_id,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )

    async def confirm_and_resume(self, *, state: ReviewState, user_id: str, db_session):
        """Workflow node: confirm changes and keep the review session resumable."""
        return await self._get_change_applier().confirm_changes(
            job_id=state.job_id,
            user_id=user_id,
            db_session=db_session,
        )

    def to_state(self, job_id: str, **kwargs) -> ReviewState:
        """Construct a workflow state object."""
        return ReviewState(job_id=job_id, **kwargs)

    def serialize_state(self, state: ReviewState) -> dict[str, Any]:
        """Serialize workflow state for compatibility callers."""
        return state.to_payload()

    def get_compiled_graph(self):
        """Expose an explicit node graph when LangGraph is available."""
        if self._compiled_graph is not None:
            return self._compiled_graph

        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            logger.info("LangGraph unavailable; ReviewGraph will run via direct workflow methods")
            return None

        graph = StateGraph(dict)
        for node_name in (
            "load_review_data",
            "check_completeness",
            "generate_review_prompt_or_suggestion",
            "wait_user_message",
            "apply_review_change",
            "confirm_and_resume",
        ):
            graph.add_node(node_name, self._build_langgraph_node(node_name))

        graph.add_edge(START, "load_review_data")
        graph.add_edge("load_review_data", "check_completeness")
        graph.add_edge("check_completeness", "generate_review_prompt_or_suggestion")
        graph.add_edge("generate_review_prompt_or_suggestion", "wait_user_message")
        graph.add_edge("wait_user_message", "apply_review_change")
        graph.add_edge("apply_review_change", "confirm_and_resume")
        graph.add_edge("confirm_and_resume", END)
        self._compiled_graph = graph.compile()
        return self._compiled_graph

    def _build_langgraph_node(self, node_name: str):
        def _node(state: dict[str, Any]) -> dict[str, Any]:
            return {**state, "_last_review_node": node_name}

        return _node

    @staticmethod
    def _build_completion_message(*, refresh: bool, reloaded: bool) -> str:
        if refresh:
            return "刷新后发现部分必填字段为空，请补全这些字段"
        if reloaded:
            return "数据已重新加载，但仍存在必填字段缺失，请先补全这些字段"
        return "发现部分必填字段为空，请先补全这些字段"

    @staticmethod
    def _get_agent():
        from agents.interaction_agent import InteractionAgent

        return InteractionAgent()

    def _get_session_service(self) -> ReviewSessionService:
        if self._session_service is None:
            self._session_service = RedisReviewSessionService()
        return self._session_service

    def _get_state_store(self) -> ReviewStateStore:
        if self._state_store is None:
            self._state_store = RedisReviewStateStore()
        return self._state_store

    def _get_data_loader(self) -> ReviewDataLoader:
        if self._data_loader is None:
            self._data_loader = LegacyReviewDataLoader()
        return self._data_loader

    def _get_chat_executor(self) -> ReviewChatExecutionAdapter:
        if self._chat_executor is None:
            self._chat_executor = InteractionAgentReviewChatExecutor(agent_factory=self._get_agent)
        return self._chat_executor

    def _get_change_applier(self) -> ReviewChangeApplier:
        if self._change_applier is None:
            self._change_applier = InteractionAgentReviewChangeApplier(agent_factory=self._get_agent)
        return self._change_applier

    def _get_notifier(self) -> ReviewNotifier:
        if self._notifier is None:
            self._notifier = InteractionAgentReviewNotifier(agent_factory=self._get_agent)
        return self._notifier


review_graph = ReviewGraph()
