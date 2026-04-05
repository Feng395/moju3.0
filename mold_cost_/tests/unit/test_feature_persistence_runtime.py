"""Tests for the src-owned feature persistence runtime."""

from __future__ import annotations

from datetime import datetime

from refactor_bootstrap import ensure_src_path

ensure_src_path()


class _FakeCursor:
    def __init__(self, *, fetchone_results=None, fetchall_result=None):
        self.fetchone_results = list(fetchone_results or [])
        self.fetchall_result = list(fetchall_result or [])
        self.executed: list[tuple[str, object]] = []
        self.closed = False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self):
        return list(self.fetchall_result)

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


def test_feature_persistence_runtime_get_subgraphs_reads_xt_file_url(monkeypatch):
    from mold_cost.infrastructure.cad import feature_persistence_runtime as runtime

    cursor = _FakeCursor(
        fetchone_results=[(1,)],
        fetchall_result=[
            ("sg-1", "P-001", "bucket/demo.dxf", "bucket/demo.x_t"),
            ("sg-2", "P-002", "bucket/demo-2.dxf", "bucket/demo-2.x_t"),
        ],
    )
    conn = _FakeConnection(cursor)
    monkeypatch.setattr(runtime, "_SUBGRAPHS_HAS_XT_FILE_URL", None)

    result = runtime.get_subgraphs_from_db("job-1", connect_factory=lambda: conn)

    assert result == [
        {
            "subgraph_id": "sg-1",
            "part_code": "P-001",
            "subgraph_file_url": "bucket/demo.dxf",
            "xt_file_url": "bucket/demo.x_t",
        },
        {
            "subgraph_id": "sg-2",
            "part_code": "P-002",
            "subgraph_file_url": "bucket/demo-2.dxf",
            "xt_file_url": "bucket/demo-2.x_t",
        },
    ]
    assert "information_schema.columns" in cursor.executed[0][0]
    assert "xt_file_url" in cursor.executed[1][0]
    assert cursor.closed is True
    assert conn.closed is True


def test_feature_persistence_runtime_save_features_persists_payload(monkeypatch):
    from mold_cost.infrastructure.cad import feature_persistence_runtime as runtime

    fixed_now = datetime(2026, 4, 5, 12, 30, 0)
    cursor = _FakeCursor(fetchone_results=[(321,)])
    conn = _FakeConnection(cursor)
    lookup_calls = []

    def _fake_lookup(part_code, wire_cut_details, *, minio_client=None):
        lookup_calls.append(
            {
                "part_code": part_code,
                "wire_cut_details": wire_cut_details,
                "minio_client": minio_client,
            }
        )
        return [
            {
                "code": "滑块",
                "instruction": "2 -红色面",
                "expected_count": 2,
                "matched_count": 2,
                "total_length": 18.5,
            }
        ]

    monkeypatch.setattr(runtime, "_json_value", lambda payload: {"json": payload})

    result = runtime.save_features_to_db(
        "sg-1",
        "job-1",
        {
            "part_code": "P-001",
            "length_mm": 10.0,
            "width_mm": 20.0,
            "thickness_mm": 30.0,
            "top_view_wire_length": 40.0,
            "front_view_wire_length": 50.0,
            "side_view_wire_length": 60.0,
            "processing_instructions": {"F1": ["工艺A"]},
            "wire_cut_details": [
                {
                    "code": "W1",
                    "instruction": "滑块红面",
                    "expected_count": 1,
                    "matched_count": 1,
                    "total_length": 9.9,
                }
            ],
            "abnormal_situation": {"wire_cut_anomalies": [{"code": "W1"}]},
            "quantity": 2,
            "material": "S136",
            "heat_treatment": "HRC48",
            "weight_kg": 1.234,
            "has_auto_material": True,
            "boring_num": 3,
            "has_material_preparation": "备料于A面",
            "water_mill": {"thread_ends": 1},
            "tooth_hole": {"tooth_hole_details": [{"id": 1}]},
            "wire_process_note": "快丝割一刀",
            "wire_process": "fast_cut",
        },
        connect_factory=lambda: conn,
        minio_client="minio-client",
        red_face_lookup=_fake_lookup,
        now_factory=lambda: fixed_now,
    )

    assert result is True
    assert lookup_calls == [
        {
            "part_code": "P-001",
            "wire_cut_details": [
                {
                    "code": "W1",
                    "instruction": "滑块红面",
                    "expected_count": 1,
                    "matched_count": 1,
                    "total_length": 9.9,
                }
            ],
            "minio_client": "minio-client",
        }
    ]
    assert conn.committed is True
    assert conn.rolled_back is False
    assert len(cursor.executed) == 3

    feature_sql, feature_values = cursor.executed[0]
    assert "INSERT INTO features" in feature_sql
    assert feature_values[0:3] == ("sg-1", "job-1", 1)
    assert feature_values[9] == {"json": {"F1": ["工艺A"]}}
    assert feature_values[10] == {
        "json": {
            "wire_cut_details": [
                {
                    "code": "滑块",
                    "instruction": "2 -红色面",
                    "expected_count": 2,
                    "matched_count": 2,
                    "total_length": 18.5,
                }
            ]
        }
    }
    assert feature_values[22] == fixed_now

    detail_sql, detail_values = cursor.executed[1]
    assert "processing_cost_calculation_details" in detail_sql
    assert detail_values == ("job-1", "sg-1", fixed_now, fixed_now)

    update_sql, update_values = cursor.executed[2]
    assert "UPDATE subgraphs" in update_sql
    assert "wire_process_note = %s" in update_sql
    assert "wire_process = %s" in update_sql
    assert update_values == ("快丝割一刀", "fast_cut", "sg-1")


def test_feature_gateway_get_subgraphs_and_save_features_use_src_runtime(monkeypatch):
    import sys
    import types

    from mold_cost.infrastructure.cad.legacy_feature_recognition_gateway import LegacyFeatureRecognitionGateway

    get_calls = []
    save_calls = []

    monkeypatch.setattr(
        "mold_cost.infrastructure.cad.legacy_feature_recognition_gateway.get_subgraphs_from_db",
        lambda job_id, subgraph_id=None: get_calls.append((job_id, subgraph_id)) or [{"subgraph_id": "sg-1"}],
    )
    monkeypatch.setattr(
        "mold_cost.infrastructure.cad.legacy_feature_recognition_gateway.save_features_to_db",
        lambda subgraph_id, job_id, features, **kwargs: save_calls.append(
            {
                "subgraph_id": subgraph_id,
                "job_id": job_id,
                "features": features,
                "kwargs": kwargs,
            }
        )
        or True,
    )
    monkeypatch.setitem(
        sys.modules,
        "scripts.minio_client",
        types.SimpleNamespace(minio_client="legacy-minio"),
    )
    monkeypatch.setitem(
        sys.modules,
        "scripts.feature_recognition.slider_red_face_lookup",
        types.SimpleNamespace(apply_red_face_lookup="lookup-fn"),
    )

    gateway = LegacyFeatureRecognitionGateway()
    subgraphs = gateway.get_subgraphs("job-2", "sg-9")
    saved = gateway.save_features("sg-9", "job-2", {"part_code": "P-009"})

    assert subgraphs == [{"subgraph_id": "sg-1"}]
    assert saved is True
    assert get_calls == [("job-2", "sg-9")]
    assert save_calls == [
        {
            "subgraph_id": "sg-9",
            "job_id": "job-2",
            "features": {"part_code": "P-009"},
            "kwargs": {
                "minio_client": "legacy-minio",
                "red_face_lookup": "lookup-fn",
            },
        }
    ]
