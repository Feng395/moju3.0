"""JobGraph checkpoint/resume integration tests."""

from __future__ import annotations

import asyncio

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_job_graph_checkpoint_resume_uses_job_id_as_thread_id():
    from mold_cost.application.workflows.job_graph import JobGraph

    class StubOrchestrator:
        async def start(self, job_id: str):
            return {
                "status": "ok",
                "job_id": job_id,
                "action_required": "user_confirmation",
                "summary": {"success_count": 2, "failed_count": 0},
            }

        async def continue_job(self, job_id: str):
            return {
                "status": "ok",
                "job_id": job_id,
                "summary": {"duration_ms": 12},
            }

    async def _run():
        graph = JobGraph(orchestrator=StubOrchestrator())
        job_id = "job-checkpoint-resume"

        start_state = await graph.run_with_state(job_id, action="start")
        continue_state = await graph.run_with_state(job_id, action="continue")

        return start_state, continue_state

    start_state, continue_state = asyncio.run(_run())

    start_checkpoint = start_state.artifacts["checkpoint"]
    continue_checkpoint = continue_state.artifacts["checkpoint"]

    # 中文注释：start 和 continue 必须命中同一个 LangGraph thread，确保恢复入口只依赖 job_id。
    assert start_checkpoint["config"]["configurable"]["thread_id"] == "job-checkpoint-resume"
    assert continue_checkpoint["config"]["configurable"]["thread_id"] == "job-checkpoint-resume"

    # 中文注释：继续执行前要能从上一轮 checkpoint 读回 feature 阶段结果。
    assert start_state.status == "interrupted"
    assert continue_state.status == "completed"
    assert continue_state.feature_summary["success_count"] == 2
    assert continue_state.artifacts["resumed_from_thread"] == "job-checkpoint-resume"
    assert (
        continue_state.artifacts["resume_checkpoint"]["configurable"]["thread_id"]
        == "job-checkpoint-resume"
    )

    # 中文注释：恢复后应生成新的 checkpoint，而不是复用旧 checkpoint_id。
    assert start_checkpoint["checkpoint_id"] != continue_checkpoint["checkpoint_id"]
