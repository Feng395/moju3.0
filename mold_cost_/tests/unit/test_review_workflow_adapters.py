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
async def test_src_review_intent_recognizer_falls_back_for_complex_intents():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _FallbackRecognizer:
        def __init__(self):
            self.calls: list[tuple[str, str, object]] = []

        async def recognize(self, message, context, job_id=None, db_session=None):
            self.calls.append((message, job_id, db_session))
            return SimpleNamespace(intent_type="QUERY_DETAILS", confidence=0.66, parameters={"subgraph_id": "sg-1"})

        async def close(self):
            return None

    fallback = _FallbackRecognizer()
    recognizer = module.SrcReviewIntentRecognizer(fallback_recognizer=fallback)

    result = await recognizer.recognize(
        "为什么这个零件这么贵？",
        {"raw_data": {"subgraphs": [{"subgraph_id": "sg-1"}]}},
        job_id="job-14",
        db_session="db",
    )

    assert result.intent_type == "QUERY_DETAILS"
    assert fallback.calls == [("为什么这个零件这么贵？", "job-14", "db")]


@pytest.mark.asyncio
async def test_src_review_intent_recognizer_factory_wraps_legacy_fallback():
    module = importlib.import_module("mold_cost.infrastructure.review.intent_recognizer_runtime")

    class _FallbackFactory:
        def create(self):
            return SimpleNamespace(
                recognize=lambda *args, **kwargs: None,
                close=lambda: None,
            )

    factory = module.SrcReviewIntentRecognizerFactory(fallback_factory=_FallbackFactory())
    recognizer = factory.create()

    assert recognizer.__class__.__name__ == "SrcReviewIntentRecognizer"
    assert recognizer._fallback_recognizer is not None


def test_src_review_action_handler_registry_keeps_simple_handlers_in_src():
    module = importlib.import_module("mold_cost.infrastructure.review.action_handler_runtime")

    registry = module.SrcReviewActionHandlerRegistry()
    registry.ensure_initialized()

    feature_handler = registry.get_handler("FEATURE_RECOGNITION")
    chat_handler = registry.get_handler("GENERAL_CHAT")
    price_handler = registry.get_handler("PRICE_CALCULATION")
    weight_handler = registry.get_handler("WEIGHT_PRICE_CALCULATION")
    weight_query_handler = registry.get_handler("WEIGHT_PRICE_QUERY")

    assert feature_handler.__class__.__name__ == "FeatureRecognitionReviewActionHandler"
    assert chat_handler.__class__.__name__ == "GeneralChatReviewActionHandler"
    assert price_handler.__class__.__name__ == "PriceCalculationReviewActionHandler"
    assert weight_handler.__class__.__name__ == "WeightPriceCalculationReviewActionHandler"
    assert weight_query_handler.__class__.__name__ == "WeightPriceQueryReviewActionHandler"


def test_src_review_action_handler_registry_falls_back_to_legacy_for_complex_intents():
    module = importlib.import_module("mold_cost.infrastructure.review.action_handler_runtime")

    registry = module.SrcReviewActionHandlerRegistry()
    data_handler = registry.get_handler("DATA_MODIFICATION")
    query_handler = registry.get_handler("QUERY_DETAILS")

    assert data_handler.__class__.__name__ == "DataModificationHandler"
    assert query_handler.__class__.__name__ == "QueryDetailsHandler"
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
