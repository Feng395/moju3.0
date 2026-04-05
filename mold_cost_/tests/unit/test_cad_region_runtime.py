"""Tests for the src-owned CAD region/export runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_region_runtime_resolves_duplicates_and_defaults():
    from mold_cost.infrastructure.cad.cad_region_runtime import resolve_region_infos

    calls = []

    def _resolver(region_id, region):
        calls.append((region_id, region))
        if region_id == "region-1":
            return (None, "", None)
        if region_id == "region-2":
            return ("P-001", "零件A", "P-001")
        if region_id == "region-3":
            return ("P-001", "零件B", "P-001")
        raise RuntimeError("boom")

    result = resolve_region_infos(
        all_regions=[
            ("region-1", {"x": 1}),
            ("region-2", {"x": 2}),
            ("region-3", {"x": 3}),
            ("region-4", {"x": 4}),
        ],
        resolver=_resolver,
    )

    assert result["failed_recognition_count"] == 1
    assert result["region_info_list"] == [
        {
            "region_id": "region-1",
            "region": {"x": 1},
            "sub_code": "region-1",
            "part_name": "未识别",
            "part_code": "region-1",
            "index": 1,
        },
        {
            "region_id": "region-2",
            "region": {"x": 2},
            "sub_code": "P-001",
            "part_name": "零件A",
            "part_code": "P-001",
            "index": 2,
        },
        {
            "region_id": "region-3",
            "region": {"x": 3},
            "sub_code": "P-001A",
            "part_name": "零件B",
            "part_code": "P-001",
            "index": 3,
        },
    ]
    assert result["region_info_map"]["P-001A"]["part_name"] == "零件B"
    assert len(calls) == 4


def test_cad_region_runtime_builds_export_plan_and_collects_results():
    from mold_cost.infrastructure.cad.cad_region_runtime import build_batch_export_list, collect_export_files

    region_info_list = [
        {"sub_code": "SG-1", "region": {"bounds": {}}, "part_name": "零件A", "part_code": "P-A", "index": 1},
        {"sub_code": "SG-2", "region": {"bounds": {}}, "part_name": "零件B", "part_code": "P-B", "index": 2},
    ]

    batch_export_list = build_batch_export_list(region_info_list=region_info_list, temp_dir="D:/temp/cad")
    export_summary = collect_export_files(
        region_info_list=region_info_list,
        export_results=[
            {"sub_code": "SG-1", "output_path": "D:/temp/cad/output_SG-1.dxf", "success": True},
            {"sub_code": "SG-2", "output_path": "D:/temp/cad/output_SG-2.dxf", "success": False, "error": "bad dxf"},
        ],
        minio_base_path="dxf/2026/04/job-1",
    )

    assert batch_export_list == [
        {"sub_code": "SG-1", "region": {"bounds": {}}, "output_path": "D:/temp/cad\\output_SG-1.dxf"},
        {"sub_code": "SG-2", "region": {"bounds": {}}, "output_path": "D:/temp/cad\\output_SG-2.dxf"},
    ]
    assert export_summary == {
        "export_files": [
            {
                "sub_code": "SG-1",
                "part_name": "零件A",
                "part_code": "P-A",
                "local_path": "D:/temp/cad/output_SG-1.dxf",
                "minio_path": "dxf/2026/04/job-1/SG-1.dxf",
                "index": 1,
            }
        ],
        "failed_export_count": 1,
    }
