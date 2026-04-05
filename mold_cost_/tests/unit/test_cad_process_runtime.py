"""Tests for the src-owned CAD process runtime."""

from __future__ import annotations

import asyncio
from datetime import datetime

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_process_runtime_handles_full_pipeline():
    from mold_cost.infrastructure.cad import cad_process_runtime as runtime

    calls: list[tuple[str, object]] = []

    class _FakeAnalysisSystem:
        def clear_cache(self):
            calls.append(("clear_cache", None))

    async def _fake_export_xt_files(**kwargs):
        calls.append(("xt", kwargs))
        return {"SG-1": "xt/2026/04/job-1/P-001.x_t"}

    result = asyncio.run(
        runtime.run_cad_process_pipeline(
            job_id="job-1",
            temp_dxf="D:/temp/input.dxf",
            temp_dir="D:/temp/cad",
            minio_base_path="dxf/2026/04/job-1",
            source_filename="demo.dwg",
            minio_client="minio-client",
            db_manager="db-manager",
            storage_manager="storage-manager",
            analysis_system_factory=lambda: calls.append(("analysis_system_factory", None)) or _FakeAnalysisSystem(),
            material_line_available=True,
            integrator_factory="material-line-integrator",
            resolve_subgraph_lwt="resolve-lwt",
            save_debug_files="save-debug",
            export_xt_from_prt="legacy-xt-exporter",
            analyze_and_export=lambda **kwargs: calls.append(("analyze", kwargs))
        or {
            "success": True,
            "analysis_time": 1.2,
            "export_time": 2.3,
            "all_regions": [("SG-1", {"x": 1})],
            "region_info_list": [{"sub_code": "SG-1"}],
            "region_info_map": {"SG-1": {"region": {"x": 1}}},
            "failed_recognition_count": 0,
            "failed_export_count": 0,
            "export_files": [
                {
                    "sub_code": "SG-1",
                    "part_code": "P-001",
                    "local_path": "D:/temp/SG-1.dxf",
                    "minio_path": "dxf/2026/04/job-1/SG-1.dxf",
                }
            ],
        },
            process_material_lines_fn=lambda **kwargs: calls.append(("material", kwargs))
            or {"processed": True, "debug_output_dir": "D:/debug"},
            upload_split_files_fn=lambda **kwargs: calls.append(("upload", kwargs))
            or {"SG-1": {"success": True, "minio_path": "dxf/2026/04/job-1/SG-1.dxf"}},
            export_xt_files_fn=_fake_export_xt_files,
            persist_split_results_fn=lambda **kwargs: calls.append(("persist", kwargs))
            or {
                "result_files": [{"filename": "SG-1.dxf"}],
                "db_success_count": 1,
                "failed_upload_count": 0,
                "failed_db_count": 0,
            },
            now_factory=lambda: datetime(2026, 4, 5, 12, 30, 0),
        )
    )

    assert result["success"] is True
    assert result["result_files"] == [{"filename": "SG-1.dxf"}]
    assert result["db_success_count"] == 1
    assert result["failed_upload_count"] == 0
    assert [name for name, _payload in calls] == [
        "analysis_system_factory",
        "analyze",
        "material",
        "upload",
        "xt",
        "persist",
        "clear_cache",
    ]


def test_cad_process_runtime_returns_error_when_analysis_fails():
    from mold_cost.infrastructure.cad import cad_process_runtime as runtime

    result = asyncio.run(
        runtime.run_cad_process_pipeline(
            job_id="job-missing",
            temp_dxf="D:/temp/input.dxf",
            temp_dir="D:/temp/cad",
            minio_base_path="dxf/2026/04/job-missing",
            source_filename="demo.dwg",
            minio_client="minio-client",
            db_manager="db-manager",
            storage_manager="storage-manager",
            analysis_system_factory=lambda: type("FakeAnalysisSystem", (), {"clear_cache": lambda self: None})(),
            material_line_available=True,
            integrator_factory="material-line-integrator",
            resolve_subgraph_lwt="resolve-lwt",
            save_debug_files="save-debug",
            export_xt_from_prt="legacy-xt-exporter",
            analyze_and_export=lambda **_kwargs: {"success": False, "message": "未识别到任何子图"},
            process_material_lines_fn=lambda **_kwargs: {"processed": False, "debug_output_dir": None},
            upload_split_files_fn=lambda **_kwargs: {},
            export_xt_files_fn=lambda **_kwargs: {},
            persist_split_results_fn=lambda **_kwargs: {},
        )
    )

    assert result == {
        "success": False,
        "message": "未识别到任何子图",
    }


def test_cad_process_runtime_execute_wrapper_uses_src_pipeline(monkeypatch):
    from mold_cost.infrastructure.cad import cad_process_runtime as runtime

    calls: list[tuple[str, object]] = []

    async def _fake_prepare_dxf_input(**kwargs):
        calls.append(("prepare", kwargs))
        return {"success": True, "temp_dxf": "D:/temp/input.dxf"}

    async def _fake_run_cad_process_pipeline(**kwargs):
        calls.append(("pipeline", kwargs))
        return {
            "success": True,
            "result_files": [{"filename": "SG-1.dxf"}, {"filename": "SG-2.dxf"}],
        }

    monkeypatch.setattr(
        runtime,
        "resolve_dwg_source",
        lambda **kwargs: calls.append(("resolve", kwargs))
        or {
            "dwg_source": "bucket/demo.dwg",
            "use_minio": True,
            "source_filename": "demo.dwg",
            "model_code": "MODEL-01",
        },
    )
    monkeypatch.setattr(runtime, "prepare_dxf_input", _fake_prepare_dxf_input)
    monkeypatch.setattr(runtime, "run_cad_process_pipeline", _fake_run_cad_process_pipeline)

    result = asyncio.run(
        runtime.execute_cad_split_process(
            dwg_url=None,
            job_id="job-2",
            db_manager="db-manager",
            storage_manager="storage-manager",
            minio_client="minio-client",
            extract_model_code_from_source="model-code-extractor",
            converter_factory="converter-factory",
            oda_converter_path="D:/tools/oda.exe",
            analysis_system_factory="analysis-system-factory",
            material_line_available=True,
            integrator_factory="material-line-integrator",
            resolve_subgraph_lwt="resolve-lwt",
            save_debug_files="save-debug",
            export_xt_from_prt="legacy-xt-exporter",
            now_factory=lambda: datetime(2026, 4, 5, 12, 30, 0),
        )
    )

    assert result == {
        "status": "ok",
        "data": {
            "total_count": 2,
            "result_files": ["SG-1.dxf", "SG-2.dxf"],
        },
    }
    assert [name for name, _payload in calls] == ["resolve", "prepare", "pipeline"]
