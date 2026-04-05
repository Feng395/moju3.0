"""Tests for review workflow adapters and default wiring."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

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
    fake_display_view_builder = type(
        "_FakeDisplayViewBuilder",
        (),
        {"build_display_view": staticmethod(lambda raw_data: [{"rows": len(raw_data.get("subgraphs", []))}])},
    )()
    fake_completeness_validator = type(
        "_FakeCompletenessValidator",
        (),
        {
            "check_data_completeness": staticmethod(lambda raw_data: {"is_complete": True, "raw_size": len(raw_data)}),
            "generate_completion_prompt": staticmethod(
                lambda missing_fields, raw_data: f"missing={len(missing_fields)} size={len(raw_data)}"
            ),
        },
    )()

    monkeypatch.setattr(module, "LegacyReviewRepositoryAdapter", lambda: fake_repo)
    monkeypatch.setattr(module, "LegacyReviewDisplayViewBuilder", lambda: fake_display_view_builder)
    monkeypatch.setattr(module, "LegacyReviewCompletenessValidator", lambda: fake_completeness_validator)

    loader = module.LegacyReviewDataLoader()
    raw_data = await loader.load("job-1", db_session="db")

    assert fake_repo.load_calls == [("db", "job-1")]
    assert raw_data["features"][0]["feature_id"] == "f-1"
    assert loader.build_display_view(raw_data) == [{"rows": 1}]
    assert loader.check_completeness(raw_data) == {"is_complete": True, "raw_size": 4}
    assert loader.build_completion_prompt([{"field": "material"}], raw_data) == "missing=1 size=4"


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
    built_change_appliers: list[object] = []

    def _fake_build_default_review_change_applier(*, state_store, review_repository):
        built = type(
            "_FakeBuiltChangeApplier",
            (),
            {"review_repo": review_repository, "state_store": state_store},
        )()
        built_change_appliers.append(built)
        return built

    monkeypatch.setattr(module, "LegacyReviewRepositoryAdapter", lambda: fake_repo)
    monkeypatch.setattr(module, "build_default_review_change_applier", _fake_build_default_review_change_applier)

    graph = module.ReviewGraph()
    data_loader = graph._get_data_loader()
    change_applier = graph._get_change_applier()

    assert data_loader.review_repo is fake_repo
    assert change_applier.review_repo is fake_repo
    assert built_change_appliers


def test_review_handler_runtime_builder_injects_legacy_collaborators():
    module = importlib.import_module("mold_cost.infrastructure.review.legacy_review_handler_adapter")

    applier = module.build_default_review_change_applier(
        state_store="state-store",
        review_repository="review-repo",
    )

    assert applier._state_store == "state-store"
    assert applier.review_repo == "review-repo"
    assert applier._intent_recognizer_factory.__class__.__name__ == "SrcReviewIntentRecognizerFactory"
    assert applier._action_handler_registry.__class__.__name__ == "SrcReviewActionHandlerRegistry"
    assert applier._confirmation_executor.__class__.__name__ == "ReviewConfirmationExecutorAdapter"

    source = importlib.import_module("mold_cost.infrastructure.review.confirmation_executor").__file__
    assert "agents.confirm_handler" not in open(source, "r", encoding="utf-8").read()


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_handles_simple_execution_intents_without_legacy():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for simple execution intents")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())
    result = await recognizer.recognize(
        "重新计算 DIE-03 的价格",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-13",
        db_session="db",
    )

    assert result.intent_type == "PRICE_CALCULATION"
    assert result.parameters == {"subgraph_ids": ["DIE-03"]}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_extracts_template_keyword_for_price_calculation():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for template price-calculation rule")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())
    result = await recognizer.recognize(
        "单独把模板计算一下",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_TMP-01"}]}},
        job_id="job-13b",
        db_session="db",
    )

    assert result.intent_type == "PRICE_CALCULATION"
    assert result.parameters == {"keyword": "模板"}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_extracts_template_keyword_for_feature_recognition():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for template feature-recognition rule")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())
    result = await recognizer.recognize(
        "重新识别模板",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_TMP-01"}]}},
        job_id="job-13c",
        db_session="db",
    )

    assert result.intent_type == "FEATURE_RECOGNITION"
    assert result.parameters == {"keyword": "模板"}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_handles_contextual_query_without_legacy():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for contextual query rule")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())

    result = await recognizer.recognize(
        "继续按刚才那套判断逻辑处理这个零件",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14",
        db_session="db",
    )

    assert result.intent_type == "QUERY_DETAILS"
    assert result.parameters == {}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_handles_contextual_data_modification_without_legacy():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for contextual data modification rule")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())

    result = await recognizer.recognize(
        "还是按刚才那个把这个零件的材质改一下",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14ctx",
        db_session="db",
    )

    assert result.intent_type == "DATA_MODIFICATION"
    assert result.parameters == {}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_factory_wraps_legacy_fallback():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _FallbackFactory:
        def __init__(self):
            self.created = 0

        def create(self):
            self.created += 1
            return SimpleNamespace(
                recognize=_async_return_none,
                close=_async_return_none,
            )

    fallback_factory = _FallbackFactory()
    factory = module.SrcReviewIntentRecognizerFactory(fallback_factory=fallback_factory)
    recognizer = factory.create()

    assert recognizer.__class__.__name__ == "SrcReviewIntentRecognizer"
    assert recognizer._fallback_recognizer is not None
    assert fallback_factory.created == 0


async def _async_return_none(*args, **kwargs):
    return None


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_factory_creates_legacy_fallback_lazily():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _FallbackRecognizer:
        def __init__(self):
            self.calls = []

        async def recognize(self, message, context, job_id=None, db_session=None):
            self.calls.append((message, job_id, db_session))
            return SimpleNamespace(intent_type="QUERY_DETAILS", confidence=0.61, parameters={})

        async def close(self):
            return None

    class _FallbackFactory:
        def __init__(self):
            self.created = 0
            self.instance = None

        def create(self):
            self.created += 1
            self.instance = _FallbackRecognizer()
            return self.instance

    fallback_factory = _FallbackFactory()
    recognizer = module.SrcReviewIntentRecognizerFactory(fallback_factory=fallback_factory).create()

    assert fallback_factory.created == 0

    result = await recognizer.recognize(
        "继续按更复杂的上下文来理解这句话",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14lazy",
        db_session="db",
    )

    assert result.intent_type == "QUERY_DETAILS"
    assert fallback_factory.created == 1
    assert fallback_factory.instance.calls == [("继续按更复杂的上下文来理解这句话", "job-14lazy", "db")]


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_handles_query_details_without_legacy():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for query-details rule")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())
    result = await recognizer.recognize(
        "DIE-03 的材料费怎么算的？",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14a",
        db_session="db",
    )

    assert result.intent_type == "QUERY_DETAILS"
    assert result.parameters == {"subgraph_id": "DIE-03", "query_type": "material"}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_handles_verification_query_without_legacy():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for verification query")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())
    result = await recognizer.recognize(
        "B2-03 大水磨长条费用这样对吗？",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_B2-03"}]}},
        job_id="job-14b",
        db_session="db",
    )

    assert result.intent_type == "QUERY_DETAILS"
    assert result.parameters == {"subgraph_id": "B2-03", "query_type": "water_mill"}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_handles_data_modification_without_legacy():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for data modification rule")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())
    result = await recognizer.recognize(
        "把 DIE-03 的材质改为 S136",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14c",
        db_session="db",
    )

    assert result.intent_type == "DATA_MODIFICATION"
    assert result.parameters == {}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_treats_single_letter_code_as_history_based_query():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for machining-code query")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())
    result = await recognizer.recognize(
        "L的线长是多少？",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14d",
        db_session="db",
    )

    assert result.intent_type == "QUERY_DETAILS"
    assert result.parameters == {"query_type": "wire"}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_handles_wire_base_and_auto_material_without_legacy():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for stable query-type rules")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())

    wire_base_result = await recognizer.recognize(
        "DIE-03 的线割基础费怎么算的？",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14e",
        db_session="db",
    )
    auto_material_result = await recognizer.recognize(
        "DIE-03 是自找料吗？",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14f",
        db_session="db",
    )

    assert wire_base_result.intent_type == "QUERY_DETAILS"
    assert wire_base_result.parameters == {"subgraph_id": "DIE-03", "query_type": "wire_base"}
    assert auto_material_result.intent_type == "QUERY_DETAILS"
    assert auto_material_result.parameters == {"subgraph_id": "DIE-03", "query_type": "add_auto_material"}


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_handles_nc_base_and_standard_without_legacy():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _ExplodingFallbackRecognizer:
        async def recognize(self, *args, **kwargs):
            raise AssertionError("fallback should not be used for stable nc/standard rules")

        async def close(self):
            return None

    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=_ExplodingFallbackRecognizer())

    nc_base_result = await recognizer.recognize(
        "DIE-03 的NC基本时间是多少？",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14g",
        db_session="db",
    )
    standard_result = await recognizer.recognize(
        "DIE-03 的标准基本费怎么算的？",
        {"raw_data": {"subgraphs": [{"subgraph_id": "uuid_DIE-03"}]}},
        job_id="job-14h",
        db_session="db",
    )

    assert nc_base_result.intent_type == "QUERY_DETAILS"
    assert nc_base_result.parameters == {"subgraph_id": "DIE-03", "query_type": "nc_base"}
    assert standard_result.intent_type == "QUERY_DETAILS"
    assert standard_result.parameters == {"subgraph_id": "DIE-03", "query_type": "standard"}


def test_src_review_action_handler_registry_keeps_simple_handlers_in_src():
    module = importlib.import_module("mold_cost.infrastructure.review.action_handler_runtime")

    registry = module.SrcReviewActionHandlerRegistry()
    registry.ensure_initialized()

    data_handler = registry.get_handler("DATA_MODIFICATION")
    feature_handler = registry.get_handler("FEATURE_RECOGNITION")
    chat_handler = registry.get_handler("GENERAL_CHAT")
    price_handler = registry.get_handler("PRICE_CALCULATION")
    query_handler = registry.get_handler("QUERY_DETAILS")
    weight_handler = registry.get_handler("WEIGHT_PRICE_CALCULATION")
    weight_query_handler = registry.get_handler("WEIGHT_PRICE_QUERY")

    assert data_handler.__class__.__name__ == "DataModificationReviewActionHandler"
    assert feature_handler.__class__.__name__ == "FeatureRecognitionReviewActionHandler"
    assert chat_handler.__class__.__name__ == "GeneralChatReviewActionHandler"
    assert price_handler.__class__.__name__ == "PriceCalculationReviewActionHandler"
    assert query_handler.__class__.__name__ == "QueryDetailsReviewActionHandler"
    assert weight_handler.__class__.__name__ == "WeightPriceCalculationReviewActionHandler"
    assert weight_query_handler.__class__.__name__ == "WeightPriceQueryReviewActionHandler"


def test_src_review_action_handler_registry_falls_back_to_legacy_for_complex_intents():
    module = importlib.import_module("mold_cost.infrastructure.review.action_handler_runtime")

    registry = module.SrcReviewActionHandlerRegistry()

    assert registry.get_handler("UNKNOWN") is None
    assert "ActionHandlerFactory" not in open(module.__file__, "r", encoding="utf-8").read()


@pytest.mark.asyncio
async def test_src_review_price_handler_saves_pending_action_via_src_store():
    module = importlib.import_module("mold_cost.infrastructure.review.review_action_handlers")

    class _FakePendingActionStore:
        def __init__(self):
            self.saved: list[tuple[str, dict, int]] = []

        async def save(self, job_id: str, payload: dict, *, ex: int = 3600):
            self.saved.append((job_id, payload, ex))

    pending_store = _FakePendingActionStore()
    handler = module.PriceCalculationReviewActionHandler(pending_action_store=pending_store)
    intent_result = SimpleNamespace(
        parameters={"subgraph_ids": ["DIE-03"]},
        raw_message="重新计算 DIE-03 的价格",
    )
    context = {
        "raw_data": {
            "subgraphs": [
                {"subgraph_id": "uuid_DIE-03"},
                {"subgraph_id": "uuid_DIE-05"},
            ]
        }
    }

    result = await handler.handle(intent_result, "job-10", context, db_session="db")

    assert result.status == "ok"
    assert result.requires_confirmation is True
    assert "DIE-03" in result.message
    assert pending_store.saved == [
        (
            "job-10",
            {
                "action_type": "PRICE_CALCULATION",
                "api_params": {
                    "job_id": "job-10",
                    "subgraph_ids": ["uuid_DIE-03"],
                    "options": {"force_recalculate": True, "skip_search": False},
                },
                "subgraph_ids": ["uuid_DIE-03"],
            },
            3600,
        )
    ]


@pytest.mark.asyncio
async def test_src_review_feature_handler_supports_concept_keyword_matching():
    module = importlib.import_module("mold_cost.infrastructure.review.review_action_handlers")

    class _FakePendingActionStore:
        def __init__(self):
            self.saved: list[tuple[str, dict, int]] = []

        async def save(self, job_id: str, payload: dict, *, ex: int = 3600):
            self.saved.append((job_id, payload, ex))

    pending_store = _FakePendingActionStore()
    handler = module.FeatureRecognitionReviewActionHandler(pending_action_store=pending_store)
    intent_result = SimpleNamespace(
        parameters={"keyword": "模架"},
        raw_message="重新识别模架",
    )
    context = {
        "display_view": [
            {"part_name": "上模座", "_source": {"subgraph_id": "uuid_UP-01"}},
            {"part_name": "托板", "_source": {"subgraph_id": "uuid_TP-01"}},
            {"part_name": "镶件", "_source": {"subgraph_id": "uuid_INS-01"}},
        ]
    }

    result = await handler.handle(intent_result, "job-11", context, db_session=None)

    assert result.status == "ok"
    assert result.data["subgraph_ids"] == ["uuid_UP-01", "uuid_TP-01"]
    assert pending_store.saved[0][1]["subgraph_ids"] == ["uuid_UP-01", "uuid_TP-01"]


@pytest.mark.asyncio
async def test_src_review_general_chat_handler_uses_src_chat_executor():
    module = importlib.import_module("mold_cost.infrastructure.review.review_action_handlers")

    class _FakeChatExecutor:
        async def chat(self, job_id: str, message: str, history: list[dict], current_data: dict | None):
            assert job_id == "job-12"
            assert message == "这个系统能做什么？"
            assert history == []
            assert current_data == {"subgraphs": [{"subgraph_id": "sg-1"}]}
            return "可以继续审核、识别特征和重新计价。"

    handler = module.GeneralChatReviewActionHandler(chat_executor=_FakeChatExecutor())
    intent_result = SimpleNamespace(raw_message="这个系统能做什么？", parameters={})

    result = await handler.handle(
        intent_result=intent_result,
        job_id="job-12",
        context={"raw_data": {"subgraphs": [{"subgraph_id": "sg-1"}]}},
        db_session=None,
    )

    assert result.status == "ok"
    assert result.requires_confirmation is False
    assert result.message == "可以继续审核、识别特征和重新计价。"


@pytest.mark.asyncio
async def test_src_data_modification_handler_filters_to_recent_subgraph_and_saves_pending_action():
    module = importlib.import_module("mold_cost.infrastructure.review.data_modification_review_handler")

    class _FakeNlpParser:
        async def parse(self, message: str, context: dict):
            assert message == "材质改为 toolox33"
            assert context["db_session"] == "db"
            return [
                {"table": "subgraphs", "id": "sg-up", "field": "material", "value": "toolox33"},
                {"table": "subgraphs", "id": "sg-die", "field": "material", "value": "toolox33"},
            ]

    class _FakeChatHistoryRepository:
        def __init__(self):
            self.calls: list[tuple[object, str, int]] = []

        async def get_recent_session_history(self, db_session, session_id: str, limit: int = 10):
            self.calls.append((db_session, session_id, limit))
            return [
                {"role": "assistant", "content": "上一轮我们在看 DIE-03 的材质。"},
                {"role": "user", "content": "它改一下"},
            ]

    class _FakeValidator:
        @staticmethod
        def validate_changes(changes, raw_data):
            assert len(changes) == 1
            assert changes[0]["id"] == "sg-die"
            assert raw_data["subgraphs"][0]["job_id"] == "job-19"
            return SimpleNamespace(is_valid=True, error_message="", warnings=[])

    class _FakeDisplayViewBuilder:
        @staticmethod
        def build_display_view(raw_data):
            return [{"rows": len(raw_data["subgraphs"])}]

    class _FakePendingActionStore:
        def __init__(self):
            self.saved: list[tuple[str, dict, int]] = []

        async def save(self, job_id: str, payload: dict, *, ex: int = 3600):
            self.saved.append((job_id, payload, ex))

    pending_store = _FakePendingActionStore()
    history_repository = _FakeChatHistoryRepository()
    handler = module.DataModificationReviewActionHandler(
        pending_action_store=pending_store,
        nlp_parser=_FakeNlpParser(),
        chat_history_repository=history_repository,
        validator=_FakeValidator(),
        display_view_builder=_FakeDisplayViewBuilder(),
        use_chat_history=True,
    )

    context = {
        "user_id": "u-19",
        "raw_data": {
            "subgraphs": [
                {"job_id": "job-19", "subgraph_id": "sg-up", "material": "P20"},
                {"job_id": "job-19", "subgraph_id": "sg-die", "material": "NAK80"},
            ]
        },
        "display_view": [
            {"part_code": "UP-01", "_source": {"subgraph_id": "sg-up"}},
            {"part_code": "DIE-03", "_source": {"subgraph_id": "sg-die"}},
        ],
    }

    result = await handler.handle(
        intent_result=SimpleNamespace(raw_message="材质改为 toolox33", parameters={}),
        job_id="job-19",
        context=context,
        db_session="db",
    )

    assert history_repository.calls == [("db", "job-19", 10)]
    assert result.status == "ok"
    assert result.requires_confirmation is True
    assert result.data["parsed_changes"] == [
        {"table": "subgraphs", "id": "sg-die", "field": "material", "value": "toolox33"}
    ]
    assert result.data["modified_data"]["subgraphs"][1]["material"] == "T00L0X33"
    assert pending_store.saved[0][1]["changes"] == result.data["parsed_changes"]


@pytest.mark.asyncio
async def test_src_data_modification_handler_keeps_explicit_batch_changes_without_history_filter():
    module = importlib.import_module("mold_cost.infrastructure.review.data_modification_review_handler")

    class _FakeNlpParser:
        async def parse(self, message: str, context: dict):
            return [{"table": "subgraphs", "id": "sg-1", "field": "material", "value": "S136"}]

    class _FakeValidator:
        @staticmethod
        def validate_changes(changes, raw_data):
            return SimpleNamespace(is_valid=True, error_message="", warnings=[])

    class _FakeDisplayViewBuilder:
        @staticmethod
        def build_display_view(raw_data):
            return raw_data["subgraphs"]

    class _FakePendingActionStore:
        async def save(self, job_id: str, payload: dict, *, ex: int = 3600):
            return None

    class _ExplodingChatHistoryRepository:
        async def get_recent_session_history(self, db_session, session_id: str, limit: int = 10):
            raise AssertionError("history should not be used when only one target is modified")

    handler = module.DataModificationReviewActionHandler(
        pending_action_store=_FakePendingActionStore(),
        nlp_parser=_FakeNlpParser(),
        chat_history_repository=_ExplodingChatHistoryRepository(),
        validator=_FakeValidator(),
        display_view_builder=_FakeDisplayViewBuilder(),
        use_chat_history=True,
    )

    result = await handler.handle(
        intent_result=SimpleNamespace(raw_message="sg-1 材质改为 S136", parameters={}),
        job_id="job-20",
        context={"raw_data": {"subgraphs": [{"job_id": "job-20", "subgraph_id": "sg-1", "material": "P20"}]}},
        db_session="db",
    )

    assert result.status == "ok"
    assert result.data["modified_data"]["subgraphs"][0]["material"] == "S136"


@pytest.mark.asyncio
async def test_src_query_details_handler_uses_history_inference_and_returns_query_type_details():
    module = importlib.import_module("mold_cost.infrastructure.review.query_details_review_handler")

    class _FakeChatHistoryRepository:
        def __init__(self):
            self.calls: list[tuple[object, str, int]] = []

        async def get_recent_session_history(self, db_session, session_id: str, limit: int = 50):
            self.calls.append((db_session, session_id, limit))
            return [
                {"role": "assistant", "content": "刚才我们核对了 DIE-03 的 NC 明细。"},
                {"role": "user", "content": "那它怎么算的？"},
            ]

    async def _fake_query_calculation_detail(**kwargs):
        assert kwargs["subgraph_id"] == "DIE-03"
        return SimpleNamespace(
            calculation_steps=[
                {
                    "category": "nc_z",
                    "steps": [
                        {
                            "step": "Z面加工",
                            "formula": "30 / 60",
                            "total_minutes": 30,
                            "nc_z_time": 0.5,
                        }
                    ],
                },
                {
                    "category": "nc_total",
                    "steps": [
                        {
                            "step": "汇总NC费用",
                            "formula": "0.5 * 120",
                            "total_hours": 0.5,
                            "total_cost": 60,
                        }
                    ],
                },
            ],
            processing_instructions=[{"code": "NC"}],
        )

    history_repository = _FakeChatHistoryRepository()
    handler = module.QueryDetailsReviewActionHandler(
        chat_history_repository=history_repository,
        use_chat_history=True,
    )
    handler._query_calculation_detail = _fake_query_calculation_detail

    result = await handler.handle(
        intent_result=SimpleNamespace(parameters={"query_type": "nc"}, raw_message="那它怎么算的？"),
        job_id="job-17",
        context={},
        db_session="db",
    )

    assert history_repository.calls == [("db", "job-17", 50)]
    assert result.status == "ok"
    assert result.data["subgraph_id"] == "DIE-03"
    assert result.data["query_type"] == "nc"
    assert "DIE-03 的NC相关计算详情" in result.message
    assert "【NC Z面时间】" in result.message
    assert "【NC总费用计算】" in result.message


@pytest.mark.asyncio
async def test_src_query_details_handler_formats_specific_material_category():
    module = importlib.import_module("mold_cost.infrastructure.review.query_details_review_handler")

    async def _fake_query_calculation_detail(**kwargs):
        return SimpleNamespace(
            calculation_steps=[
                {
                    "category": "material",
                    "steps": [
                        {
                            "step": "匹配材料单价",
                            "material": "S136",
                            "matched_sub_category": "塑胶模仁钢",
                            "material_cost": 88.5,
                        }
                    ],
                }
            ],
            processing_instructions=None,
        )

    handler = module.QueryDetailsReviewActionHandler(use_chat_history=False)
    handler._query_calculation_detail = _fake_query_calculation_detail

    result = await handler.handle(
        intent_result=SimpleNamespace(parameters={"subgraph_id": "UP-01", "query_type": "material"}, raw_message="UP-01 材料费怎么算"),
        job_id="job-18",
        context={},
        db_session="db",
    )

    assert result.status == "ok"
    assert "UP-01 的材料费计算详情" in result.message
    assert "材料名称: S136" in result.message
    assert "材料费(元): 88.5" in result.message


@pytest.mark.asyncio
async def test_src_weight_price_query_handler_uses_chat_history_inference():
    module = importlib.import_module("mold_cost.infrastructure.review.weight_price_query_handler")

    class _FakeChatHistoryRepository:
        def __init__(self):
            self.calls: list[tuple[object, str, int]] = []

        async def get_recent_session_history(self, db_session, session_id: str, limit: int = 50):
            self.calls.append((db_session, session_id, limit))
            return [
                {"role": "assistant", "content": "上一轮我们看的是 UP-08 的结果。"},
                {"role": "user", "content": "那它按重量怎么算？"},
            ]

    async def _fake_query_weight_price_detail(**kwargs):
        assert kwargs["subgraph_id"] == "UP-08"
        return SimpleNamespace(
            weight_price_steps=[
                {
                    "category": "weight_price",
                    "steps": [
                        {
                            "step": "获取零件信息",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 20,
                            "material": "S136",
                        },
                        {
                            "step": "计算加权价格",
                            "formula": "weight * rule_price",
                            "weight": 1.23,
                            "rule_price": 18.5,
                            "weight_price": 22.76,
                        },
                    ],
                }
            ]
        )

    history_repository = _FakeChatHistoryRepository()
    handler = module.WeightPriceQueryReviewActionHandler(
        chat_history_repository=history_repository,
        use_chat_history=True,
    )
    handler._query_weight_price_detail = _fake_query_weight_price_detail

    result = await handler.handle(
        intent_result=SimpleNamespace(parameters={}, raw_message="那它按重量怎么算？"),
        job_id="job-15",
        context={"raw_data": {"subgraphs": [{"subgraph_id": "uuid_UP-08"}]}},
        db_session="db",
    )

    assert history_repository.calls == [("db", "job-15", 50)]
    assert result.status == "ok"
    assert result.requires_confirmation is False
    assert result.data["subgraph_id"] == "UP-08"
    assert "UP-08 的按重量计算详情" in result.message
    assert "规则单价(元/kg): 18.5" in result.message


@pytest.mark.asyncio
async def test_src_weight_price_query_handler_returns_empty_message_when_steps_missing():
    module = importlib.import_module("mold_cost.infrastructure.review.weight_price_query_handler")

    class _FakeChatHistoryRepository:
        async def get_recent_session_history(self, db_session, session_id: str, limit: int = 50):
            return []

    async def _fake_query_weight_price_detail(**kwargs):
        return SimpleNamespace(weight_price_steps=None)

    handler = module.WeightPriceQueryReviewActionHandler(
        chat_history_repository=_FakeChatHistoryRepository(),
        use_chat_history=False,
    )
    handler._query_weight_price_detail = _fake_query_weight_price_detail

    result = await handler.handle(
        intent_result=SimpleNamespace(parameters={"subgraph_id": "DIE-03"}, raw_message="DIE-03 按重量怎么算"),
        job_id="job-16",
        context={},
        db_session="db",
    )

    assert result.status == "ok"
    assert result.message == "DIE-03 暂无按重量计算的详情数据。"


@pytest.mark.asyncio
async def test_review_confirmation_executor_applies_data_modification_and_clears_pending_action():
    module = importlib.import_module("mold_cost.infrastructure.review.confirmation_executor")

    class _FakePendingActionStore:
        def __init__(self):
            self.deleted: list[str] = []

        async def load(self, job_id: str):
            assert job_id == "job-7"
            return {
                "action_type": "DATA_MODIFICATION",
                "changes": [{"field": "material"}],
                "modified_data": {
                    "subgraphs": [
                        {
                            "subgraph_id": "sg-1",
                            "modified_at": "2026-04-05T10:00:00",
                        }
                    ]
                },
            }

        async def delete(self, job_id: str):
            self.deleted.append(job_id)

    class _FakeDbSession:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            self.rollbacks += 1

    fake_repo = _FakeReviewRepository()
    pending_store = _FakePendingActionStore()
    db_session = _FakeDbSession()

    executor = module.ReviewConfirmationExecutorAdapter(
        pending_action_store=pending_store,
        review_repository=fake_repo,
    )

    result = await executor.handle_confirmation(job_id="job-7", user_id="u-1", db_session=db_session)

    assert result == {
        "status": "ok",
        "message": "数据修改已保存",
        "data": {
            "action_type": "DATA_MODIFICATION",
            "changes_count": 1,
        },
    }
    assert pending_store.deleted == ["job-7"]
    assert db_session.commits == 1
    assert db_session.rollbacks == 0
    assert fake_repo.update_calls[0][1] == "job-7"
    assert fake_repo.update_calls[0][2]["subgraphs"][0]["modified_at"].isoformat() == "2026-04-05T10:00:00"


@pytest.mark.asyncio
async def test_review_confirmation_executor_triggers_feature_api_and_clears_pending_action():
    module = importlib.import_module("mold_cost.infrastructure.review.confirmation_executor")

    class _FakePendingActionStore:
        def __init__(self):
            self.deleted: list[str] = []

        async def load(self, job_id: str):
            assert job_id == "job-8"
            return {
                "action_type": "FEATURE_RECOGNITION",
                "api_params": {"job_id": "job-8", "subgraph_ids": ["sg-1"]},
            }

        async def delete(self, job_id: str):
            self.deleted.append(job_id)

    requests: list[tuple[str, dict]] = []

    async def _fake_request_executor(url: str, payload: dict):
        requests.append((url, payload))
        return {"data": {"task_id": "task-1"}}

    pending_store = _FakePendingActionStore()
    executor = module.ReviewConfirmationExecutorAdapter(
        pending_action_store=pending_store,
        request_executor=_fake_request_executor,
    )

    result = await executor.handle_confirmation(job_id="job-8", user_id="u-1", db_session="db")

    assert result == {
        "status": "ok",
        "message": "特征识别任务已提交",
        "data": {
            "action_type": "FEATURE_RECOGNITION",
            "task_id": "task-1",
            "subgraph_ids": ["sg-1"],
            "api_response": {"data": {"task_id": "task-1"}},
        },
    }
    assert requests == [
        (
            importlib.import_module("mold_cost.infrastructure.review.confirmation_executor").settings.FEATURE_REPROCESS_API_URL,
            {"job_id": "job-8", "subgraph_ids": ["sg-1"]},
        )
    ]
    assert pending_store.deleted == ["job-8"]


@pytest.mark.asyncio
async def test_review_notifier_uses_message_persistence_adapter(monkeypatch):
    module = importlib.import_module("mold_cost.domain.review.services.review_notifier")

    published_messages: list[tuple[str, str]] = []
    persisted_messages: list[tuple[str, dict, object]] = []

    class _FakeRedisClient:
        async def publish(self, channel: str, payload: str):
            published_messages.append((channel, payload))

    class _FakeMessagePersistence:
        async def push_and_persist(self, *, job_id: str, ws_message: dict, db_session=None, ws_manager=None):
            persisted_messages.append((job_id, ws_message, db_session))

    monkeypatch.setattr(module, "redis_client", _FakeRedisClient())
    monkeypatch.setattr(module, "get_message_persistence_adapter", lambda: _FakeMessagePersistence())

    notifier = module.InteractionAgentReviewNotifier()
    await notifier.push_system_message("job-9", "ready", db_session="db")

    assert published_messages and published_messages[0][0] == "job:job-9:review"
    assert len(persisted_messages) == 1
    assert persisted_messages[0][0] == "job-9"
    assert persisted_messages[0][1]["type"] == "system_message"
    assert persisted_messages[0][1]["message"] == "ready"
    assert persisted_messages[0][2] == "db"
