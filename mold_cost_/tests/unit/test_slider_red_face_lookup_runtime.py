"""Tests for the src-owned slider red-face lookup runtime."""

from __future__ import annotations

import json
import tempfile

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_slider_red_face_lookup_runtime_patches_existing_slider_entry(monkeypatch):
    from mold_cost.infrastructure.cad import slider_red_face_lookup_runtime as runtime

    class _FakeMinioClient:
        def __init__(self, payload):
            self.payload = payload
            self.calls = []

        def download_file(self, object_name, save_path):
            self.calls.append((object_name, save_path))
            with open(save_path, "w", encoding="utf-8") as file:
                json.dump(self.payload, file, ensure_ascii=False)
            return True

    monkeypatch.setattr(runtime, "_DB_CACHE", {})
    minio_client = _FakeMinioClient(
        {
            "DIE-06": {
                "wire_cut_details": [
                    {
                        "area_num": 2,
                        "total_length": 18.5,
                        "single_length": 9.25,
                    }
                ]
            }
        }
    )

    with tempfile.TemporaryDirectory(prefix="slider-lookup-test-") as _temp_dir:
        result = runtime.apply_red_face_lookup(
            "die-06",
            [{"code": "W1", "instruction": "滑块红面", "matched_count": 1}],
            minio_client=minio_client,
            minio_db_path="slider/custom.json",
        )

    assert result == [
        {
            "code": "滑块",
            "instruction": "滑块红面",
            "matched_count": 2,
            "view": "front_view",
            "area_num": 2,
            "total_length": 18.5,
            "single_length": 9.25,
            "expected_count": 2,
        }
    ]
    assert minio_client.calls[0][0] == "slider/custom.json"


def test_slider_red_face_lookup_runtime_appends_slider_entry_when_missing(monkeypatch):
    from mold_cost.infrastructure.cad import slider_red_face_lookup_runtime as runtime

    monkeypatch.setattr(
        runtime,
        "_load_from_minio",
        lambda _path, _client: {
            "die-07": {
                "wire_cut_details": [
                    {
                        "area_num": 3,
                        "total_length": 21.0,
                        "single_length": 7.0,
                    }
                ]
            }
        },
    )

    result = runtime.apply_red_face_lookup(
        "DIE-07",
        [{"code": "W2", "instruction": "普通线割"}],
        minio_client=object(),
    )

    assert result[-1] == {
        "code": "滑块",
        "cone": "f",
        "view": "front_view",
        "area_num": 3,
        "instruction": "3 -红色面",
        "slider_angle": 0,
        "total_length": 21.0,
        "is_additional": True,
        "matched_count": 3,
        "single_length": 7.0,
        "expected_count": 3,
        "matched_line_ids": [],
        "overlapping_length": 0.0,
    }
