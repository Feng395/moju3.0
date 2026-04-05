"""Tests for the src-owned CAD upload runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_upload_runtime_builds_upload_list():
    from mold_cost.infrastructure.cad.cad_upload_runtime import upload_split_files

    calls = []

    class _FakeMinioClient:
        def batch_upload_files(self, upload_list):
            calls.append(upload_list)
            return {"SG-1": {"success": True}}

    result = upload_split_files(
        export_files=[
            {"sub_code": "SG-1", "local_path": "D:/temp/SG-1.dxf", "minio_path": "dxf/job-1/SG-1.dxf"},
            {"sub_code": "SG-2", "local_path": "D:/temp/SG-2.dxf", "minio_path": "dxf/job-1/SG-2.dxf"},
        ],
        minio_client=_FakeMinioClient(),
    )

    assert result == {"SG-1": {"success": True}}
    assert calls == [[
        ("SG-1", "D:/temp/SG-1.dxf", "dxf/job-1/SG-1.dxf"),
        ("SG-2", "D:/temp/SG-2.dxf", "dxf/job-1/SG-2.dxf"),
    ]]


def test_cad_upload_runtime_handles_missing_client():
    from mold_cost.infrastructure.cad.cad_upload_runtime import upload_split_files

    result = upload_split_files(
        export_files=[{"sub_code": "SG-1", "local_path": "D:/temp/SG-1.dxf", "minio_path": "dxf/job-1/SG-1.dxf"}],
        minio_client=None,
    )

    assert result == {}
