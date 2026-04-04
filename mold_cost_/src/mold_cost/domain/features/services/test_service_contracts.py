"""CAD / Feature 服务契约测试。"""

from __future__ import annotations

import asyncio

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_split_service_returns_stable_summary_and_artifacts():
    """验证 CAD 拆图服务会产出统一 summary 与 artifact 引用。"""
    from mold_cost.domain.cad.services.split_service import LegacyCadSplitService

    class StubGateway:
        async def split(self, dwg_url, job_id, minio_client=None):
            return {
                "status": "ok",
                "data": {
                    "total_count": 2,
                    "result_files": ["A01.dxf", "B02.dxf"],
                },
            }

        async def list_subgraphs(self, job_id):
            return [
                {
                    "subgraph_id": "job-1_A01",
                    "part_code": "A01",
                    "part_name": "BLOCK-A",
                    "subgraph_file_url": "dxf/2026/04/job-1/A01.dxf",
                },
                {
                    "subgraph_id": "job-1_B02",
                    "part_code": "B02",
                    "part_name": "BLOCK-B",
                    "subgraph_file_url": "dxf/2026/04/job-1/B02.dxf",
                },
            ]

    service = LegacyCadSplitService(StubGateway())
    result = asyncio.run(service.split(dwg_url="dwg/demo.dwg", job_id="job-1"))

    assert result["status"] == "ok"
    assert result["success"] is True
    assert result["operation"] == "cad_split"
    assert result["summary"] == {
        "operation": "cad_split",
        "job_id": "job-1",
        "status": "success",
        "total_count": 2,
        "success_count": 2,
        "failed_count": 0,
        "requested_count": 2,
        "artifact_count": 2,
        "failed_ids": [],
    }
    assert result["artifacts"][0]["artifact_type"] == "cad_subgraph_dxf"
    assert result["artifacts"][0]["ref"] == "minio://dxf/2026/04/job-1/A01.dxf"
    assert result["data"]["subgraphs"][0]["subgraph_id"] == "job-1_A01"


def test_feature_recognition_service_normalizes_partial_results():
    """验证特征识别服务会统一 partial summary、error 与 artifact。"""
    from mold_cost.domain.features.services.recognition_service import LegacyFeatureRecognitionService

    class StubGateway:
        @staticmethod
        def batch_recognize(job_id, subgraph_id=None, progress_callback=None):
            assert job_id == "job-2"
            assert subgraph_id is None
            return {
                "success": True,
                "data": {
                    "success_count": 1,
                    "failed_count": 1,
                    "results": [
                        {
                            "subgraph_id": "SG-1",
                            "part_code": "P-1",
                            "success": True,
                            "features": {
                                "length_mm": 12.3,
                                "wire_cut_details": [],
                            },
                        },
                        {
                            "subgraph_id": "SG-2",
                            "part_code": "P-2",
                            "success": False,
                            "message": "下载失败",
                        },
                    ],
                },
            }

        @staticmethod
        def analyze_dxf(dxf_path):
            return {"path": dxf_path}

        @staticmethod
        def get_subgraphs(job_id, subgraph_id=None):
            return [
                {
                    "subgraph_id": "SG-1",
                    "part_code": "P-1",
                    "subgraph_file_url": "dxf/2026/04/job-2/SG-1.dxf",
                },
                {
                    "subgraph_id": "SG-2",
                    "part_code": "P-2",
                    "subgraph_file_url": "dxf/2026/04/job-2/SG-2.dxf",
                },
            ]

        @staticmethod
        def save_features(subgraph_id, job_id, features):
            return True

        @staticmethod
        def upload_feature_database(database, minio_path):
            return None

    service = LegacyFeatureRecognitionService(StubGateway())
    result = service.batch_recognize("job-2")

    assert result["status"] == "ok"
    assert result["success"] is True
    assert result["summary"] == {
        "operation": "feature_recognition",
        "job_id": "job-2",
        "status": "partial",
        "total_count": 2,
        "success_count": 1,
        "failed_count": 1,
        "requested_count": 2,
        "artifact_count": 1,
        "failed_ids": ["SG-2"],
        "mode": "batch",
    }
    assert result["artifacts"] == [
        {
            "artifact_type": "feature_record",
            "ref": "db://features/job-2/SG-1",
            "storage": "database",
            "locator": {
                "job_id": "job-2",
                "subgraph_id": "SG-1",
                "part_code": "P-1",
                "source_path": "dxf/2026/04/job-2/SG-1.dxf",
            },
            "metadata": {
                "operation": "feature_recognition",
                "feature_keys": ["length_mm", "wire_cut_details"],
                "source_ref": "minio://dxf/2026/04/job-2/SG-1.dxf",
            },
        }
    ]
    assert result["data"]["results"][1]["status"] == "failed"
    assert result["data"]["results"][1]["error"] == "下载失败"


def test_feature_recognition_service_returns_structured_error_for_missing_job():
    """验证缺参时会返回统一异常模型。"""
    from mold_cost.domain.features.services.recognition_service import LegacyFeatureRecognitionService

    class StubGateway:
        @staticmethod
        def batch_recognize(job_id, subgraph_id=None, progress_callback=None):
            raise AssertionError("should not be called")

        @staticmethod
        def analyze_dxf(dxf_path):
            return None

        @staticmethod
        def get_subgraphs(job_id, subgraph_id=None):
            return []

        @staticmethod
        def save_features(subgraph_id, job_id, features):
            return True

        @staticmethod
        def upload_feature_database(database, minio_path):
            return None

    service = LegacyFeatureRecognitionService(StubGateway())
    result = service.batch_recognize("")

    assert result["status"] == "error"
    assert result["error"] == {
        "code": "MISSING_JOB_ID",
        "message": "缺少 job_id",
        "retryable": False,
        "details": {
            "requested_subgraph_id": None,
        },
    }
    assert result["summary"]["status"] == "failed"
    assert result["artifacts"] == []
