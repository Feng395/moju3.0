"""Tests for the src-owned CAD .x_t export runtime."""

from __future__ import annotations

import asyncio
from datetime import datetime

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_xt_export_runtime_skips_without_nx():
    from mold_cost.infrastructure.cad.cad_xt_export_runtime import export_xt_files

    class _FakeDbManager:
        def get_prt_file_path(self, _job_id):
            raise AssertionError("db lookup should not run when NX is unavailable")

    class _FakeStorageManager:
        async def get_file(self, *_args, **_kwargs):
            raise AssertionError("storage should not run when NX is unavailable")

    result = asyncio.run(
        export_xt_files(
            job_id="job-1",
            temp_dir="D:/temp/cad",
            export_files=[{"sub_code": "A1"}],
            storage_manager=_FakeStorageManager(),
            db_manager=_FakeDbManager(),
            minio_client=object(),
            export_xt_from_prt=lambda **_kwargs: {"A1": "xt/path"},
            nx_importer=lambda: (_ for _ in ()).throw(ImportError("no nx")),
        )
    )

    assert result == {}


def test_cad_xt_export_runtime_downloads_prt_and_exports(monkeypatch):
    from mold_cost.infrastructure.cad import cad_xt_export_runtime as runtime

    calls = []

    class _FakeDbManager:
        def get_prt_file_path(self, job_id):
            calls.append(("db", job_id))
            return "prt/2026/04/demo.prt"

    class _FakeStorageManager:
        async def get_file(self, source, save_path, use_minio=False):
            calls.append(("storage", source, save_path, use_minio))
            return True

    monkeypatch.setattr(
        runtime,
        "datetime",
        type(
            "_FixedDatetime",
            (),
            {
                "now": staticmethod(lambda: datetime(2026, 4, 5, 9, 30, 0)),
            },
        ),
    )

    result = asyncio.run(
        runtime.export_xt_files(
            job_id="job-2",
            temp_dir="D:/temp/cad",
            export_files=[{"sub_code": "A1", "part_code": "P-001"}],
            storage_manager=_FakeStorageManager(),
            db_manager=_FakeDbManager(),
            minio_client="minio-client",
            export_xt_from_prt=lambda **kwargs: calls.append(("export", kwargs)) or {"A1": "xt/2026/04/job-2/P-001.x_t"},
            nx_importer=lambda: object(),
        )
    )

    assert result == {"A1": "xt/2026/04/job-2/P-001.x_t"}
    assert calls[0] == ("db", "job-2")
    assert calls[1] == ("storage", "prt/2026/04/demo.prt", "D:/temp/cad\\source.prt", True)
    assert calls[2][0] == "export"
    assert calls[2][1]["xt_minio_base"] == "xt/2026/04/job-2"
    assert calls[2][1]["minio_client"] == "minio-client"


def test_cad_xt_export_runtime_uses_local_prt_without_minio():
    from mold_cost.infrastructure.cad.cad_xt_export_runtime import export_xt_files

    calls = []

    class _FakeDbManager:
        def get_prt_file_path(self, _job_id):
            return r"D:\cad\demo.prt"

    class _FakeStorageManager:
        async def get_file(self, source, save_path, use_minio=False):
            calls.append((source, save_path, use_minio))
            return True

    result = asyncio.run(
        export_xt_files(
            job_id="job-3",
            temp_dir="D:/temp/cad",
            export_files=[{"sub_code": "A1"}],
            storage_manager=_FakeStorageManager(),
            db_manager=_FakeDbManager(),
            minio_client="minio-client",
            export_xt_from_prt=lambda **_kwargs: {},
            nx_importer=lambda: object(),
        )
    )

    assert result == {}
    assert calls == [(r"D:\cad\demo.prt", "D:/temp/cad\\source.prt", False)]
