"""Review workflow orchestration facade."""

from __future__ import annotations

from collections.abc import Mapping
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
from ...infrastructure.db.repositories.review_repository_adapter import LegacyReviewRepositoryAdapter
from ...infrastructure.review.legacy_review_handler_adapter import build_default_review_change_applier
from ...infrastructure.workflows.review_file_checkpoint_store import ReviewFileCheckpointStore
from .review_state import ReviewState

logger = get_logger(__name__)


class ReviewGraph:
    """Workflow-level coordinator for review start / modify / confirm / chat."""

    CHECKPOINT_NAMESPACE = "review_workflow"

    def __init__(
        self,
        *,
        session_service: ReviewSessionService | None = None,
        state_store: ReviewStateStore | None = None,
        data_loader: ReviewDataLoader | None = None,
        chat_executor: ReviewChatExecutionAdapter | None = None,
        change_applier: ReviewChangeApplier | None = None,
        notifier: ReviewNotifier | None = None,
        durable_store=None,
    ):
        self._compiled_graph = None
        self._checkpointer = None
        self._runtime_contexts: dict[str, dict[str, Any]] = {}
        self._review_repository = None
        self._session_service = session_service
        self._state_store = state_store
        self._data_loader = data_loader
        self._chat_executor = chat_executor
        self._change_applier = change_applier
        self._notifier = notifier
        self._durable_store = durable_store if durable_store is not None else ReviewFileCheckpointStore()

    def invoke(self, state: ReviewState) -> ReviewState:
        return state

    async def start_review(self, job_id: str, db_session):
        logger.info("Start review via ReviewGraph: job_id=%s", job_id)
        # 中文注释：启动审核时先抢占会话锁，确保同一 job 只有一个活跃审核会话。
        if not await self._get_session_service().acquire(job_id, timeout=1800):
            return OpResult(status="error", message="该任务正在被其他用户审核中")
        if self.get_compiled_graph() is None:
            return await self._start_review_direct(job_id=job_id, db_session=db_session)
        return await self._run_langgraph_mode(
            job_id=job_id,
            db_session=db_session,
            input_payload={"job_id": job_id, "mode": "start", "refresh": False, "reloaded": False},
        )

    async def handle_modification(self, job_id: str, modification_text: str, user_id: str, db_session):
        logger.info("Handle review modification via ReviewGraph: job_id=%s", job_id)
        if self.get_compiled_graph() is None:
            return await self._handle_modification_direct(
                job_id=job_id,
                modification_text=modification_text,
                user_id=user_id,
                db_session=db_session,
            )
        interrupted = self.get_graph_state(job_id).interrupts
        if interrupted:
            return await self._run_langgraph_mode(
                job_id=job_id,
                db_session=db_session,
                resume_payload={
                    "action": "modification",
                    "modification_text": modification_text,
                    "user_id": user_id,
                },
            )
        return await self._run_langgraph_mode(
            job_id=job_id,
            db_session=db_session,
            input_payload={
                "job_id": job_id,
                "mode": "modify",
                "modification_text": modification_text,
                "user_id": user_id,
            },
        )

    async def confirm_changes(self, job_id: str, user_id: str, db_session):
        logger.info("Confirm review changes via ReviewGraph: job_id=%s", job_id)
        if self.get_compiled_graph() is None:
            return await self._confirm_changes_direct(job_id=job_id, user_id=user_id, db_session=db_session)
        interrupted = self.get_graph_state(job_id).interrupts
        if interrupted:
            return await self._run_langgraph_mode(
                job_id=job_id,
                db_session=db_session,
                resume_payload={"action": "confirm", "user_id": user_id},
            )
        return await self._run_langgraph_mode(
            job_id=job_id,
            db_session=db_session,
            input_payload={"job_id": job_id, "mode": "confirm", "user_id": user_id},
        )

    async def refresh_data(self, job_id: str, db_session):
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
        if self.get_compiled_graph() is None:
            return await self._refresh_data_direct(job_id=job_id, db_session=db_session, current_state=current_state)
        return await self._run_langgraph_mode(
            job_id=job_id,
            db_session=db_session,
            input_payload={
                "job_id": job_id,
                "mode": "refresh",
                "refresh": True,
                "reloaded": current_state is None,
                "previous_state": None if current_state is None else self.serialize_state(current_state),
            },
        )

    async def get_review_state(self, job_id: str):
        state = await self._get_state_store().load(job_id)
        if state is None:
            state = self._load_durable_state(job_id)
        return None if state is None else self.serialize_state(state)

    async def check_lock(self, job_id: str) -> bool:
        return await self._get_session_service().is_locked(job_id)

    async def chat(self, job_id: str, message: str, history: list[dict], current_data):
        return await self._get_chat_executor().chat(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        )

    async def chat_stream(self, job_id: str, message: str, history: list[dict], current_data):
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
        # 中文注释：该节点只负责取数和组装状态，不负责推送消息或执行聊天。
        raw_data = await self._get_data_loader().load(job_id=job_id, db_session=db_session)
        display_view = self._get_data_loader().build_display_view(raw_data)
        state_store = self._get_state_store()
        created_at = previous_state.created_at if previous_state else now_shanghai().isoformat()
        extra = dict(previous_state.extra) if previous_state else {}
        extra.pop("last_completion_prompt", None)
        return state_store.build_state(
            job_id=job_id,
            status=previous_state.status if previous_state else "pending",
            raw_data=raw_data,
            display_view=display_view,
            completeness={},
            data_version=state_store.calculate_data_version(raw_data),
            modifications=list(previous_state.modifications) if previous_state else [],
            suggestions=[],
            messages=list(previous_state.messages) if previous_state else [],
            created_at=created_at,
            last_modified_at=previous_state.last_modified_at if previous_state else None,
            last_confirmed_at=previous_state.last_confirmed_at if previous_state else None,
            last_refreshed_at=previous_state.last_refreshed_at if previous_state else None,
            reloaded_at=now_shanghai().isoformat() if mark_reloaded else None,
            refresh_count=previous_state.refresh_count if previous_state else 0,
            confirm_count=previous_state.confirm_count if previous_state else 0,
            current_node=previous_state.current_node if previous_state else None,
            waiting_for=previous_state.waiting_for if previous_state else None,
            resume_from=previous_state.resume_from if previous_state else None,
            checkpoint_id=previous_state.checkpoint_id if previous_state else None,
            extra=extra,
        )

    def check_completeness(self, state: ReviewState) -> ReviewState:
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
        await self._get_state_store().save(state)
        await self._get_notifier().push_display_view(state.job_id, state.display_view, db_session=db_session)
        if not state.completeness.get("is_complete", True):
            missing_fields = state.completeness.get("missing_fields", [])
            completion_prompt = self._get_data_loader().build_completion_prompt(missing_fields, state.raw_data)
            completion_suggestion = await self._get_chat_executor().generate_completion_suggestion(
                completion_prompt,
                state.raw_data,
            )
            state.suggestions = [{
                "kind": "completion",
                "prompt": completion_prompt,
                "suggestion": completion_suggestion,
                "created_at": now_shanghai().isoformat(),
            }]
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
                data={"job_id": state.job_id, "completeness": state.completeness, "suggestion": completion_suggestion},
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
            data.update({"refresh_count": state.refresh_count, "is_complete": True, "missing_fields_count": 0})
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
        session_service = self._get_session_service()
        state_store = self._get_state_store()
        if allow_reacquire:
            # 中文注释：修改入口允许自动续租或重建锁，尽量延长审核会话连续性。
            if not await session_service.ensure_active(job_id, timeout=1800):
                return None, OpResult(status="error", message="会话已被其他用户占用或已过期，请重新启动审核")
        else:
            # 中文注释：confirm 入口不偷偷重建会话，避免掩盖真实的会话失效问题。
            if not await session_service.is_locked(job_id):
                return None, OpResult(status="error", message="审核会话已过期或被释放")
            await session_service.renew(job_id, timeout=1800)
        await state_store.renew(job_id, timeout=3600)
        state = await state_store.load(job_id)
        if state is None:
            state = self._load_durable_state(job_id)
            if state is not None:
                await state_store.save(state)
        if state is not None:
            return state, None
        if allow_reload and db_session is not None:
            # 中文注释：状态丢失但锁仍有效时，重建起始状态，避免让用户整轮审核白做。
            reloaded_state = await self.load_review_data(job_id=job_id, db_session=db_session, mark_reloaded=True)
            reloaded_state = self.check_completeness(reloaded_state)
            await self.generate_review_prompt_or_suggestion(
                state=reloaded_state,
                db_session=db_session,
                refresh=False,
                reloaded=True,
            )
            await self._get_notifier().push_system_message(job_id, "已自动重新加载历史数据。", db_session=db_session)
            return reloaded_state, None
        return None, OpResult(status="error", message=missing_state_message)

    async def apply_review_change(
        self,
        *,
        state: ReviewState,
        modification_text: str,
        user_id: str,
        db_session,
    ) -> tuple[ReviewState, OpResult]:
        return await self._get_change_applier().handle_modification(
            state=state,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )

    async def confirm_and_resume(self, *, state: ReviewState, user_id: str, db_session) -> tuple[ReviewState, OpResult]:
        return await self._get_change_applier().confirm_changes(state=state, user_id=user_id, db_session=db_session)

    def to_state(self, job_id: str, **kwargs) -> ReviewState:
        return ReviewState(job_id=job_id, **kwargs)

    def serialize_state(self, state: ReviewState) -> dict[str, Any]:
        return state.to_payload()

    def checkpoint_config(self, job_id: str, checkpoint_id: str | None = None) -> dict[str, Any]:
        # 中文注释：当前 review graph 还未拆成子图，checkpoint_ns 保持默认空字符串即可稳定读写快照。
        configurable = {"thread_id": job_id}
        if checkpoint_id:
            configurable["checkpoint_id"] = checkpoint_id
        return {"configurable": configurable}

    def get_graph_state(self, job_id: str):
        graph = self.get_compiled_graph()
        if graph is None:
            return None
        return graph.get_state(self.checkpoint_config(job_id))

    def get_compiled_graph(self):
        if self._compiled_graph is not None:
            return self._compiled_graph
        try:
            from langgraph.checkpoint.memory import InMemorySaver
            from langgraph.graph import END, START, StateGraph
        except Exception:
            logger.info("LangGraph unavailable; ReviewGraph will run via direct workflow methods")
            return None
        self._checkpointer = InMemorySaver()
        graph = StateGraph(dict)
        graph.add_node("load_review_data", self._langgraph_load_review_data)
        graph.add_node("check_completeness", self._langgraph_check_completeness)
        graph.add_node("generate_review_prompt_or_suggestion", self._langgraph_generate_review_prompt_or_suggestion)
        graph.add_node("wait_user_message", self._langgraph_wait_user_message)
        graph.add_node("apply_review_change", self._langgraph_apply_review_change)
        graph.add_node("confirm_and_resume", self._langgraph_confirm_and_resume)
        graph.add_edge(START, "load_review_data")
        graph.add_edge("load_review_data", "check_completeness")
        graph.add_edge("check_completeness", "generate_review_prompt_or_suggestion")
        graph.add_edge("generate_review_prompt_or_suggestion", "wait_user_message")
        graph.add_edge("wait_user_message", "apply_review_change")
        graph.add_edge("apply_review_change", "confirm_and_resume")
        graph.add_edge("confirm_and_resume", END)
        self._compiled_graph = graph.compile(checkpointer=self._checkpointer)
        return self._compiled_graph

    @staticmethod
    def _build_completion_message(*, refresh: bool, reloaded: bool) -> str:
        if refresh:
            return "刷新后发现部分必填字段为空，请补全这些字段"
        if reloaded:
            return "数据已重新加载，但仍存在必填字段缺失，请先补全这些字段"
        return "发现部分必填字段为空，请先补全这些字段"

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
            self._data_loader = LegacyReviewDataLoader(review_repository=self._get_review_repository())
        return self._data_loader

    def _get_chat_executor(self) -> ReviewChatExecutionAdapter:
        if self._chat_executor is None:
            # 中文注释：默认 chat executor 已直接走共享 LLM 配置，不再默认实例化 InteractionAgent。
            self._chat_executor = InteractionAgentReviewChatExecutor()
        return self._chat_executor

    def _get_change_applier(self) -> ReviewChangeApplier:
        if self._change_applier is None:
            self._change_applier = build_default_review_change_applier(
                state_store=self._get_state_store(),
                review_repository=self._get_review_repository(),
            )
        return self._change_applier

    def _get_notifier(self) -> ReviewNotifier:
        if self._notifier is None:
            self._notifier = InteractionAgentReviewNotifier()
        return self._notifier

    def _get_review_repository(self):
        if self._review_repository is None:
            self._review_repository = LegacyReviewRepositoryAdapter()
        return self._review_repository

    async def _start_review_direct(self, *, job_id: str, db_session) -> OpResult:
        state = await self.load_review_data(job_id=job_id, db_session=db_session)
        state = self.check_completeness(state)
        result = await self.generate_review_prompt_or_suggestion(
            state=state,
            db_session=db_session,
            refresh=False,
            reloaded=False,
        )
        await self._persist_waiting_state(
            state,
            waiting_for="user_message",
            current_node="wait_user_message",
            resume_from="apply_review_change",
        )
        return result

    async def _handle_modification_direct(
        self,
        *,
        job_id: str,
        modification_text: str,
        user_id: str,
        db_session,
    ) -> OpResult:
        state, error = await self.wait_user_message(
            job_id=job_id,
            db_session=db_session,
            allow_reacquire=True,
            allow_reload=True,
            missing_state_message="审核会话已过期，请重新启动审核",
        )
        if error is not None or state is None:
            return error or OpResult(status="error", message="审核状态缺失")
        state, result = await self.apply_review_change(
            state=state,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )
        if self._requires_confirmation(result):
            await self._persist_waiting_state(
                state,
                waiting_for="confirmation",
                current_node="confirm_and_resume",
                resume_from="confirm_and_resume",
            )
        else:
            await self._persist_waiting_state(
                state,
                waiting_for="user_message",
                current_node=None,
                resume_from="apply_review_change",
            )
        return result

    async def _confirm_changes_direct(self, *, job_id: str, user_id: str, db_session) -> OpResult:
        state, error = await self.wait_user_message(
            job_id=job_id,
            db_session=db_session,
            allow_reacquire=False,
            allow_reload=False,
            missing_state_message="未找到审核会话",
        )
        if error is not None or state is None:
            return error or OpResult(status="error", message="审核状态缺失")
        state, result = await self.confirm_and_resume(state=state, user_id=user_id, db_session=db_session)
        await self._persist_waiting_state(
            state,
            waiting_for="user_message",
            current_node=None,
            resume_from="apply_review_change",
        )
        return result

    async def _refresh_data_direct(self, *, job_id: str, db_session, current_state: ReviewState | None) -> OpResult:
        state = await self.load_review_data(
            job_id=job_id,
            db_session=db_session,
            previous_state=current_state,
            mark_reloaded=current_state is None,
        )
        state = self.check_completeness(state)
        state.refresh_count = (current_state.refresh_count if current_state else 0) + 1
        state.last_refreshed_at = now_shanghai().isoformat()
        result = await self.generate_review_prompt_or_suggestion(
            state=state,
            db_session=db_session,
            refresh=True,
            reloaded=current_state is None,
        )
        await self._persist_waiting_state(
            state,
            waiting_for="user_message",
            current_node="wait_user_message",
            resume_from="apply_review_change",
        )
        return result

    async def _run_langgraph_mode(
        self,
        *,
        job_id: str,
        db_session,
        input_payload: dict[str, Any] | None = None,
        resume_payload: dict[str, Any] | None = None,
    ) -> OpResult:
        graph = self.get_compiled_graph()
        if graph is None:
            return OpResult(status="error", message="LangGraph not available")
        config = self.checkpoint_config(job_id)
        self._runtime_contexts[job_id] = {"db_session": db_session}
        try:
            if resume_payload is not None and self.get_graph_state(job_id).interrupts:
                from langgraph.types import Command

                output = await graph.ainvoke(Command(resume=resume_payload), config)
            else:
                output = await graph.ainvoke(input_payload or {}, config)
        finally:
            self._runtime_contexts.pop(job_id, None)
        return self._extract_result_from_graph_output(job_id=job_id, output=output)

    def _extract_result_from_graph_output(self, *, job_id: str, output: Mapping[str, Any] | None) -> OpResult:
        payload = None if output is None else output.get("result")
        if payload is None:
            snapshot = self.get_graph_state(job_id)
            if snapshot is not None:
                payload = snapshot.values.get("result")
        if payload is None:
            return OpResult(status="error", message="审核流程未返回结果")
        return self._deserialize_op_result(payload)

    async def _langgraph_load_review_data(self, graph_state: dict[str, Any]) -> dict[str, Any]:
        mode = graph_state.get("mode")
        if mode not in {"start", "refresh"}:
            return self._merge_graph_state(graph_state, last_review_node="load_review_data")
        previous_state = self._state_from_payload(graph_state.get("job_id"), graph_state.get("previous_state"))
        state = await self.load_review_data(
            job_id=graph_state["job_id"],
            db_session=self._runtime_db_session(graph_state.get("job_id")),
            previous_state=previous_state,
            mark_reloaded=bool(graph_state.get("reloaded")),
        )
        if mode == "refresh":
            state.refresh_count = (previous_state.refresh_count if previous_state else 0) + 1
            state.last_refreshed_at = now_shanghai().isoformat()
        return self._merge_graph_state(
            graph_state,
            review_state=self.serialize_state(state),
            last_review_node="load_review_data",
        )

    async def _langgraph_check_completeness(self, graph_state: dict[str, Any]) -> dict[str, Any]:
        state = self._state_from_payload(graph_state.get("job_id"), graph_state.get("review_state"))
        if state is None:
            return self._merge_graph_state(graph_state, last_review_node="check_completeness")
        if graph_state.get("mode") in {"start", "refresh"}:
            state = self.check_completeness(state)
        return self._merge_graph_state(
            graph_state,
            review_state=self.serialize_state(state),
            last_review_node="check_completeness",
        )

    async def _langgraph_generate_review_prompt_or_suggestion(self, graph_state: dict[str, Any]) -> dict[str, Any]:
        state = self._state_from_payload(graph_state.get("job_id"), graph_state.get("review_state"))
        if state is None or graph_state.get("mode") not in {"start", "refresh"}:
            return self._merge_graph_state(graph_state, last_review_node="generate_review_prompt_or_suggestion")
        result = await self.generate_review_prompt_or_suggestion(
            state=state,
            db_session=self._runtime_db_session(graph_state.get("job_id")),
            refresh=bool(graph_state.get("refresh")),
            reloaded=bool(graph_state.get("reloaded")),
        )
        return self._merge_graph_state(
            graph_state,
            review_state=self.serialize_state(state),
            result=self._serialize_op_result(result),
            last_review_node="generate_review_prompt_or_suggestion",
        )

    async def _langgraph_wait_user_message(self, graph_state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.types import interrupt

        mode = graph_state.get("mode")
        state = self._state_from_payload(graph_state.get("job_id"), graph_state.get("review_state"))
        job_id = graph_state.get("job_id")
        if mode in {"start", "refresh"} and state is not None:
            await self._persist_waiting_state(
                state,
                waiting_for="user_message",
                current_node="wait_user_message",
                resume_from="apply_review_change",
            )
            # 中文注释：在 interrupt 前先把最新 waiting state 写回图状态，便于恢复测试直接观察快照。
            graph_state["review_state"] = self.serialize_state(state)
            graph_state["last_review_node"] = "wait_user_message"
            resume_value = interrupt({"kind": "review_wait_user_message", "job_id": job_id, "status": state.status})
            graph_state = self._merge_graph_state(
                graph_state,
                mode="modify",
                modification_text=(resume_value or {}).get("modification_text"),
                user_id=(resume_value or {}).get("user_id"),
                review_state=self.serialize_state(state),
                last_review_node="wait_user_message",
            )
        else:
            graph_state = self._merge_graph_state(graph_state, last_review_node="wait_user_message")
        if graph_state.get("mode") != "modify":
            return graph_state
        restored_state, error = await self.wait_user_message(
            job_id=job_id,
            db_session=self._runtime_db_session(job_id),
            allow_reacquire=True,
            allow_reload=True,
            missing_state_message="审核会话已过期，请重新启动审核",
        )
        if error is not None or restored_state is None:
            return self._merge_graph_state(
                graph_state,
                result=self._serialize_op_result(error or OpResult(status="error", message="审核状态缺失")),
            )
        return self._merge_graph_state(graph_state, review_state=self.serialize_state(restored_state))

    async def _langgraph_apply_review_change(self, graph_state: dict[str, Any]) -> dict[str, Any]:
        if graph_state.get("mode") != "modify" or not graph_state.get("modification_text"):
            return self._merge_graph_state(graph_state, last_review_node="apply_review_change")
        state = self._state_from_payload(graph_state.get("job_id"), graph_state.get("review_state"))
        if state is None:
            return self._merge_graph_state(
                graph_state,
                result=self._serialize_op_result(OpResult(status="error", message="未找到审核状态")),
                last_review_node="apply_review_change",
            )
        state, result = await self.apply_review_change(
            state=state,
            modification_text=graph_state["modification_text"],
            user_id=graph_state.get("user_id") or "",
            db_session=self._runtime_db_session(graph_state.get("job_id")),
        )
        return self._merge_graph_state(
            graph_state,
            review_state=self.serialize_state(state),
            result=self._serialize_op_result(result),
            last_review_node="apply_review_change",
        )

    async def _langgraph_confirm_and_resume(self, graph_state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.types import interrupt

        state = self._state_from_payload(graph_state.get("job_id"), graph_state.get("review_state"))
        result = self._deserialize_op_result(graph_state.get("result")) if graph_state.get("result") else None
        job_id = graph_state.get("job_id")
        if graph_state.get("mode") == "modify" and state is not None and result is not None and self._requires_confirmation(result):
            await self._persist_waiting_state(
                state,
                waiting_for="confirmation",
                current_node="confirm_and_resume",
                resume_from="confirm_and_resume",
            )
            # 中文注释：确认前暂停同样把 waiting snapshot 回写到图状态。
            graph_state["review_state"] = self.serialize_state(state)
            graph_state["last_review_node"] = "confirm_and_resume"
            resume_value = interrupt(
                {"kind": "review_confirm_and_resume", "job_id": job_id, "pending_modifications": len(state.modifications)}
            )
            graph_state = self._merge_graph_state(
                graph_state,
                mode="confirm",
                user_id=(resume_value or {}).get("user_id"),
                review_state=self.serialize_state(state),
                last_review_node="confirm_and_resume",
            )
        elif graph_state.get("mode") == "modify" and state is not None:
            await self._persist_waiting_state(
                state,
                waiting_for="user_message",
                current_node=None,
                resume_from="apply_review_change",
            )
            return self._merge_graph_state(
                graph_state,
                review_state=self.serialize_state(state),
                last_review_node="confirm_and_resume",
            )
        else:
            graph_state = self._merge_graph_state(graph_state, last_review_node="confirm_and_resume")
        if graph_state.get("mode") != "confirm":
            return graph_state
        if state is None:
            state, error = await self.wait_user_message(
                job_id=job_id,
                db_session=self._runtime_db_session(job_id),
                allow_reacquire=False,
                allow_reload=False,
                missing_state_message="未找到审核会话",
            )
            if error is not None or state is None:
                return self._merge_graph_state(
                    graph_state,
                    result=self._serialize_op_result(error or OpResult(status="error", message="未找到审核会话")),
                )
        state, confirm_result = await self.confirm_and_resume(
            state=state,
            user_id=graph_state.get("user_id") or "",
            db_session=self._runtime_db_session(job_id),
        )
        await self._persist_waiting_state(
            state,
            waiting_for="user_message",
            current_node=None,
            resume_from="apply_review_change",
        )
        return self._merge_graph_state(
            graph_state,
            review_state=self.serialize_state(state),
            result=self._serialize_op_result(confirm_result),
        )

    async def _persist_waiting_state(
        self,
        state: ReviewState,
        *,
        waiting_for: str | None,
        current_node: str | None,
        resume_from: str | None,
    ) -> None:
        # 中文注释：把 LangGraph 的暂停点同步回 ReviewState，保证查询接口和路由都能看到一致状态。
        state.waiting_for = waiting_for
        state.current_node = current_node
        state.resume_from = resume_from
        state.checkpoint_id = current_node
        if waiting_for == "confirmation":
            state.status = "awaiting_confirmation"
        elif state.completeness.get("is_complete", True):
            state.status = "reviewing"
        else:
            state.status = "pending_completion"
        await self._get_state_store().save(state)
        self._persist_durable_checkpoint(state)

    def _build_durable_checkpoint(self, state: ReviewState) -> dict[str, Any]:
        checkpoint_id = state.checkpoint_id or state.current_node or "review_state"
        return {
            "thread_id": state.job_id,
            "checkpoint_id": checkpoint_id,
            "config": self.checkpoint_config(state.job_id, checkpoint_id=checkpoint_id),
            "status": state.status,
            "waiting_for": state.waiting_for,
            "resume_from": state.resume_from,
        }

    def _persist_durable_checkpoint(self, state: ReviewState) -> None:
        checkpoint = self._build_durable_checkpoint(state)
        target = self._durable_store.save(
            job_id=state.job_id,
            state=self.serialize_state(state),
            checkpoint=checkpoint,
        )
        state.extra["durable_checkpoint"] = {
            "backend": "review_file_checkpoint_store",
            "path": str(target),
            "thread_id": state.job_id,
        }

    def _load_durable_state(self, job_id: str) -> ReviewState | None:
        snapshot = self._durable_store.load(job_id)
        if snapshot is None:
            return None
        payload = snapshot.get("state")
        if not isinstance(payload, dict):
            return None
        state = ReviewState.from_payload(job_id=job_id, payload=payload)
        if not isinstance(state.extra, dict):
            state.extra = {}
        state.extra.setdefault(
            "durable_checkpoint",
            {
                "backend": "review_file_checkpoint_store",
                "thread_id": job_id,
            },
        )
        return state

    def _runtime_db_session(self, job_id: str | None):
        if job_id is None:
            return None
        return self._runtime_contexts.get(job_id, {}).get("db_session")

    def _state_from_payload(self, job_id: str | None, payload: Any) -> ReviewState | None:
        if job_id is None or payload is None:
            return None
        if isinstance(payload, ReviewState):
            return payload
        if isinstance(payload, dict):
            return ReviewState.from_payload(job_id=job_id, payload=payload)
        return None

    @staticmethod
    def _serialize_op_result(result: OpResult) -> dict[str, Any]:
        return {"status": result.status, "message": result.message, "data": result.data}

    @staticmethod
    def _deserialize_op_result(payload: Any) -> OpResult:
        if isinstance(payload, OpResult):
            return payload
        if isinstance(payload, dict):
            return OpResult(
                status=payload.get("status", "error"),
                message=payload.get("message", ""),
                data=payload.get("data"),
            )
        return OpResult(status="error", message="审核流程结果格式错误")

    @staticmethod
    def _requires_confirmation(result: OpResult) -> bool:
        return bool((result.data or {}).get("requires_confirmation"))

    @staticmethod
    def _merge_graph_state(graph_state: dict[str, Any], **updates: Any) -> dict[str, Any]:
        merged = dict(graph_state)
        merged.update({key: value for key, value in updates.items() if value is not None})
        return merged


review_graph = ReviewGraph()
