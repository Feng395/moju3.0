"""JobGraph checkpoint/resume integration tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
import shutil

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_job_graph_checkpoint_resume_uses_job_id_as_thread_id():
    from mold_cost.application.workflows.job_graph import JobGraph
    from mold_cost.infrastructure.workflows.job_file_checkpoint_store import JobFileCheckpointStore

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
        temp_dir = Path(__file__).resolve().parent / ".job-checkpoint-runtime"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        try:
            store = JobFileCheckpointStore(temp_dir)
            job_id = "job-checkpoint-resume"

            start_graph = JobGraph(orchestrator=StubOrchestrator(), durable_store=store)
            start_state = await start_graph.run_with_state(job_id, action="start")

            continue_graph = JobGraph(orchestrator=StubOrchestrator(), durable_store=store)
            continue_state = await continue_graph.run_with_state(job_id, action="continue")

            return start_state, continue_state
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    start_state, continue_state = asyncio.run(_run())

    start_checkpoint = start_state.artifacts["checkpoint"]
    continue_checkpoint = continue_state.artifacts["checkpoint"]

    assert start_checkpoint["config"]["configurable"]["thread_id"] == "job-checkpoint-resume"
    assert continue_checkpoint["config"]["configurable"]["thread_id"] == "job-checkpoint-resume"

    assert start_state.status == "interrupted"
    assert continue_state.status == "completed"
    assert continue_state.feature_summary["success_count"] == 2
    assert continue_state.artifacts["resumed_from_thread"] == "job-checkpoint-resume"
    assert continue_state.artifacts["resume_checkpoint"]["configurable"]["thread_id"] == "job-checkpoint-resume"
    assert start_checkpoint["checkpoint_id"] != continue_checkpoint["checkpoint_id"]


def test_orchestrator_worker_can_resume_from_durable_checkpoint_after_restart():
    from mold_cost.application.workflows.job_graph import JobGraph
    from mold_cost.infrastructure.workflows.job_file_checkpoint_store import JobFileCheckpointStore
    from workers.orchestrator_worker import OrchestratorWorker

    class StubOrchestrator:
        async def start(self, job_id: str):
            return {
                "status": "ok",
                "job_id": job_id,
                "action_required": "user_confirmation",
                "summary": {"success_count": 1},
            }

        async def continue_job(self, job_id: str):
            return {
                "status": "ok",
                "job_id": job_id,
                "summary": {"duration_ms": 20, "resumed": True},
            }

    async def _run():
        temp_dir = Path(__file__).resolve().parent / ".job-checkpoint-worker-restart"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        try:
            store = JobFileCheckpointStore(temp_dir)
            job_id = "job-worker-restart"

            start_graph = JobGraph(orchestrator=StubOrchestrator(), durable_store=store)
            first_worker = OrchestratorWorker(job_workflow=start_graph)
            await first_worker.handle_message({"job_id": job_id, "thread_id": job_id, "action": "start"})

            checkpoint_payload = store.load(job_id)
            assert checkpoint_payload is not None
            assert checkpoint_payload["thread_id"] == job_id

            continue_graph = JobGraph(orchestrator=StubOrchestrator(), durable_store=store)
            restarted_worker = OrchestratorWorker(job_workflow=continue_graph)
            await restarted_worker.handle_message({"job_id": job_id, "thread_id": job_id, "action": "continue"})

            return checkpoint_payload, store.load(job_id)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    start_checkpoint_payload, continue_checkpoint_payload = asyncio.run(_run())

    assert start_checkpoint_payload["checkpoint"]["config"]["configurable"]["thread_id"] == "job-worker-restart"
    assert continue_checkpoint_payload is not None
    assert continue_checkpoint_payload["checkpoint"]["config"]["configurable"]["thread_id"] == "job-worker-restart"
    assert continue_checkpoint_payload["state"]["status"] == "completed"
    assert continue_checkpoint_payload["state"]["pricing_summary"]["resumed"] is True
