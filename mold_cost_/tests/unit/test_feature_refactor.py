"""特征识别重构相关测试。"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_feature_recognition_service_wraps_gateway():
    """验证领域服务会把调用统一转发到 gateway。"""
    from mold_cost.domain.features.services.recognition_service import LegacyFeatureRecognitionService

    calls: list[tuple] = []

    class StubGateway:
        @staticmethod
        def batch_recognize(job_id, subgraph_id=None, progress_callback=None):
            calls.append(("batch", job_id, subgraph_id, progress_callback))
            return {"success": True, "data": {"job_id": job_id, "subgraph_id": subgraph_id}}

        @staticmethod
        def analyze_dxf(dxf_path):
            calls.append(("analyze", dxf_path))
            return {"file": dxf_path}

        @staticmethod
        def get_subgraphs(job_id, subgraph_id=None):
            calls.append(("get_subgraphs", job_id, subgraph_id))
            return [{"job_id": job_id, "subgraph_id": subgraph_id}]

        @staticmethod
        def save_features(subgraph_id, job_id, features):
            calls.append(("save", subgraph_id, job_id, features))
            return True

        @staticmethod
        def upload_feature_database(database, minio_path):
            calls.append(("upload", minio_path, database))

    service = LegacyFeatureRecognitionService(StubGateway())

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


def test_reprocess_features_use_case_executes_with_stubbed_service():
    """验证后台执行体会调用领域特征服务。"""
    from mold_cost.application.use_cases.features import ReprocessFeaturesUseCase

    payloads: list[dict] = []

    class StubFeatureService:
        async def reprocess(self, job_id, subgraph_ids, force_reprocess):
            payloads.append(
                {
                    "job_id": job_id,
                    "subgraph_ids": subgraph_ids,
                    "force_reprocess": force_reprocess,
                }
            )
            return {"status": "ok", "total": len(subgraph_ids)}

    use_case = ReprocessFeaturesUseCase(feature_service=StubFeatureService())

    result = asyncio.run(use_case._execute("job-3", ["sub-a"], False))

    assert result == {"status": "ok", "total": 1}
    assert payloads == [
        {
            "job_id": "job-3",
            "subgraph_ids": ["sub-a"],
            "force_reprocess": False,
        }
    ]


def test_features_router_reprocess_entry_uses_use_case(monkeypatch):
    """验证 gateway feature 入口会经由应用用例收口。"""
    from api_gateway.routers.features import router

    calls: list[dict] = []

    async def fake_submit(self, job_id, subgraph_ids, force_reprocess):
        calls.append(
            {
                "job_id": job_id,
                "subgraph_ids": subgraph_ids,
                "force_reprocess": force_reprocess,
            }
        )
        return {
            "status": "accepted",
            "message": "ok",
            "job_id": job_id,
            "subgraph_count": len(subgraph_ids),
        }

    monkeypatch.setattr("api_gateway.routers.features.ReprocessFeaturesUseCase.submit", fake_submit)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        "/api/features/reprocess",
        json={
            "job_id": "job-router",
            "subgraph_ids": ["sub-1", "sub-2"],
            "force_reprocess": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-router"
    assert calls == [
        {
            "job_id": "job-router",
            "subgraph_ids": ["sub-1", "sub-2"],
            "force_reprocess": False,
        }
    ]


def test_legacy_feature_upload_entry_uses_domain_service(monkeypatch):
    """验证 legacy feature 上传入口会经由领域服务收口。"""
    import mold_cost.domain.features.services as feature_services
    from mold_cost.interfaces.api.legacy_cad_api import create_app

    calls: list[dict] = []

    class StubFeatureService:
        def upload_feature_database(self, csv_folder, minio_path=None):
            calls.append({"csv_folder": csv_folder, "minio_path": minio_path})
            return {
                "success": True,
                "message": "上传成功，共 1 条记录",
                "minio_path": minio_path or "slider/feature_database.json",
                "csv_source": f"{csv_folder}\\report.csv",
            }

    monkeypatch.setattr(feature_services, "feature_recognition_service", StubFeatureService())

    client = TestClient(create_app())
    response = client.post(
        "/api/feature-recognition/upload-feature-db",
        json={
            "csv_folder": r"D:\demo\split_result",
            "minio_path": "slider/custom.json",
        },
    )

    assert response.status_code == 200
    assert response.json()["minio_path"] == "slider/custom.json"
    assert calls == [
        {
            "csv_folder": r"D:\demo\split_result",
            "minio_path": "slider/custom.json",
        }
    ]


def test_feature_gateway_analyze_dxf_uses_src_runtime(monkeypatch):
    from mold_cost.infrastructure.cad.legacy_feature_recognition_gateway import LegacyFeatureRecognitionGateway

    calls: list[str] = []

    def _fake_analyze_dxf_features(dxf_path: str):
        calls.append(dxf_path)
        return {"path": dxf_path, "source": "src-runtime"}

    monkeypatch.setattr(
        "mold_cost.infrastructure.cad.legacy_feature_recognition_gateway.analyze_dxf_features",
        _fake_analyze_dxf_features,
    )

    gateway = LegacyFeatureRecognitionGateway()
    result = gateway.analyze_dxf("demo-runtime.dxf")

    assert result == {"path": "demo-runtime.dxf", "source": "src-runtime"}
    assert calls == ["demo-runtime.dxf"]


def test_feature_gateway_batch_recognize_uses_src_runtime(monkeypatch):
    import sys
    import types

    from mold_cost.infrastructure.cad.legacy_feature_recognition_gateway import (
        LegacyFeatureRecognitionGateway,
        settings,
    )

    calls = []
    fake_minio_client = object()

    def _fake_batch_feature_recognition(job_id, subgraph_id=None, progress_callback=None, **kwargs):
        calls.append(
            {
                "job_id": job_id,
                "subgraph_id": subgraph_id,
                "progress_callback": progress_callback,
                "kwargs": kwargs,
            }
        )
        return {"success": True, "data": {"total": 0, "success_count": 0, "failed_count": 0, "results": []}}

    monkeypatch.setattr(
        "mold_cost.infrastructure.cad.legacy_feature_recognition_gateway.batch_feature_recognition",
        _fake_batch_feature_recognition,
    )
    monkeypatch.setitem(
        sys.modules,
        "scripts.minio_client",
        types.SimpleNamespace(minio_client=fake_minio_client),
    )
    monkeypatch.setattr(
        "mold_cost.infrastructure.cad.legacy_feature_recognition_gateway.update_slider_red_face_data",
        "slider-updater",
    )

    gateway = LegacyFeatureRecognitionGateway()
    callback = lambda *args: None
    result = gateway.batch_recognize("job-batch", "sub-batch", callback)

    assert result["success"] is True
    assert len(calls) == 1
    captured = calls[0]
    assert captured["job_id"] == "job-batch"
    assert captured["subgraph_id"] == "sub-batch"
    assert captured["progress_callback"] is callback
    assert captured["kwargs"]["minio_client"] is fake_minio_client
    assert captured["kwargs"]["slider_red_face_updater"] == "slider-updater"
    assert captured["kwargs"]["get_subgraphs"].__self__ is gateway
    assert captured["kwargs"]["get_subgraphs"].__func__ is gateway.get_subgraphs.__func__
    assert captured["kwargs"]["save_features"].__self__ is gateway
    assert captured["kwargs"]["save_features"].__func__ is gateway.save_features.__func__
    assert captured["kwargs"]["db_config"] == {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "user": settings.DB_USER,
        "password": settings.DB_PASSWORD,
        "database": settings.DB_NAME,
    }
