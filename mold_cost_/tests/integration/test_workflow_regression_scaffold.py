"""Workflow-level regression scaffolding tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def _load_bundle():
    from tools.diagnostics.golden_workflow import load_inventory, load_sample_bundle

    # 中文注释：integration 骨架复用 golden inventory，避免测试样本定义出现分叉。
    inventory = load_inventory()
    sample_entry = inventory["golden_samples"][0]
    bundle = load_sample_bundle(sample_entry)
    return inventory, bundle


def _load_workflow_objects():
    # 中文注释：延迟导入 workflow 对象，减少 pytest 收集阶段被环境差异影响。
    ensure_src_path()
    from mold_cost.application.use_cases import continue_job as continue_job_module
    from mold_cost.application.use_cases.continue_job import ContinueJobUseCase
    from mold_cost.application.workflows.job_graph import job_graph
    from mold_cost.application.workflows.review_graph import review_graph

    return ContinueJobUseCase, continue_job_module, job_graph, review_graph


def test_pause_resume_fixture_can_be_hydrated():
    from tools.diagnostics.golden_workflow import (
        hydrate_pause_resume_fixture,
        load_pause_resume_template,
    )

    _ContinueJobUseCase, _continue_job_module, job_graph, review_graph = _load_workflow_objects()
    _inventory, bundle = _load_bundle()
    template = load_pause_resume_template(
        Path(__file__).with_name("fixtures") / "workflow_pause_resume_fixture.json"
    )
    fixture = hydrate_pause_resume_fixture(
        template=template,
        manifest=bundle["manifest"],
        expected_summary=bundle["expected_summary"],
        job_graph=job_graph,
        review_graph=review_graph,
    )

    # 中文注释：这里验证的是“恢复快照合同”，不是执行真实的 review/pricing 逻辑。
    assert fixture["fixture_version"] == "workflow.pause_resume.v1"
    assert fixture["job_state"]["status"] == "paused"
    assert fixture["job_state"]["artifacts"]["golden_sample_id"] == bundle["manifest"]["sample_id"]
    assert fixture["job_state"]["artifacts"]["last_completed_stage"] == "feature_recognition"
    assert fixture["job_state"]["artifacts"]["next_stage"] == "pricing"
    assert fixture["review_state"]["status"] == "awaiting_confirm"
    assert fixture["resume_request"]["action"] == "continue_job"


def test_continue_job_use_case_accepts_pause_resume_fixture(monkeypatch):
    from tools.diagnostics.golden_workflow import (
        hydrate_pause_resume_fixture,
        load_pause_resume_template,
    )

    ContinueJobUseCase, continue_job_module, job_graph, review_graph = _load_workflow_objects()
    _inventory, bundle = _load_bundle()
    template = load_pause_resume_template(
        Path(__file__).with_name("fixtures") / "workflow_pause_resume_fixture.json"
    )
    fixture = hydrate_pause_resume_fixture(
        template=template,
        manifest=bundle["manifest"],
        expected_summary=bundle["expected_summary"],
        job_graph=job_graph,
        review_graph=review_graph,
    )

    scheduled = {}
    calls: list[str] = []

    def fake_create_task(coro):
        # 中文注释：拦截后台任务调度，只验证 submit 是否把 continue 请求正确挂起。
        scheduled["coro"] = coro

        class DummyTask:
            def done(self) -> bool:
                return False

        return DummyTask()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    use_case = ContinueJobUseCase()

    async def fake_execute_continue_job(job_id: str):
        # 中文注释：跳过 MQ/Redis 等外部依赖，只验证恢复入口收到正确 job_id。
        calls.append(job_id)

    monkeypatch.setattr(use_case, "_execute_continue_job", fake_execute_continue_job)
    response = asyncio.run(use_case.submit(fixture["job_state"]["job_id"]))

    assert response["status"] == "accepted"
    assert response["job_id"] == fixture["job_state"]["job_id"]

    asyncio.run(scheduled["coro"])

    assert calls == [fixture["job_state"]["job_id"]]
