"""Tests for the src-owned slider red-face update runtime."""

from __future__ import annotations

import tempfile

from refactor_bootstrap import ensure_src_path

ensure_src_path()


class _FakeCursor:
    def __init__(self, *, fetchone_results=None):
        self.fetchone_results = list(fetchone_results or [])
        self.executed: list[tuple[str, object]] = []
        self.closed = False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_slider_red_face_update_runtime_patches_existing_slider_entry(monkeypatch):
    from mold_cost.infrastructure.cad import slider_red_face_update_runtime as runtime

    cursor = _FakeCursor(
        fetchone_results=[
            (
                {
                    "wire_cut_details": [
                        {
                            "code": "W1",
                            "instruction": "滑块红面",
                            "matched_count": 1,
                            "expected_count": 1,
                            "single_length": 8.0,
                            "total_length": 8.0,
                        }
                    ]
                },
            )
        ]
    )
    conn = _FakeConnection(cursor)
    monkeypatch.setattr(runtime, "_json_value", lambda payload: {"json": payload})

    with tempfile.NamedTemporaryFile(suffix=".x_t") as xt_file:
        result = runtime.update_slider_red_face_data(
            "sg-1",
            "job-1",
            xt_file.name,
            connect_factory=lambda: conn,
            extract_red_face_stats=lambda _path: {
                "red_face_count": 2,
                "total_area": 18.5,
                "single_length": 9.25,
            },
        )

    assert result is True
    assert conn.committed is True
    assert conn.rolled_back is False
    assert cursor.closed is True
    assert conn.closed is True

    update_sql, update_params = cursor.executed[1]
    assert "UPDATE features SET metadata" in update_sql
    assert update_params == (
        {
            "json": {
                "wire_cut_details": [
                    {
                        "code": "滑块",
                        "instruction": "滑块红面",
                        "matched_count": 2,
                        "expected_count": 2,
                        "single_length": 9.25,
                        "total_length": 18.5,
                        "view": "front_view",
                        "area_num": 2,
                    }
                ]
            }
        },
        "sg-1",
        "job-1",
    )


def test_slider_red_face_update_runtime_downloads_xt_and_appends_new_entry(monkeypatch):
    from mold_cost.infrastructure.cad import slider_red_face_update_runtime as runtime

    class _FakeMinioClient:
        def __init__(self):
            self.calls = []

        def get_file(self, object_name, save_path):
            self.calls.append((object_name, save_path))
            with open(save_path, "w", encoding="utf-8") as file:
                file.write("xt")
            return True

    cursor = _FakeCursor(fetchone_results=[({"wire_cut_details": [{"code": "W2", "instruction": "普通线割"}]},)])
    conn = _FakeConnection(cursor)
    minio_client = _FakeMinioClient()
    monkeypatch.setattr(runtime, "_json_value", lambda payload: {"json": payload})

    result = runtime.update_slider_red_face_data(
        "sg-2",
        "job-2",
        "bucket/demo.x_t",
        minio_client=minio_client,
        connect_factory=lambda: conn,
        extract_red_face_stats=lambda path: {
            "red_face_count": 3,
            "total_area": 21.0,
            "single_length": 7.0,
            "source_path": path,
        },
    )

    assert result is True
    assert minio_client.calls[0][0] == "bucket/demo.x_t"

    update_sql, update_params = cursor.executed[1]
    assert "UPDATE features SET metadata" in update_sql
    assert update_params == (
        {
            "json": {
                "wire_cut_details": [
                    {"code": "W2", "instruction": "普通线割"},
                    {
                        "code": "滑块",
                        "cone": "f",
                        "view": "front_view",
                        "area_num": 3,
                        "instruction": "3 -红色面",
                        "slider_angle": 0,
                        "total_length": 21.0,
                        "is_additional": False,
                        "matched_count": 3,
                        "single_length": 7.0,
                        "expected_count": 3,
                        "matched_line_ids": [],
                        "overlapping_length": 0.0,
                    },
                ]
            }
        },
        "sg-2",
        "job-2",
    )


def test_slider_red_face_update_runtime_skips_write_when_no_red_faces():
    from mold_cost.infrastructure.cad import slider_red_face_update_runtime as runtime

    connect_calls = []

    with tempfile.NamedTemporaryFile(suffix=".x_t") as xt_file:
        result = runtime.update_slider_red_face_data(
            "sg-3",
            "job-3",
            xt_file.name,
            connect_factory=lambda: connect_calls.append(True),
            extract_red_face_stats=lambda _path: None,
        )

    assert result is False
    assert connect_calls == []
