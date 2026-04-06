"""重构后主骨架的离线冒烟验证。"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_refactor_entrypoints_can_import():
    """验证新旧入口在不连接外部服务时可以完成导入。"""
    from api_gateway.repositories.chat_history_repository import ChatHistoryRepository as LegacyChatHistoryRepository
    from api_gateway.routers import chat_router, features, jobs, review_router
    from api_gateway.services.file_service import FileService
    from api_gateway.services.job_service import JobService
    from mold_cost.application.use_cases.get_job_status import GetJobStatusUseCase
    from mold_cost.application.use_cases.handle_review_message import ReviewChatUseCase
    from mold_cost.application.use_cases.start_review import StartReviewUseCase
    from mold_cost.application.workflows.job_graph import job_graph
    from mold_cost.application.workflows.review_graph import review_graph
    from mold_cost.domain.jobs import JobSummary
    from mold_cost.domain.pricing.calculators import price_total
    from mold_cost.domain.pricing.search import total_search
    from mold_cost.infrastructure.db.repositories.chat_history_repository import (
        ChatHistoryRepository as SrcChatHistoryRepository,
    )
    from mold_cost.infrastructure.mcp import tool_gateway
    from mold_cost.interfaces.api import get_legacy_cad_app
    from mold_cost.interfaces.api.routers.jobs import get_jobs_router, get_legacy_jobs_router
    from mold_cost.interfaces.mcp import get_server_module
    from scripts import check_services as legacy_check_services
    from scripts import unified_api as legacy_unified_api
    from scripts import verify_integration as legacy_verify_integration
    from tools.diagnostics import check_services as tools_check_services
    from tools.diagnostics import verify_integration as tools_verify_integration

    # 中文注释：这里按文件直接加载 cad_chaitu 兼容壳，避免触发旧包的重型初始化链。
    cad_unified_api_path = Path(__file__).resolve().parents[2] / "scripts" / "cad_chaitu" / "unified_api.py"
    spec = importlib.util.spec_from_file_location("cad_legacy_unified_api_test", cad_unified_api_path)
    cad_legacy_unified_api = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(cad_legacy_unified_api)

    # 中文注释：这里只校验装配成功，不触发真实外部调用。
    assert jobs.router is not None
    assert features.router is not None
    assert review_router.router is not None
    assert chat_router.router is not None
    assert issubclass(LegacyChatHistoryRepository, SrcChatHistoryRepository)
    assert isinstance(JobService(), JobService)
    assert isinstance(FileService(), FileService)
    assert isinstance(GetJobStatusUseCase(), GetJobStatusUseCase)
    assert isinstance(StartReviewUseCase(), StartReviewUseCase)
    assert isinstance(ReviewChatUseCase(), ReviewChatUseCase)
    assert job_graph is not None
    assert review_graph is not None
    assert not hasattr(type(review_graph), "_get_agent")
    assert review_graph._get_chat_executor().__class__.__name__ == "WorkflowReviewChatExecutor"
    assert JobSummary(job_id="job-1", status="pending").job_id == "job-1"
    assert price_total is not None
    assert total_search is not None
    assert tool_gateway is not None
    assert get_legacy_cad_app() is not None
    assert callable(get_jobs_router)
    assert callable(get_legacy_jobs_router)
    assert callable(get_server_module)
    assert tools_check_services.main is not None
    assert tools_verify_integration.main is not None
    assert legacy_check_services.main is not None
    assert legacy_unified_api.app is not None
    assert legacy_verify_integration.main is not None
    assert cad_legacy_unified_api.app is not None


def test_job_graph_can_delegate_to_stubbed_orchestrator(monkeypatch):
    """验证任务工作流外壳能正常委派给编排器。"""
    from mold_cost.application.workflows.job_graph import JobGraph

    class StubOrchestrator:
        async def start(self, job_id: str):
            return {"status": "started", "job_id": job_id}

        async def continue_job(self, job_id: str):
            return {"status": "continued", "job_id": job_id}

    graph = JobGraph()
    monkeypatch.setattr(graph, "_get_orchestrator", lambda: StubOrchestrator())

    start_result = asyncio.run(graph.start_job("job-start"))
    continue_result = asyncio.run(graph.continue_job("job-continue"))

    assert start_result == {"status": "started", "job_id": "job-start"}
    assert continue_result == {"status": "continued", "job_id": "job-continue"}


def test_review_graph_can_run_with_stubbed_review_services():
    """验证 review LangGraph 可在 stub 服务下完成 interrupt / resume 主链。"""
    from agents.base_agent import OpResult
    from mold_cost.application.workflows.review_graph import ReviewGraph
    from mold_cost.application.workflows.review_state import ReviewState

    class StubSessionService:
        def __init__(self):
            self._locks: set[str] = set()

        async def acquire(self, job_id: str, timeout: int = 1800) -> bool:
            self._locks.add(job_id)
            return True

        async def ensure_active(self, job_id: str, timeout: int = 1800) -> bool:
            self._locks.add(job_id)
            return True

        async def renew(self, job_id: str, timeout: int = 1800) -> bool:
            return job_id in self._locks

        async def is_locked(self, job_id: str) -> bool:
            return job_id in self._locks

    class StubStateStore:
        def __init__(self):
            self._states: dict[str, ReviewState] = {}

        def build_state(self, job_id: str, **kwargs):
            return ReviewState(job_id=job_id, **kwargs)

        def calculate_data_version(self, raw_data: dict):
            return {"features:sub-1": f"v{len(raw_data.get('features', []))}"}

        def serialize(self, state: ReviewState) -> dict:
            return state.to_payload()

        async def load(self, job_id: str):
            return self._states.get(job_id)

        async def save(self, state: ReviewState, ex: int = 3600) -> None:
            self._states[state.job_id] = state

        async def renew(self, job_id: str, timeout: int = 3600) -> bool:
            return job_id in self._states

    class StubDataLoader:
        async def load(self, job_id: str, db_session):
            return {
                "features": [{"feature_id": "feat-1"}],
                "subgraphs": [{"subgraph_id": "sub-1"}],
                "job_price_snapshots": [{"snapshot_id": "snap-1"}],
            }

        def build_display_view(self, raw_data: dict):
            return [{"kind": "feature", "count": len(raw_data["features"])}]

        def check_completeness(self, raw_data: dict):
            return {"is_complete": True, "missing_fields": []}

        def build_completion_prompt(self, missing_fields: list[dict], raw_data: dict):
            return "请补全缺失字段"

    class StubChatExecutor:
        async def generate_completion_suggestion(self, prompt: str, context_data: dict) -> str:
            return f"suggestion:{prompt}"

        async def chat(self, job_id: str, message: str, history: list[dict], current_data):
            return {
                "job_id": job_id,
                "message": message,
                "history": history,
                "current_data": current_data,
            }

        async def chat_stream(self, job_id: str, message: str, history: list[dict], current_data):
            yield {"job_id": job_id, "chunk": message}

    class StubChangeApplier:
        async def handle_modification(
            self,
            *,
            state: ReviewState,
            modification_text: str,
            user_id: str,
            db_session,
        ):
            state.modifications.append({"text": modification_text, "user_id": user_id})
            state.status = "awaiting_confirmation"
            return state, OpResult(
                status="ok",
                message="修改已暂存，请确认",
                data={
                    "action": "modify",
                    "job_id": state.job_id,
                    "modification_text": modification_text,
                    "user_id": user_id,
                    "db": db_session,
                    "requires_confirmation": True,
                },
            )

        async def confirm_changes(self, *, state: ReviewState, user_id: str, db_session):
            state.modifications = []
            state.confirm_count += 1
            state.status = "reviewing"
            return state, OpResult(
                status="ok",
                message="操作已执行，可以继续修改",
                data={"action": "confirm", "job_id": state.job_id, "user_id": user_id, "db": db_session},
            )

    class StubNotifier:
        async def push_display_view(self, job_id: str, display_view: list[dict], db_session=None) -> None:
            return None

        async def push_completion_request(self, job_id: str, completion_data: dict, db_session=None) -> None:
            return None

        async def push_system_message(self, job_id: str, message_text: str, db_session=None) -> None:
            return None

    graph = ReviewGraph(
        session_service=StubSessionService(),
        state_store=StubStateStore(),
        data_loader=StubDataLoader(),
        chat_executor=StubChatExecutor(),
        change_applier=StubChangeApplier(),
        notifier=StubNotifier(),
    )

    start_result = asyncio.run(graph.start_review("job-review", "db"))
    assert isinstance(start_result, OpResult)
    assert start_result.status == "ok"
    assert start_result.data["job_id"] == "job-review"
    start_snapshot = graph.get_graph_state("job-review")
    assert start_snapshot is not None
    assert start_snapshot.interrupts
    assert asyncio.run(graph.get_review_state("job-review"))["waiting_for"] == "user_message"

    modify_result = asyncio.run(graph.handle_modification("job-review", "修改材质", "u1", "db"))
    assert isinstance(modify_result, OpResult)
    assert modify_result.data["action"] == "modify"
    modify_snapshot = graph.get_graph_state("job-review")
    assert modify_snapshot is not None
    assert modify_snapshot.interrupts
    assert asyncio.run(graph.get_review_state("job-review"))["waiting_for"] == "confirmation"

    confirm_result = asyncio.run(graph.confirm_changes("job-review", "u1", "db"))
    assert isinstance(confirm_result, OpResult)
    assert confirm_result.data["action"] == "confirm"
    confirm_snapshot = graph.get_graph_state("job-review")
    assert confirm_snapshot is not None
    assert not confirm_snapshot.interrupts

    refresh_result = asyncio.run(graph.refresh_data("job-review", "db"))
    assert isinstance(refresh_result, OpResult)
    assert refresh_result.status == "ok"
    assert refresh_result.data["refresh_count"] == 1
    assert refresh_result.data["is_complete"] is True

    persisted_state = asyncio.run(graph.get_review_state("job-review"))
    assert persisted_state["job_id"] == "job-review"
    assert persisted_state["status"] == "reviewing"
    assert persisted_state["waiting_for"] == "user_message"
    assert asyncio.run(graph.check_lock("job-review")) is True
    assert asyncio.run(graph.chat("job-review", "你好", [], {"x": 1}))["message"] == "你好"

    async def _collect_stream():
        items = []
        async for chunk in graph.chat_stream("job-review", "stream", [], None):
            items.append(chunk)
        return items

    assert asyncio.run(_collect_stream()) == [{"job_id": "job-review", "chunk": "stream"}]


def test_continue_job_route_bridges_to_job_service(monkeypatch):
    """验证 jobs 路由的 continue 入口已经桥接到新的任务服务。"""
    from api_gateway.routers import jobs as jobs_router

    calls: list[str] = []

    class FakeJobService:
        async def submit_continue_job(self, job_id: str):
            calls.append(job_id)
            return {"status": "accepted", "job_id": job_id}

    monkeypatch.setattr(jobs_router, "JobService", FakeJobService)

    result = asyncio.run(jobs_router.continue_job("job-legacy", current_user={"user_id": "u1"}))

    assert result == {"status": "accepted", "job_id": "job-legacy"}
    assert calls == ["job-legacy"]
