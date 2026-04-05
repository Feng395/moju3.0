"""Tests for the src-owned CAD analysis/export runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_analysis_runtime_handles_full_flow(monkeypatch):
    from mold_cost.infrastructure.cad.cad_analysis_runtime import analyze_and_export_subgraphs

    class _FakeAnalyzer:
        def analyze_cad_file_streaming(self, _temp_dxf):
            yield ("region-1", {"x": 1}, 1, 2)
            yield ("region-2", {"x": 2}, 2, 2)

        def resolve_region_info(self, region_id, _region):
            if region_id == "region-1":
                return ("P-001", "零件A", "P-001")
            return ("P-001", "零件B", "P-001")

    class _FakeAnalysisSystem:
        def __init__(self):
            self.analyzer = _FakeAnalyzer()

        def batch_export_regions_concurrent(self, batch_export_list, **kwargs):
            assert kwargs["max_workers"] == 7
            return [
                {"sub_code": "P-001", "output_path": batch_export_list[0]["output_path"], "success": True},
                {"sub_code": "P-001A", "output_path": batch_export_list[1]["output_path"], "success": True},
            ]

    monkeypatch.setenv("EXPORT_WORKERS", "7")

    result = analyze_and_export_subgraphs(
        analysis_system=_FakeAnalysisSystem(),
        temp_dxf="D:/temp/input.dxf",
        temp_dir="D:/temp/cad",
        minio_base_path="dxf/2026/04/job-1",
    )

    assert result["success"] is True
    assert len(result["all_regions"]) == 2
    assert result["failed_recognition_count"] == 0
    assert result["failed_export_count"] == 0
    assert result["region_info_list"][1]["sub_code"] == "P-001A"
    assert result["export_files"] == [
        {
            "sub_code": "P-001",
            "part_name": "零件A",
            "part_code": "P-001",
            "local_path": "D:/temp/cad\\output_P-001.dxf",
            "minio_path": "dxf/2026/04/job-1/P-001.dxf",
            "index": 1,
        },
        {
            "sub_code": "P-001A",
            "part_name": "零件B",
            "part_code": "P-001",
            "local_path": "D:/temp/cad\\output_P-001A.dxf",
            "minio_path": "dxf/2026/04/job-1/P-001A.dxf",
            "index": 2,
        },
    ]


def test_cad_analysis_runtime_returns_error_when_no_regions():
    from mold_cost.infrastructure.cad.cad_analysis_runtime import analyze_and_export_subgraphs

    class _FakeAnalyzer:
        def analyze_cad_file_streaming(self, _temp_dxf):
            if False:
                yield None

    class _FakeAnalysisSystem:
        def __init__(self):
            self.analyzer = _FakeAnalyzer()

    result = analyze_and_export_subgraphs(
        analysis_system=_FakeAnalysisSystem(),
        temp_dxf="D:/temp/input.dxf",
        temp_dir="D:/temp/cad",
        minio_base_path="dxf/2026/04/job-1",
    )

    assert result["success"] is False
    assert result["message"] == "未识别到任何子图"
