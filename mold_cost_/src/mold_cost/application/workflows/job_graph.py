"""Main job workflow facade backed by a real LangGraph runtime."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any
import uuid

from ...core.logging import get_logger
from .job_state import JobAction, JobState

logger = get_logger(__name__)


class JobGraph:
    """Workflow facade for start/continue job execution."""

    # 中文注释：保留业务上的逻辑命名空间，便于外部 envelope 识别 job workflow。
    CHECKPOINT_NAMESPACE = "job_workflow"
    # 中文注释：LangGraph 顶层线程恢复依赖 thread_id，根图的 checkpoint_ns 保持为空字符串。
    RUNTIME_CHECKPOINT_NAMESPACE = ""
    START_FLOW = (
        "load_context",
        "validate_start",
        "execute_start",
        "collect_post_run",
        "finalize",
    )
    CONTINUE_FLOW = (
        "load_context",
        "validate_continue",
        "execute_continue",
        "collect_post_run",
        "finalize",
    )
    STOP_AND_FINALIZE_STATUSES = {"failed", "ignored"}

    def __init__(self, *, orchestrator=None, checkpointer=None):
        self._compiled_graph = None
        self._orchestrator = orchestrator
        self._checkpointer = checkpointer if checkpointer is not None else self._build_default_checkpointer()

    def invoke(self, state: JobState) -> JobState:
        """Compatibility hook for older sync callers."""
        return state

    async def run(self, job_id: str, action: JobAction = "start") -> dict[str, Any]:
        """Run the workflow and return a legacy-compatible result payload."""
        state = await self.run_with_state(job_id=job_id, action=action)
        return self._result_from_state(state)

    async def run_with_state(self, job_id: str, action: JobAction = "start") -> JobState:
        """Run the workflow and return the final state object."""
        graph = self.get_compiled_graph()
        state = await self._prepare_input_state(job_id=job_id, action=action)

        if graph is None:
            return await self._run_flow_legacy(state)

        config = self.checkpoint_config(job_id=job_id)
        payload = await graph.ainvoke(self._to_runtime_payload(state), config=config)
        final_state = self.deserialize_state(payload if isinstance(payload, dict) else {})
        snapshot = await self.get_checkpoint_snapshot(job_id=job_id)
        return self._attach_runtime_checkpoint(final_state, snapshot)

    async def start_job(self, job_id: str) -> dict[str, Any]:
        logger.info("Starting job via JobGraph: job_id=%s", job_id)
        return await self.run(job_id=job_id, action="start")

    async def continue_job(self, job_id: str) -> dict[str, Any]:
        logger.info("Continuing job via JobGraph: job_id=%s", job_id)
        return await self.run(job_id=job_id, action="continue")

    async def handle_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Unified worker entry for job queue messages."""
        job_id = message.get("job_id")
        if not job_id:
            return {
                "status": "error",
                "message": "message missing job_id",
                "error_code": "MISSING_JOB_ID",
            }

        action = self._normalize_action(message.get("action"))
        if action is None:
            return {
                "status": "error",
                "message": f"unsupported job action: {message.get('action')}",
                "error_code": "UNSUPPORTED_ACTION",
            }

        return await self.run(job_id=job_id, action=action)

    def to_state(self, job_id: str, **kwargs: Any) -> JobState:
        """Construct a workflow state object with stable field names."""
        if "dwg_file_path" in kwargs and "dwg_path" not in kwargs:
            kwargs["dwg_path"] = kwargs.pop("dwg_file_path")
        if "prt_file_path" in kwargs and "prt_path" not in kwargs:
            kwargs["prt_path"] = kwargs.pop("prt_file_path")
        kwargs.setdefault("checkpoint_ns", self.CHECKPOINT_NAMESPACE)
        kwargs.setdefault("thread_id", job_id)
        return JobState(job_id=job_id, **kwargs)

    def serialize_state(self, state: JobState) -> dict[str, Any]:
        """Serialize workflow state for checkpointing."""
        data = asdict(state)
        artifacts = data.get("artifacts") or {}
        artifacts.pop("checkpoint", None)
        return data

    def deserialize_state(self, payload: dict[str, Any]) -> JobState:
        """Restore workflow state from a serialized payload."""
        return self.to_state(**payload)

    def checkpoint_config(
        self,
        job_id: str,
        checkpoint_id: str | None = None,
        checkpoint_ns: str | None = None,
    ) -> dict[str, Any]:
        """Build a real LangGraph runtime config envelope."""
        configurable = {"thread_id": job_id}
        if checkpoint_ns is not None:
            configurable["checkpoint_ns"] = checkpoint_ns
        if checkpoint_id:
            configurable["checkpoint_id"] = checkpoint_id
        return {"configurable": configurable}

    def build_checkpoint(
        self,
        state: JobState,
        runtime_config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        next_nodes: tuple[str, ...] | list[str] | None = None,
    ) -> dict[str, Any]:
        """Build checkpoint metadata using the real runtime config whenever available."""
        checkpoint_id = state.checkpoint_id or state.current_step
        config = runtime_config or self.checkpoint_config(
            state.job_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=state.checkpoint_ns,
        )
        normalized_config = self._normalize_checkpoint_config(config, state.job_id)
        configurable = normalized_config["configurable"]
        runtime_checkpoint_id = configurable.get("checkpoint_id") or checkpoint_id
        runtime_checkpoint_ns = configurable.get("checkpoint_ns")
        return {
            "checkpoint_id": runtime_checkpoint_id,
            "resume_from": state.resume_from,
            "thread_id": configurable["thread_id"],
            "checkpoint_ns": runtime_checkpoint_ns,
            "config": normalized_config,
            "metadata": metadata or {},
            "next_nodes": list(next_nodes or []),
            "state": self.serialize_state(state),
        }

    async def get_checkpoint_snapshot(
        self,
        job_id: str,
        checkpoint_id: str | None = None,
    ):
        """Read the latest workflow checkpoint for the given job thread."""
        graph = self.get_compiled_graph()
        if graph is None:
            return None

        config = self.checkpoint_config(
            job_id=job_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=self.RUNTIME_CHECKPOINT_NAMESPACE,
        )
        try:
            return await graph.aget_state(config)
        except Exception:
            logger.debug("Unable to inspect checkpoint state: job_id=%s", job_id, exc_info=True)
            return None

    def get_compiled_graph(self):
        """Compile the real LangGraph once and reuse it."""
        if self._compiled_graph is not None:
            return self._compiled_graph

        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            logger.info("LangGraph is not available; workflow facade stays in local mode")
            return None

        # 中文注释：图内部使用 dict 状态，避免 LangGraph 保留 channel 名与公开 JobState 字段冲突。
        graph = StateGraph(dict)
        graph.add_node("load_context", self._node_load_context)
        graph.add_node("validate_start", self._node_validate_start)
        graph.add_node("validate_continue", self._node_validate_continue)
        graph.add_node("execute_start", self._node_execute_start)
        graph.add_node("execute_continue", self._node_execute_continue)
        graph.add_node("collect_post_run", self._node_collect_post_run)
        graph.add_node("finalize", self._node_finalize)
        graph.add_edge(START, "load_context")
        graph.add_conditional_edges("load_context", self._route_validation_node)
        graph.add_conditional_edges("validate_start", self._route_after_validate_start)
        graph.add_conditional_edges("validate_continue", self._route_after_validate_continue)
        graph.add_conditional_edges("execute_start", self._route_after_execute_start)
        graph.add_conditional_edges("execute_continue", self._route_after_execute_continue)
        graph.add_edge("collect_post_run", "finalize")
        graph.add_edge("finalize", END)

        self._compiled_graph = graph.compile(checkpointer=self._checkpointer, name=self.CHECKPOINT_NAMESPACE)
        return self._compiled_graph

    async def _prepare_input_state(self, job_id: str, action: JobAction) -> JobState:
        state = self.to_state(job_id=job_id, action=action)
        if action != "continue":
            return state

        snapshot = await self.get_checkpoint_snapshot(job_id=job_id)
        if snapshot is None or not snapshot.values:
            return state

        # 中文注释：continue 只在 workflow 层恢复同一 thread 的最近 checkpoint，
        # worker 和 use case 仍只需要传 job_id，不感知 LangGraph 细节。
        resumed_state = self.deserialize_state(snapshot.values)
        resumed_state.action = action
        resumed_state.job_id = job_id
        resumed_state.thread_id = job_id
        resumed_state.current_step = "bootstrap"
        resumed_state.status = "created"
        resumed_state.errors = list(resumed_state.errors)
        resumed_state.subgraph_ids = list(resumed_state.subgraph_ids)
        resumed_state.feature_summary = dict(resumed_state.feature_summary)
        resumed_state.pricing_summary = dict(resumed_state.pricing_summary)
        resumed_state.artifacts = dict(resumed_state.artifacts)
        resumed_state.artifacts["resume_checkpoint"] = self._normalize_checkpoint_config(snapshot.config, job_id)
        resumed_state.artifacts["resumed_from_thread"] = job_id
        resumed_state.resume_from = resumed_state.resume_from or "execute_continue"
        return resumed_state

    async def _run_flow_legacy(self, state: JobState) -> JobState:
        state.status = "running"
        steps = self.START_FLOW if state.action == "start" else self.CONTINUE_FLOW

        for step_name in steps:
            # 中文注释：LangGraph 不可用时仍保留旧的显式步骤推进，保证兼容迁移不断链。
            state.current_step = step_name
            state.checkpoint_id = step_name
            handler = getattr(self, f"_step_{step_name}")
            state = await handler(state)
            state.artifacts["checkpoint"] = self.build_checkpoint(state)
            if step_name != "finalize" and state.status in self.STOP_AND_FINALIZE_STATUSES:
                state.current_step = "finalize"
                state.checkpoint_id = "finalize"
                state = await self._step_finalize(state)
                state.artifacts["checkpoint"] = self.build_checkpoint(state)
                break

        return state

    async def _node_load_context(self, state: dict[str, Any]) -> dict[str, Any]:
        return await self._run_node("load_context", state, self._step_load_context)

    async def _node_validate_start(self, state: dict[str, Any]) -> dict[str, Any]:
        return await self._run_node("validate_start", state, self._step_validate_start)

    async def _node_validate_continue(self, state: dict[str, Any]) -> dict[str, Any]:
        return await self._run_node("validate_continue", state, self._step_validate_continue)

    async def _node_execute_start(self, state: dict[str, Any]) -> dict[str, Any]:
        return await self._run_node("execute_start", state, self._step_execute_start)

    async def _node_execute_continue(self, state: dict[str, Any]) -> dict[str, Any]:
        return await self._run_node("execute_continue", state, self._step_execute_continue)

    async def _node_collect_post_run(self, state: dict[str, Any]) -> dict[str, Any]:
        return await self._run_node("collect_post_run", state, self._step_collect_post_run)

    async def _node_finalize(self, state: dict[str, Any]) -> dict[str, Any]:
        return await self._run_node("finalize", state, self._step_finalize)

    async def _run_node(self, step_name: str, state: dict[str, Any], handler) -> dict[str, Any]:
        working_state = self._coerce_state(state)
        working_state.current_step = step_name
        working_state.thread_id = working_state.job_id
        if working_state.status in {"created", "paused"}:
            working_state.status = "running"
        working_state = await handler(working_state)
        return self._to_runtime_payload(working_state)

    def _route_validation_node(self, state: dict[str, Any]) -> str:
        return "validate_continue" if self._coerce_state(state).action == "continue" else "validate_start"

    def _route_after_validate_start(self, state: dict[str, Any]) -> str:
        return self._route_next_or_finalize(state, next_node="execute_start")

    def _route_after_validate_continue(self, state: dict[str, Any]) -> str:
        return self._route_next_or_finalize(state, next_node="execute_continue")

    def _route_after_execute_start(self, state: dict[str, Any]) -> str:
        return self._route_next_or_finalize(state, next_node="collect_post_run")

    def _route_after_execute_continue(self, state: dict[str, Any]) -> str:
        return self._route_next_or_finalize(state, next_node="collect_post_run")

    def _route_next_or_finalize(self, state: dict[str, Any], *, next_node: str) -> str:
        runtime_state = self._coerce_state(state)
        return "finalize" if runtime_state.status in self.STOP_AND_FINALIZE_STATUSES else next_node

    async def _step_load_context(self, state: JobState) -> JobState:
        # 中文注释：这里集中补齐 workflow 需要的上下文，避免 worker 再做 DB 查询和字段拼装。
        job = await self._load_job_record(state.job_id)
        if job is None:
            state.artifacts["context_available"] = False
            return state

        state.artifacts["context_available"] = True
        state.user_id = self._stringify(getattr(job, "user_id", None))
        state.dwg_path = getattr(job, "dwg_file_path", None)
        state.prt_path = getattr(job, "prt_file_path", None)
        state.subgraph_ids = await self._load_subgraph_ids(state.job_id)
        state.review_status = self._derive_review_status(getattr(job, "status", None))
        state.artifacts["job"] = self._snapshot_job(job)
        if state.action == "continue" and state.subgraph_ids:
            state.artifacts["resume_hint"] = {"subgraph_count": len(state.subgraph_ids)}
        return state

    async def _step_validate_start(self, state: JobState) -> JobState:
        if not state.artifacts.get("context_available"):
            return state

        job_status = state.artifacts.get("job", {}).get("status")
        if not state.dwg_path:
            # 中文注释：start 阶段缺少 DWG 属于硬失败，在这里截断，
            # 不再让底层 orchestrator 承担入口数据校验职责。
            await self._mark_job_failed(state.job_id, "missing_dwg_file_path")
            return self._fail_state(
                state,
                message="job missing dwg_file_path",
                error_code="MISSING_DWG_FILE_PATH",
            )

        if job_status == "processing":
            return self._ignore_state(state, "job is already processing")

        if job_status in {"completed", "awaiting_confirm"}:
            return self._ignore_state(state, f"job is already in terminal gate: {job_status}")

        return state

    async def _step_validate_continue(self, state: JobState) -> JobState:
        if not state.artifacts.get("context_available"):
            return state

        job_status = state.artifacts.get("job", {}).get("status")
        if job_status != "awaiting_confirm":
            return self._fail_state(
                state,
                message=f"job is not awaiting confirmation: {job_status}",
                error_code="INVALID_STATUS",
            )

        state.review_status = "awaiting_confirm"
        # 中文注释：resume_from 继续保留轻量字段，便于旧 envelope 和新 runtime 并行兼容。
        state.resume_from = "execute_continue"
        return state

    async def _step_execute_start(self, state: JobState) -> JobState:
        result = await self._get_orchestrator().start(state.job_id)
        return self._apply_execution_result(state, result)

    async def _step_execute_continue(self, state: JobState) -> JobState:
        result = await self._get_orchestrator().continue_job(state.job_id)
        return self._apply_execution_result(state, result)

    async def _step_collect_post_run(self, state: JobState) -> JobState:
        # 中文注释：执行完成后统一回收 DB 中的最新状态，
        # 让 start / continue 都通过同一处补齐 summary / review_status。
        refreshed_job = await self._load_job_record(state.job_id)
        if refreshed_job is not None:
            state.artifacts["job"] = self._snapshot_job(refreshed_job)
            state.dwg_path = getattr(refreshed_job, "dwg_file_path", None)
            state.prt_path = getattr(refreshed_job, "prt_file_path", None)
            state.review_status = self._derive_review_status(getattr(refreshed_job, "status", None))
            state.subgraph_ids = await self._load_subgraph_ids(state.job_id)

        if state.action == "start":
            state.feature_summary.setdefault("subgraph_count", len(state.subgraph_ids))
            if state.review_status == "awaiting_confirm":
                state.resume_from = "execute_continue"
        else:
            job_snapshot = state.artifacts.get("job", {})
            if job_snapshot.get("total_cost") is not None:
                state.pricing_summary.setdefault("total_cost", job_snapshot.get("total_cost"))
                state.pricing_summary.setdefault("currency", job_snapshot.get("currency"))
            state.pricing_summary.setdefault("subgraph_count", len(state.subgraph_ids))
            if state.status != "failed":
                state.resume_from = None

        return state

    async def _step_finalize(self, state: JobState) -> JobState:
        if state.status == "running":
            state.status = "completed"

        if state.status == "completed":
            state.current_step = "completed"
        elif state.status == "failed":
            state.current_step = "failed"

        return state

    def _apply_execution_result(self, state: JobState, result: dict[str, Any]) -> JobState:
        state.artifacts["result"] = result
        state.artifacts["result_summary"] = self._normalize_value(result)

        if result.get("status") == "error":
            return self._fail_state(
                state,
                message=result.get("message", "workflow execution failed"),
                error_code=result.get("error_code"),
            )

        summary = result.get("summary") or {}
        if state.action == "start":
            state.feature_summary = self._coerce_summary(summary)
            if result.get("action_required") == "user_confirmation":
                # 中文注释：start 跑到这里说明业务已进入人工确认闸口，
                # workflow 用 interrupted 表达“流程暂停但不是失败”。
                state.review_status = "awaiting_confirm"
                state.resume_from = "execute_continue"
                state.status = "interrupted"
            else:
                state.status = "completed"
        else:
            state.pricing_summary = self._coerce_summary(summary)
            state.review_status = "completed"
            state.resume_from = None
            state.status = "completed"

        return state

    def _attach_runtime_checkpoint(self, state: JobState, snapshot) -> JobState:
        if snapshot is None:
            state.artifacts["checkpoint"] = self.build_checkpoint(state)
            return state

        runtime_config = self._normalize_checkpoint_config(snapshot.config, state.job_id)
        configurable = runtime_config["configurable"]
        state.thread_id = configurable["thread_id"]
        state.checkpoint_ns = configurable.get("checkpoint_ns", state.checkpoint_ns)
        state.checkpoint_id = configurable.get("checkpoint_id")
        state.artifacts["checkpoint"] = self.build_checkpoint(
            state,
            runtime_config=runtime_config,
            metadata=self._normalize_value(snapshot.metadata),
            next_nodes=tuple(snapshot.next or ()),
        )
        return state

    def _result_from_state(self, state: JobState) -> dict[str, Any]:
        result = state.artifacts.get("result")
        if isinstance(result, dict):
            return result

        if state.status == "ignored":
            return {
                "status": "ignored",
                "message": state.errors[-1] if state.errors else "job skipped",
                "job_id": state.job_id,
            }

        error_code = state.artifacts.get("error_code")
        if state.status == "failed":
            payload = {
                "status": "error",
                "message": state.errors[-1] if state.errors else "job workflow failed",
                "job_id": state.job_id,
            }
            if error_code:
                payload["error_code"] = error_code
            return payload

        return {"status": state.status, "job_id": state.job_id}

    async def _load_job_record(self, job_id: str):
        if not self._looks_like_uuid(job_id):
            return None

        try:
            from shared.database import get_db
            from shared.models import Job
            from sqlalchemy import select
        except Exception:
            logger.debug("Job context imports unavailable during workflow bootstrap")
            return None

        job_uuid = uuid.UUID(job_id)
        async for db in get_db():
            result = await db.execute(select(Job).where(Job.job_id == job_uuid))
            return result.scalar_one_or_none()
        return None

    async def _load_subgraph_ids(self, job_id: str) -> list[str]:
        if not self._looks_like_uuid(job_id):
            return []

        try:
            from shared.database import get_db
            from shared.models import Subgraph
            from sqlalchemy import select
        except Exception:
            logger.debug("Subgraph context imports unavailable during workflow bootstrap")
            return []

        job_uuid = uuid.UUID(job_id)
        async for db in get_db():
            result = await db.execute(select(Subgraph.subgraph_id).where(Subgraph.job_id == job_uuid))
            return [row[0] for row in result.fetchall()]
        return []

    async def _mark_job_failed(self, job_id: str, reason: str) -> None:
        if not self._looks_like_uuid(job_id):
            return

        try:
            from shared.database import get_db
            from shared.models import Job
            from sqlalchemy import update
        except Exception:
            logger.warning("Unable to import DB dependencies for failure update")
            return

        job_uuid = uuid.UUID(job_id)
        async for db in get_db():
            # 中文注释：这里只做最小失败回写，避免把完整编排逻辑重新塞回 worker。
            await db.execute(
                update(Job)
                .where(Job.job_id == job_uuid)
                .values(
                    status="failed",
                    error_message=reason,
                    updated_at=datetime.utcnow(),
                )
            )
            await db.commit()
            break

        try:
            from shared.progress_publisher import ProgressPublisher
            from shared.progress_stages import ProgressStage

            ProgressPublisher().publish_progress(
                job_id=job_id,
                stage=ProgressStage.FAILED,
                progress=0,
                message=f"task failed before orchestration: {reason}",
                details={"source": "job_graph", "error": reason},
            )
        except Exception:
            logger.warning("Unable to publish failure progress for job_id=%s", job_id, exc_info=True)

    def _fail_state(self, state: JobState, message: str, error_code: str | None = None) -> JobState:
        if not state.errors or state.errors[-1] != message:
            state.errors.append(message)
        state.status = "failed"
        state.artifacts["error_code"] = error_code
        return state

    def _ignore_state(self, state: JobState, message: str) -> JobState:
        state.errors.append(message)
        state.status = "ignored"
        return state

    def _snapshot_job(self, job: Any) -> dict[str, Any]:
        return {
            "job_id": self._stringify(getattr(job, "job_id", None)),
            "user_id": self._stringify(getattr(job, "user_id", None)),
            "status": getattr(job, "status", None),
            "current_stage": getattr(job, "current_stage", None),
            "progress": getattr(job, "progress", None),
            "dwg_path": getattr(job, "dwg_file_path", None),
            "prt_path": getattr(job, "prt_file_path", None),
            "total_cost": self._normalize_value(getattr(job, "total_cost", None)),
            "currency": getattr(job, "currency", None),
        }

    def _derive_review_status(self, job_status: str | None) -> str | None:
        if job_status == "awaiting_confirm":
            return "awaiting_confirm"
        if job_status == "completed":
            return "completed"
        if job_status == "failed":
            return "failed"
        return job_status

    def _coerce_summary(self, summary: Any) -> dict[str, Any]:
        if isinstance(summary, dict):
            return self._normalize_value(summary)
        if summary is None:
            return {}
        return {"value": self._normalize_value(summary)}

    def _normalize_action(self, action: Any) -> JobAction | None:
        if action in (None, "", "start"):
            return "start"
        if action in {"continue", "continue_job"}:
            return "continue"
        return None

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._normalize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def _looks_like_uuid(self, value: str) -> bool:
        try:
            uuid.UUID(value)
        except (TypeError, ValueError, AttributeError):
            return False
        return True

    def _stringify(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    def _coerce_state(self, state: JobState | dict[str, Any]) -> JobState:
        if isinstance(state, JobState):
            return state
        return self.deserialize_state(state)

    def _to_runtime_payload(self, state: JobState) -> dict[str, Any]:
        payload = self.serialize_state(state)
        # 中文注释：checkpoint_* / thread_id 属于运行时配置，不放进图状态，
        # 避免和 LangGraph 的保留字段发生冲突。
        payload.pop("checkpoint_ns", None)
        payload.pop("checkpoint_id", None)
        payload.pop("thread_id", None)
        return payload

    def _normalize_checkpoint_config(self, config: dict[str, Any] | None, job_id: str) -> dict[str, Any]:
        configurable = dict((config or {}).get("configurable") or {})
        configurable.setdefault("thread_id", job_id)
        return {"configurable": configurable}

    @staticmethod
    def _build_default_checkpointer():
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except Exception:
            logger.info("LangGraph checkpoint saver is not available; workflow will use local fallback")
            return None
        return MemorySaver()

    def _get_orchestrator(self):
        if self._orchestrator is not None:
            return self._orchestrator

        from agents import get_orchestrator_agent

        return get_orchestrator_agent()


job_graph = JobGraph()
