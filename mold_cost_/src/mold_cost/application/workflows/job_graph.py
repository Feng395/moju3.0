"""Main job workflow facade with explicit state progression."""

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

    # 中文注释：先显式声明步骤顺序，保持 facade 形态不变，
    # 后续再把这些步骤平移到真实 LangGraph 节点实现。
    CHECKPOINT_NAMESPACE = "job_workflow"
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

    def __init__(self):
        self._compiled_graph = None

    def invoke(self, state: JobState) -> JobState:
        """Compatibility stub for future LangGraph state invocation."""
        return state

    async def run(self, job_id: str, action: JobAction = "start") -> dict[str, Any]:
        """Run the workflow and return a legacy-compatible result payload."""
        state = await self.run_with_state(job_id=job_id, action=action)
        return self._result_from_state(state)

    async def run_with_state(self, job_id: str, action: JobAction = "start") -> JobState:
        """Run the workflow and return the final state object."""
        state = self.to_state(job_id=job_id, action=action)
        return await self._run_flow(state)

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

    def checkpoint_config(self, job_id: str, checkpoint_id: str | None = None) -> dict[str, Any]:
        """Build a LangGraph-style checkpoint config envelope."""
        configurable = {
            "thread_id": job_id,
            "checkpoint_ns": self.CHECKPOINT_NAMESPACE,
        }
        if checkpoint_id:
            configurable["checkpoint_id"] = checkpoint_id
        return {"configurable": configurable}

    def build_checkpoint(self, state: JobState) -> dict[str, Any]:
        """Build checkpoint metadata without depending on LangGraph runtime."""
        checkpoint_id = state.checkpoint_id or state.current_step
        return {
            "checkpoint_id": checkpoint_id,
            "resume_from": state.resume_from,
            "config": self.checkpoint_config(state.job_id, checkpoint_id),
            "state": self.serialize_state(state),
        }

    def get_compiled_graph(self):
        """Build a minimal explicit LangGraph layout when available."""
        if self._compiled_graph is not None:
            return self._compiled_graph

        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            logger.info("LangGraph is not available; workflow facade stays in local mode")
            return None

        graph = StateGraph(dict)
        graph.add_node("load_context", lambda state: state)
        graph.add_node("validate_start", lambda state: state)
        graph.add_node("validate_continue", lambda state: state)
        graph.add_node("execute_start", lambda state: state)
        graph.add_node("execute_continue", lambda state: state)
        graph.add_node("collect_post_run", lambda state: state)
        graph.add_node("finalize", lambda state: state)
        graph.add_edge(START, "load_context")
        graph.add_conditional_edges(
            "load_context",
            lambda state: "validate_continue" if state.get("action") == "continue" else "validate_start",
        )
        graph.add_edge("validate_start", "execute_start")
        graph.add_edge("validate_continue", "execute_continue")
        graph.add_edge("execute_start", "collect_post_run")
        graph.add_edge("execute_continue", "collect_post_run")
        graph.add_edge("collect_post_run", "finalize")
        graph.add_edge("finalize", END)
        self._compiled_graph = graph.compile()
        return self._compiled_graph

    async def _run_flow(self, state: JobState) -> JobState:
        state.status = "running"
        steps = self.START_FLOW if state.action == "start" else self.CONTINUE_FLOW

        for step_name in steps:
            # 中文注释：每一步都写回 checkpoint 元数据，
            # 这样后续接入 interrupt/resume 时可以直接复用当前状态对象。
            state.current_step = step_name
            state.checkpoint_id = step_name
            handler = getattr(self, f"_step_{step_name}")
            state = await handler(state)
            state.artifacts["checkpoint"] = self.build_checkpoint(state)
            if step_name != "finalize" and state.status in {"failed", "ignored"}:
                state.current_step = "finalize"
                state.checkpoint_id = "finalize"
                state = await self._step_finalize(state)
                state.artifacts["checkpoint"] = self.build_checkpoint(state)
                break

        return state

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
            # 中文注释：start 阶段缺少 DWG 属于硬失败，直接在这里截断，
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
        # 中文注释：resume_from 先用轻量字符串表达恢复点，
        # 后续如果接 LangGraph checkpoint，可直接映射到节点名。
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
            state.checkpoint_id = "completed"
        elif state.status == "failed":
            state.current_step = "failed"
            state.checkpoint_id = "failed"
        else:
            state.checkpoint_id = state.current_step

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
                # 中文注释：start 跑到这里说明业务上已进入人工确认门，
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
        if action == "continue":
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

    @staticmethod
    def _get_orchestrator():
        from agents import get_orchestrator_agent

        return get_orchestrator_agent()


job_graph = JobGraph()
