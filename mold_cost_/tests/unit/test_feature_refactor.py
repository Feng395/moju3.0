"""特征识别重构相关测试。"""

from __future__ import annotations

import asyncio

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_feature_recognition_service_wraps_legacy_module(monkeypatch):
    """验证领域服务会把调用统一转发到 legacy 模块。"""
    from mold_cost.domain.features.services.recognition_service import LegacyFeatureRecognitionService

    calls: list[tuple] = []

    class StubLegacyModule:
        @staticmethod
        def batch_feature_recognition_process(job_id, subgraph_id=None, progress_callback=None):
            calls.append(("batch", job_id, subgraph_id, progress_callback))
            return {"success": True, "data": {"job_id": job_id, "subgraph_id": subgraph_id}}

        @staticmethod
        def analyze_dxf_features(dxf_path):
            calls.append(("analyze", dxf_path))
            return {"file": dxf_path}

        @staticmethod
        def get_subgraphs_from_db(job_id, subgraph_id=None):
            calls.append(("get_subgraphs", job_id, subgraph_id))
            return [{"job_id": job_id, "subgraph_id": subgraph_id}]

        @staticmethod
        def save_features_to_db(subgraph_id, job_id, features):
            calls.append(("save", subgraph_id, job_id, features))
            return True

    service = LegacyFeatureRecognitionService()
    monkeypatch.setattr(service, "_load_legacy_module", lambda: StubLegacyModule)

    callback = lambda *args: None
    assert service.batch_recognize("job-1", "sub-1", callback)["success"] is True
    assert service.analyze_dxf("demo.dxf") == {"file": "demo.dxf"}
    assert service.get_subgraphs("job-1", "sub-1") == [{"job_id": "job-1", "subgraph_id": "sub-1"}]
    assert service.save_features("sub-1", "job-1", {"x": 1}) is True

    assert calls[0][:3] == ("batch", "job-1", "sub-1")
    assert calls[1] == ("analyze", "demo.dxf")
    assert calls[2] == ("get_subgraphs", "job-1", "sub-1")
    assert calls[3] == ("save", "sub-1", "job-1", {"x": 1})


def test_reprocess_features_use_case_submits_background_task(monkeypatch):
    """验证应用层用例会创建后台任务并透传参数。"""
    from mold_cost.application.use_cases.features import ReprocessFeaturesUseCase

    created_tasks = []

    def fake_create_task(coro):
        created_tasks.append(coro)
        coro.close()
        return None

    monkeypatch.setattr("mold_cost.application.use_cases.features.asyncio.create_task", fake_create_task)

    use_case = ReprocessFeaturesUseCase()
    result = asyncio.run(use_case.submit("job-2", ["sub-1", "sub-2"], True))

    assert result == {
        "status": "accepted",
        "message": "特征识别任务已提交，请通过 WebSocket 监听进度",
        "job_id": "job-2",
        "subgraph_count": 2,
    }
    assert len(created_tasks) == 1


def test_reprocess_features_use_case_executes_with_stubbed_agent(monkeypatch):
    """验证后台执行体会调用 CAD agent 的批量识别接口。"""
    from mold_cost.application.use_cases.features import ReprocessFeaturesUseCase

    payloads: list[dict] = []

    class StubCadAgent:
        async def recognize_features_batch(self, payload):
            payloads.append(payload)
            return {"status": "ok", "total": len(payload["subgraph_ids"])}

    use_case = ReprocessFeaturesUseCase()
    monkeypatch.setattr(use_case, "_get_cad_agent", lambda: StubCadAgent())

    result = asyncio.run(use_case._execute("job-3", ["sub-a"], False))

    assert result == {"status": "ok", "total": 1}
    assert payloads == [
        {
            "job_id": "job-3",
            "subgraph_ids": ["sub-a"],
            "force_reprocess": False,
        }
    ]
