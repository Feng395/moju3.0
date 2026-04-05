"""ReviewGraph durable checkpoint resume integration tests."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_review_graph_can_resume_from_durable_checkpoint_after_restart():
    from agents.base_agent import OpResult
    from mold_cost.application.workflows.review_graph import ReviewGraph
    from mold_cost.application.workflows.review_state import ReviewState
    from mold_cost.infrastructure.workflows.review_file_checkpoint_store import ReviewFileCheckpointStore

    class StubSessionService:
        async def acquire(self, job_id: str, timeout: int = 1800) -> bool:
            return True

        async def ensure_active(self, job_id: str, timeout: int = 1800) -> bool:
            return True

        async def renew(self, job_id: str, timeout: int = 1800) -> bool:
            return True

        async def is_locked(self, job_id: str) -> bool:
            return True

    class EphemeralStateStore:
        def __init__(self):
            self._states: dict[str, ReviewState] = {}

        def build_state(self, job_id: str, **kwargs):
            return ReviewState(job_id=job_id, **kwargs)

        def calculate_data_version(self, raw_data: dict):
            return {"features:feat-1": f"v{len(raw_data.get('features', []))}"}

        def serialize(self, state: ReviewState) -> dict:
            return state.to_payload()

        async def load(self, job_id: str):
            return self._states.get(job_id)

        async def save(self, state: ReviewState, ex: int = 3600) -> None:
            self._states[state.job_id] = state

        async def renew(self, job_id: str, timeout: int = 3600) -> bool:
            return True

    class StubDataLoader:
        async def load(self, job_id: str, db_session):
            return {
                "features": [{"feature_id": "feat-1", "subgraph_id": "sub-1"}],
                "subgraphs": [{"subgraph_id": "sub-1"}],
                "job_price_snapshots": [{"snapshot_id": "snap-1"}],
            }

        def build_display_view(self, raw_data: dict):
            return [{"kind": "feature", "count": len(raw_data["features"])}]

        def check_completeness(self, raw_data: dict):
            return {"is_complete": True, "missing_fields": []}

        def build_completion_prompt(self, missing_fields: list[dict], raw_data: dict):
            return "complete"

    class StubChatExecutor:
        async def generate_completion_suggestion(self, prompt: str, context_data: dict) -> str:
            return f"suggestion:{prompt}"

        async def chat(self, job_id: str, message: str, history: list[dict], current_data):
            return {"job_id": job_id, "message": message}

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
                message="modified",
                data={"action": "modify", "requires_confirmation": True},
            )

        async def confirm_changes(self, *, state: ReviewState, user_id: str, db_session):
            state.modifications = []
            state.confirm_count += 1
            state.status = "reviewing"
            return state, OpResult(
                status="ok",
                message="confirmed",
                data={"action": "confirm", "confirm_count": state.confirm_count},
            )

    class StubNotifier:
        async def push_display_view(self, job_id: str, display_view: list[dict], db_session=None) -> None:
            return None

        async def push_completion_request(self, job_id: str, completion_data: dict, db_session=None) -> None:
            return None

        async def push_system_message(self, job_id: str, message_text: str, db_session=None) -> None:
            return None

    temp_dir = Path(__file__).resolve().parent / ".review-checkpoint-runtime"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    store = ReviewFileCheckpointStore(root_dir=temp_dir)

    def build_graph():
        return ReviewGraph(
            session_service=StubSessionService(),
            state_store=EphemeralStateStore(),
            data_loader=StubDataLoader(),
            chat_executor=StubChatExecutor(),
            change_applier=StubChangeApplier(),
            notifier=StubNotifier(),
            durable_store=store,
        )

    graph1 = build_graph()
    start_result = asyncio.run(graph1.start_review("job-review-restart", "db"))
    assert start_result.status == "ok"
    durable_state_after_start = store.load("job-review-restart")
    assert durable_state_after_start is not None
    assert durable_state_after_start["state"]["waiting_for"] == "user_message"

    graph2 = build_graph()
    modify_result = asyncio.run(graph2.handle_modification("job-review-restart", "修改材质", "u1", "db"))
    assert modify_result.status == "ok"
    assert modify_result.data["action"] == "modify"
    durable_state_after_modify = store.load("job-review-restart")
    assert durable_state_after_modify is not None
    assert durable_state_after_modify["state"]["waiting_for"] == "confirmation"

    graph3 = build_graph()
    confirm_result = asyncio.run(graph3.confirm_changes("job-review-restart", "u1", "db"))
    assert confirm_result.status == "ok"
    assert confirm_result.data["action"] == "confirm"
    durable_state_after_confirm = store.load("job-review-restart")
    assert durable_state_after_confirm is not None
    assert durable_state_after_confirm["state"]["waiting_for"] == "user_message"
    assert durable_state_after_confirm["state"]["confirm_count"] == 1
    shutil.rmtree(temp_dir, ignore_errors=True)
