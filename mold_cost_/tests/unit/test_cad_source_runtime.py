"""Tests for the src-owned CAD source resolution runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_source_runtime_detects_minio_object_path():
    from mold_cost.infrastructure.cad.cad_source_runtime import is_probable_minio_object_path

    assert is_probable_minio_object_path("dwg/2026/04/demo.dwg") is True
    assert is_probable_minio_object_path(r"D:\cad\demo.dwg") is False
    assert is_probable_minio_object_path("https://example.com/demo.dwg") is False


def test_cad_source_runtime_resolves_dwg_from_db():
    from mold_cost.infrastructure.cad.cad_source_runtime import resolve_dwg_source

    class _FakeDbManager:
        def get_dwg_file_path(self, job_id):
            assert job_id == "job-1"
            return "dwg/2026/04/demo.dwg"

    result = resolve_dwg_source(
        dwg_url=None,
        job_id="job-1",
        db_manager=_FakeDbManager(),
        extract_model_code_from_source=lambda source: f"MODEL::{source}",
    )

    assert result == {
        "dwg_source": "dwg/2026/04/demo.dwg",
        "use_minio": True,
        "url_filename": "demo.dwg",
        "source_filename": "demo",
        "model_code": "MODEL::dwg/2026/04/demo.dwg",
    }


def test_cad_source_runtime_resolves_local_dwg_and_prt():
    from mold_cost.infrastructure.cad.cad_source_runtime import resolve_dwg_source, resolve_prt_source

    class _FakeDbManager:
        def get_prt_file_path(self, job_id):
            assert job_id == "job-2"
            return r"D:\cad\demo.prt"

    dwg_result = resolve_dwg_source(
        dwg_url=r"D:\cad\demo.dwg",
        job_id="job-2",
        db_manager=object(),
        extract_model_code_from_source=lambda _source: None,
    )
    prt_result = resolve_prt_source(job_id="job-2", db_manager=_FakeDbManager())

    assert dwg_result == {
        "dwg_source": r"D:\cad\demo.dwg",
        "use_minio": False,
        "url_filename": "demo.dwg",
        "source_filename": "demo",
        "model_code": "demo",
    }
    assert prt_result == {
        "prt_source": r"D:\cad\demo.prt",
        "use_minio": False,
    }
