"""Tests for the src-owned CAD split runtime boundary."""

from __future__ import annotations

import asyncio

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_split_runtime_initializes_managers_before_processing():
    from mold_cost.infrastructure.cad.cad_split_runtime import run_cad_split

    calls: list[tuple[str, object]] = []
    fake_minio_client = object()

    async def _fake_chaitu_process(*, dwg_url, job_id, minio_client=None):
        calls.append(("process", (dwg_url, job_id, minio_client)))
        return {"status": "ok", "data": {"job_id": job_id}}

    def _fake_init_managers(*, minio_client=None):
        calls.append(("init", minio_client))

    result = asyncio.run(
        run_cad_split(
            dwg_url="bucket/demo.dwg",
            job_id="job-1",
            minio_client=fake_minio_client,
            load_entrypoints=lambda: (_fake_chaitu_process, _fake_init_managers),
        )
    )

    assert result == {"status": "ok", "data": {"job_id": "job-1"}}
    assert calls == [
        ("init", fake_minio_client),
        ("process", ("bucket/demo.dwg", "job-1", fake_minio_client)),
    ]


def test_cad_split_gateway_uses_src_runtime(monkeypatch):
    from mold_cost.infrastructure.cad.legacy_cad_split_gateway import LegacyCadSplitGateway

    calls = []
    fake_minio_client = object()

    async def _fake_run_cad_split(*, dwg_url, job_id, minio_client, load_entrypoints):
        calls.append(
            {
                "dwg_url": dwg_url,
                "job_id": job_id,
                "minio_client": minio_client,
                "load_entrypoints": load_entrypoints,
            }
        )
        return {"status": "ok", "message": "runtime"}

    monkeypatch.setattr(
        "mold_cost.infrastructure.cad.legacy_cad_split_gateway.run_cad_split",
        _fake_run_cad_split,
    )

    gateway = LegacyCadSplitGateway()
    result = asyncio.run(gateway.split("bucket/demo.dwg", "job-2", fake_minio_client))

    assert result == {"status": "ok", "message": "runtime"}
    assert len(calls) == 1
    assert calls[0]["dwg_url"] == "bucket/demo.dwg"
    assert calls[0]["job_id"] == "job-2"
    assert calls[0]["minio_client"] is fake_minio_client
    assert callable(calls[0]["load_entrypoints"])
    assert calls[0]["load_entrypoints"] is gateway._load_legacy_entrypoints


def test_cad_pool_database_manager_bridge_is_lazy(monkeypatch):
    from mold_cost.infrastructure.db import cad_pool

    class _FakeDatabaseManager:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    monkeypatch.setattr(cad_pool, "_load_database_manager", lambda: _FakeDatabaseManager)

    manager = cad_pool.DatabaseManager("host", 5432, "db", "user", "pwd")

    assert isinstance(manager, _FakeDatabaseManager)
    assert manager.args == ("host", 5432, "db", "user", "pwd")


def test_legacy_material_line_integrator_wrapper_points_to_src_runtime():
    wrapper_path = "d:\\workspace\\project\\python\\mold3.0\\mold_cost_\\scripts\\cad_chaitu\\material_line_integrator.py"
    with open(wrapper_path, "r", encoding="utf-8") as file:
        content = file.read()

    assert "from mold_cost.infrastructure.cad.material_line_integrator import MaterialLineIntegrator" in content


def test_legacy_cad_system_wrapper_points_to_src_runtime():
    wrapper_path = "d:\\workspace\\project\\python\\mold3.0\\mold_cost_\\scripts\\cad_chaitu\\cad_system.py"
    with open(wrapper_path, "r", encoding="utf-8") as file:
        content = file.read()

    assert "from mold_cost.infrastructure.cad.cad_system import CADAnalysisSystem" in content


def test_legacy_number_extractor_wrapper_points_to_src_runtime():
    wrapper_path = "d:\\workspace\\project\\python\\mold3.0\\mold_cost_\\scripts\\cad_chaitu\\number_extractor.py"
    with open(wrapper_path, "r", encoding="utf-8") as file:
        content = file.read()

    assert (
        "from mold_cost.infrastructure.cad.number_extractor import ProfessionalDrawingNumberExtractor"
        in content
    )


def test_legacy_text_processor_wrapper_points_to_src_runtime():
    wrapper_path = "d:\\workspace\\project\\python\\mold3.0\\mold_cost_\\scripts\\cad_chaitu\\text_processor.py"
    with open(wrapper_path, "r", encoding="utf-8") as file:
        content = file.read()

    assert "from mold_cost.infrastructure.cad.text_processor import IntelligentTextProcessor" in content


def test_legacy_cutting_detector_wrapper_points_to_src_runtime():
    wrapper_path = "d:\\workspace\\project\\python\\mold3.0\\mold_cost_\\scripts\\cad_chaitu\\cutting_detector.py"
    with open(wrapper_path, "r", encoding="utf-8") as file:
        content = file.read()

    assert "from mold_cost.infrastructure.cad.cutting_detector import RelaxedCuttingDetector" in content
