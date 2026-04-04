"""重构后主骨架的离线冒烟验证。"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_refactor_entrypoints_can_import():
    """验证新旧入口在不连接外部服务时可以完成导入。"""
    from api_gateway.routers import chat_router, features, jobs, review_router
    from api_gateway.services.file_service import FileService
    from api_gateway.services.job_service import JobService
    from mold_cost.application.workflows.job_graph import job_graph
    from mold_cost.interfaces.api import legacy_cad_app
    from mold_cost.application.workflows.review_graph import review_graph
    from tools.diagnostics import check_services as tools_check_services
    from tools.diagnostics import verify_integration as tools_verify_integration
    from scripts import check_services as legacy_check_services
    from scripts import unified_api as legacy_unified_api
    from scripts import verify_integration as legacy_verify_integration

    # 中文注释：这里按文件直接加载 cad_chaitu 下的兼容壳，避免触发旧包的重型初始化链。
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
    assert isinstance(JobService(), JobService)
    assert isinstance(FileService(), FileService)
    assert job_graph is not None
    assert review_graph is not None
    assert legacy_cad_app is not None
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


def test_review_graph_can_delegate_to_stubbed_agent(monkeypatch):
    """验证审核工作流外壳能正常委派给交互代理。"""
    from mold_cost.application.workflows.review_graph import ReviewGraph

    class StubAgent:
        async def start_review(self, job_id: str, db_session):
            return {"action": "start", "job_id": job_id, "db": db_session}

        async def handle_modification(self, job_id: str, modification_text: str, user_id: str, db_session):
            return {
                "action": "modify",
                "job_id": job_id,
                "modification_text": modification_text,
                "user_id": user_id,
                "db": db_session,
            }

        async def confirm_changes(self, job_id: str, user_id: str, db_session):
            return {"action": "confirm", "job_id": job_id, "user_id": user_id, "db": db_session}

        async def refresh_data(self, job_id: str, db_session):
            return {"action": "refresh", "job_id": job_id, "db": db_session}

        async def get_review_state(self, job_id: str):
            return {"job_id": job_id, "status": "reviewing"}

        async def check_lock(self, job_id: str) -> bool:
            return job_id == "locked-job"

        async def chat(self, job_id: str, message: str, history: list[dict], current_data):
            return {
                "job_id": job_id,
                "message": message,
                "history": history,
                "current_data": current_data,
            }

        async def chat_stream(self, job_id: str, message: str, history: list[dict], current_data):
            yield {"job_id": job_id, "chunk": message}

    graph = ReviewGraph()
    monkeypatch.setattr(graph, "_get_agent", lambda: StubAgent())

    assert asyncio.run(graph.start_review("job-review", "db"))["action"] == "start"
    assert asyncio.run(graph.handle_modification("job-review", "修改材料", "u1", "db"))["action"] == "modify"
    assert asyncio.run(graph.confirm_changes("job-review", "u1", "db"))["action"] == "confirm"
    assert asyncio.run(graph.refresh_data("job-review", "db"))["action"] == "refresh"
    assert asyncio.run(graph.get_review_state("job-review")) == {"job_id": "job-review", "status": "reviewing"}
    assert asyncio.run(graph.check_lock("locked-job")) is True
    assert asyncio.run(graph.chat("job-review", "你好", [], {"x": 1}))["message"] == "你好"

    async def _collect_stream():
        items = []
        async for chunk in graph.chat_stream("job-review", "stream", [], None):
            items.append(chunk)
        return items

    assert asyncio.run(_collect_stream()) == [{"job_id": "job-review", "chunk": "stream"}]


def test_legacy_continue_helper_bridges_to_use_case(monkeypatch):
    """验证旧 jobs 路由中的继续执行辅助函数已经桥接到新用例。"""
    from api_gateway.routers import jobs as jobs_router

    calls: list[str] = []

    class FakeContinueJobUseCase:
        async def _execute_continue_job(self, job_id: str):
            calls.append(job_id)

    monkeypatch.setattr(jobs_router, "ContinueJobUseCase", FakeContinueJobUseCase)

    asyncio.run(jobs_router._execute_continue_job(None, "job-legacy"))

    assert calls == ["job-legacy"]
