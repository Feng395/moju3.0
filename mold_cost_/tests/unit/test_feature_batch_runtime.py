"""Tests for the src-owned feature batch runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


class _FakeMinioClient:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def batch_get_files(self, download_tasks, max_workers=5):
        self.calls.append((download_tasks, max_workers))
        return self.results


def test_feature_batch_runtime_happy_path_preserves_part_code_and_slider_update(monkeypatch):
    from mold_cost.infrastructure.cad.feature_batch_runtime import batch_feature_recognition

    save_calls = []
    slider_calls = []
    progress_calls = []

    monkeypatch.setenv("MINIO_DOWNLOAD_WORKERS", "5")

    def _fake_get_subgraphs(job_id, subgraph_id):
        assert (job_id, subgraph_id) == ("job-1", "sg-1")
        return [
            {
                "subgraph_id": "sg-1",
                "part_code": "P-001",
                "subgraph_file_url": "bucket/demo.dxf",
                "xt_file_url": "bucket/demo.x_t",
            }
        ]

    def _fake_save_features(subgraph_id, job_id, features):
        save_calls.append((subgraph_id, job_id, features))
        return True

    def _fake_slider_updater(**kwargs):
        slider_calls.append(kwargs)

    monkeypatch.setattr(
        "mold_cost.infrastructure.cad.feature_batch_runtime.analyze_dxf_features",
        lambda path: {
            "source_path": path,
            "wire_cut_details": [{"instruction": "滑块红面", "code": "W1"}],
        },
    )

    minio_client = _FakeMinioClient(
        {
            "sg-1": {
                "success": True,
                "save_path": "D:/temp/sg-1.dxf",
            }
        }
    )

    result = batch_feature_recognition(
        "job-1",
        subgraph_id="sg-1",
        progress_callback=lambda *args: progress_calls.append(args),
        get_subgraphs=_fake_get_subgraphs,
        save_features=_fake_save_features,
        minio_client=minio_client,
        slider_red_face_updater=_fake_slider_updater,
        db_config={"database": "demo"},
    )

    assert result["success"] is True
    assert result["data"]["total"] == 1
    assert result["data"]["success_count"] == 1
    assert result["data"]["failed_count"] == 0
    assert result["data"]["results"][0]["subgraph_id"] == "sg-1"
    assert save_calls == [
        (
            "sg-1",
            "job-1",
            {
                "source_path": "D:/temp/sg-1.dxf",
                "wire_cut_details": [{"instruction": "滑块红面", "code": "W1"}],
                "part_code": "P-001",
            },
        )
    ]
    assert slider_calls == [
        {
            "subgraph_id": "sg-1",
            "job_id": "job-1",
            "xt_file_url": "bucket/demo.x_t",
            "db_config": {"database": "demo"},
            "minio_client": minio_client,
        }
    ]
    assert progress_calls == [(1, 1, 1, 0)]
    assert minio_client.calls[0][1] == 5
    assert minio_client.calls[0][0][0][0] == "sg-1"


def test_feature_batch_runtime_tracks_download_analyze_and_save_failures(monkeypatch):
    from mold_cost.infrastructure.cad.feature_batch_runtime import batch_feature_recognition

    progress_calls = []

    def _fake_get_subgraphs(job_id, subgraph_id):
        assert (job_id, subgraph_id) == ("job-2", None)
        return [
            {"subgraph_id": "sg-download", "part_code": "P-D", "subgraph_file_url": "download-fail.dxf"},
            {"subgraph_id": "sg-analyze", "part_code": "P-A", "subgraph_file_url": "analyze-fail.dxf"},
            {"subgraph_id": "sg-save", "part_code": "P-S", "subgraph_file_url": "save-fail.dxf"},
        ]

    def _fake_save_features(subgraph_id, job_id, features):
        assert job_id == "job-2"
        assert features["part_code"] == "P-S"
        return False

    def _fake_analyze(path):
        if path.endswith("sg-analyze.dxf"):
            return None
        if path.endswith("sg-save.dxf"):
            return {"wire_cut_details": []}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("mold_cost.infrastructure.cad.feature_batch_runtime.analyze_dxf_features", _fake_analyze)

    minio_client = _FakeMinioClient(
        {
            "sg-download": {"success": False, "error": "missing"},
            "sg-analyze": {"success": True, "save_path": "D:/temp/sg-analyze.dxf"},
            "sg-save": {"success": True, "save_path": "D:/temp/sg-save.dxf"},
        }
    )

    result = batch_feature_recognition(
        "job-2",
        progress_callback=lambda *args: progress_calls.append(args),
        get_subgraphs=_fake_get_subgraphs,
        save_features=_fake_save_features,
        minio_client=minio_client,
    )

    assert result == {
        "success": True,
        "data": {
            "total": 3,
            "success_count": 0,
            "failed_count": 3,
            "results": [
                {
                    "subgraph_id": "sg-download",
                    "part_code": "P-D",
                    "success": False,
                    "message": "下载失败: missing",
                },
                {
                    "subgraph_id": "sg-analyze",
                    "part_code": "P-A",
                    "success": False,
                    "message": "特征识别失败",
                },
                {
                    "subgraph_id": "sg-save",
                    "part_code": "P-S",
                    "success": False,
                    "message": "保存到数据库失败",
                },
            ],
        },
    }
    assert progress_calls == [
        (1, 3, 0, 1),
        (2, 3, 0, 2),
        (3, 3, 0, 3),
    ]


def test_feature_batch_runtime_skips_slider_update_without_xt_file(monkeypatch):
    from mold_cost.infrastructure.cad.feature_batch_runtime import batch_feature_recognition

    slider_calls = []

    monkeypatch.setattr(
        "mold_cost.infrastructure.cad.feature_batch_runtime.analyze_dxf_features",
        lambda _path: {"wire_cut_details": [{"instruction": "滑块红面"}]},
    )

    minio_client = _FakeMinioClient(
        {
            "sg-1": {"success": True, "save_path": "D:/temp/sg-1.dxf"},
        }
    )

    result = batch_feature_recognition(
        "job-3",
        subgraph_id="sg-1",
        get_subgraphs=lambda *_args: [
            {
                "subgraph_id": "sg-1",
                "part_code": "P-001",
                "subgraph_file_url": "bucket/demo.dxf",
                "xt_file_url": None,
            }
        ],
        save_features=lambda *_args: True,
        minio_client=minio_client,
        slider_red_face_updater=lambda **kwargs: slider_calls.append(kwargs),
        db_config={"database": "demo"},
    )

    assert result["success"] is True
    assert slider_calls == []
