"""Tests for the src-owned CAD split persistence runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_split_persistence_runtime_persists_only_uploaded_items():
    from mold_cost.infrastructure.cad.cad_split_persistence_runtime import persist_split_results

    calls = []

    class _FakeDbManager:
        def save_subgraph(self, sub_code, file_url, source_file, job_id, part_name=None, part_code=None, xt_file_url=None):
            calls.append(
                {
                    "sub_code": sub_code,
                    "file_url": file_url,
                    "source_file": source_file,
                    "job_id": job_id,
                    "part_name": part_name,
                    "part_code": part_code,
                    "xt_file_url": xt_file_url,
                }
            )
            return sub_code != "SG-DB-FAIL"

    result = persist_split_results(
        export_files=[
            {
                "sub_code": "SG-OK",
                "minio_path": "dxf/2026/04/job-1/SG-OK.dxf",
                "part_name": "零件A",
                "part_code": "P-A",
            },
            {
                "sub_code": "SG-UPLOAD-FAIL",
                "minio_path": "dxf/2026/04/job-1/SG-UPLOAD-FAIL.dxf",
                "part_name": "零件B",
                "part_code": "P-B",
            },
            {
                "sub_code": "SG-DB-FAIL",
                "minio_path": "dxf/2026/04/job-1/SG-DB-FAIL.dxf",
                "part_name": "零件C",
                "part_code": "P-C",
            },
        ],
        upload_results={
            "SG-OK": {"success": True},
            "SG-UPLOAD-FAIL": {"success": False, "error": "minio error"},
            "SG-DB-FAIL": {"success": True},
        },
        db_manager=_FakeDbManager(),
        source_filename="source-demo",
        job_id="job-1",
        xt_url_map={"SG-OK": "xt/2026/04/job-1/P-A.x_t"},
    )

    assert result == {
        "result_files": [
            {
                "path": "dxf/2026/04/job-1/SG-OK.dxf",
                "filename": "SG-OK.dxf",
                "sub_code": "SG-OK",
                "source_file": "source-demo",
                "part_name": "零件A",
                "part_code": "P-A",
            }
        ],
        "db_success_count": 1,
        "failed_upload_count": 1,
        "failed_db_count": 1,
    }
    assert calls == [
        {
            "sub_code": "SG-OK",
            "file_url": "dxf/2026/04/job-1/SG-OK.dxf",
            "source_file": "source-demo",
            "job_id": "job-1",
            "part_name": "零件A",
            "part_code": "P-A",
            "xt_file_url": "xt/2026/04/job-1/P-A.x_t",
        },
        {
            "sub_code": "SG-DB-FAIL",
            "file_url": "dxf/2026/04/job-1/SG-DB-FAIL.dxf",
            "source_file": "source-demo",
            "job_id": "job-1",
            "part_name": "零件C",
            "part_code": "P-C",
            "xt_file_url": None,
        },
    ]
