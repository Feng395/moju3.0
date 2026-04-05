"""Tests for review workflow adapters and default wiring."""

from __future__ import annotations

import importlib

import pytest

from mold_cost.application.workflows.review_state import ReviewState


class _FakeReviewRepository:
    def __init__(self):
        self.load_calls: list[tuple[object, str]] = []
        self.update_calls: list[tuple[object, str, dict]] = []

    async def get_all_review_data(self, db_session, job_id: str):
        self.load_calls.append((db_session, job_id))
        return {
            "features": [{"feature_id": "f-1"}],
            "job_price_snapshots": [{"snapshot_id": 1}],
            "subgraphs": [{"subgraph_id": "sg-1"}],
            "processing_cost_calculation_details": [{"detail_id": "d-1"}],
        }

    async def update_all_review_data(self, db_session, job_id: str, data: dict):
        self.update_calls.append((db_session, job_id, data))


class _FakeStateStore:
    def __init__(self):
        self.saved_states: list[ReviewState] = []

    def calculate_data_version(self, raw_data: dict) -> dict[str, str]:
        return {
            "features:f-1": "hash-1",
            "job_price_snapshots:1": "hash-2",
            "subgraphs:sg-1": "hash-3",
            "processing_cost_calculation_details:d-1": "hash-4",
        }

    async def save(self, state: ReviewState, ex: int = 3600) -> None:
        self.saved_states.append(state)


@pytest.mark.asyncio
async def test_review_data_loader_uses_infra_adapter_by_default(monkeypatch):
    module = importlib.import_module("mold_cost.domain.review.services.review_data_loader")

    fake_repo = _FakeReviewRepository()
    monkeypatch.setattr(module, "LegacyReviewRepositoryAdapter", lambda: fake_repo)

    loader = module.LegacyReviewDataLoader()
    raw_data = await loader.load("job-1", db_session="db")

    assert fake_repo.load_calls == [("db", "job-1")]
    assert raw_data["features"][0]["feature_id"] == "f-1"


@pytest.mark.asyncio
async def test_review_change_applier_confirm_uses_infra_adapter_by_default(monkeypatch):
    module = importlib.import_module("mold_cost.domain.review.services.review_change_applier")

    fake_repo = _FakeReviewRepository()
    fake_state_store = _FakeStateStore()

    class _FakeConfirmationExecutor:
        async def handle_confirmation(self, *, job_id: str, user_id: str, db_session):
            return {
                "status": "ok",
                "message": "confirmed",
                "data": {"job_id": job_id, "user_id": user_id, "db_session": db_session},
            }

    monkeypatch.setattr(module, "LegacyReviewRepositoryAdapter", lambda: fake_repo)

    applier = module.InteractionAgentReviewChangeApplier(
        state_store=fake_state_store,
        confirmation_executor=_FakeConfirmationExecutor(),
    )
    state = ReviewState(
        job_id="job-2",
        raw_data={
            "features": [{"feature_id": "f-1"}],
            "job_price_snapshots": [{"snapshot_id": 1}],
            "subgraphs": [{"subgraph_id": "sg-1"}],
            "processing_cost_calculation_details": [{"detail_id": "d-1"}],
        },
        data_version={
            "features:f-1": "hash-1",
            "job_price_snapshots:1": "hash-2",
            "subgraphs:sg-1": "hash-3",
            "processing_cost_calculation_details:d-1": "hash-4",
        },
        modifications=[{"id": "m-1"}],
        status="awaiting_confirmation",
    )

    updated_state, result = await applier.confirm_changes(
        state=state,
        user_id="u-1",
        db_session="db",
    )

    assert fake_repo.load_calls == [("db", "job-2")]
    assert result.status == "ok"
    assert updated_state.confirm_count == 1
    assert updated_state.modifications == []
    assert fake_state_store.saved_states


@pytest.mark.asyncio
async def test_review_change_applier_modification_uses_adapter_collaborators(monkeypatch):
    module = importlib.import_module("mold_cost.domain.review.services.review_change_applier")

    fake_repo = _FakeReviewRepository()
    fake_state_store = _FakeStateStore()
    modified_payload = {
        "features": [{"feature_id": "f-1"}],
        "job_price_snapshots": [{"snapshot_id": 1}],
        "subgraphs": [{"subgraph_id": "sg-1", "material": "S136"}],
        "processing_cost_calculation_details": [{"detail_id": "d-1"}],
    }

    class _FakeIntentResult:
        intent_type = "DATA_MODIFICATION"

    class _FakeRecognizer:
        async def recognize(self, message, context, job_id=None, db_session=None):
            assert message == "修改材质"
            assert job_id == "job-3"
            assert db_session == "db"
            return _FakeIntentResult()

        async def close(self):
            return None

    class _FakeRecognizerFactory:
        def create(self):
            return _FakeRecognizer()

    class _FakeActionResult:
        status = "ok"
        message = "pending confirm"
        requires_confirmation = True
        data = {
            "modified_data": modified_payload,
            "display_view": [{"label": "updated"}],
            "parsed_changes": [{"field": "material"}],
            "modification_id": "m-2",
        }

    class _FakeHandler:
        async def handle(self, intent_result, job_id, context, db_session):
            assert intent_result.intent_type == "DATA_MODIFICATION"
            assert job_id == "job-3"
            assert context["user_id"] == "u-1"
            assert db_session == "db"
            return _FakeActionResult()

    class _FakeRegistry:
        def ensure_initialized(self):
            return None

        def get_handler(self, intent_type: str):
            assert intent_type == "DATA_MODIFICATION"
            return _FakeHandler()

    monkeypatch.setattr(module, "LegacyReviewRepositoryAdapter", lambda: fake_repo)

    applier = module.InteractionAgentReviewChangeApplier(
        state_store=fake_state_store,
        review_repository=fake_repo,
        intent_recognizer_factory=_FakeRecognizerFactory(),
        action_handler_registry=_FakeRegistry(),
    )
    state = ReviewState(
        job_id="job-3",
        raw_data={
            "features": [{"feature_id": "f-1"}],
            "job_price_snapshots": [{"snapshot_id": 1}],
            "subgraphs": [{"subgraph_id": "sg-1"}],
            "processing_cost_calculation_details": [{"detail_id": "d-1"}],
        },
        data_version={
            "features:f-1": "hash-1",
            "job_price_snapshots:1": "hash-2",
            "subgraphs:sg-1": "hash-3",
            "processing_cost_calculation_details:d-1": "hash-4",
        },
        modifications=[],
        status="reviewing",
    )

    updated_state, result = await applier.handle_modification(
        state=state,
        modification_text="修改材质",
        user_id="u-1",
        db_session="db",
    )

    assert fake_repo.load_calls == [("db", "job-3")]
    assert result.status == "ok"
    assert result.data["requires_confirmation"] is True
    assert updated_state.raw_data == modified_payload
    assert updated_state.display_view == [{"label": "updated"}]
    assert updated_state.status == "awaiting_confirmation"
    assert updated_state.modifications[0]["id"] == "m-2"
    assert fake_state_store.saved_states


def test_review_graph_default_wiring_uses_shared_review_repository(monkeypatch):
    module = importlib.import_module("mold_cost.application.workflows.review_graph")

    fake_repo = _FakeReviewRepository()
    monkeypatch.setattr(module, "LegacyReviewRepositoryAdapter", lambda: fake_repo)

    graph = module.ReviewGraph()
    data_loader = graph._get_data_loader()
    change_applier = graph._get_change_applier()

    assert data_loader.review_repo is fake_repo
    assert change_applier.review_repo is fake_repo
