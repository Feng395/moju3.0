"""Tests for the src-owned feature analysis runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_feature_analysis_runtime_returns_normalized_result(monkeypatch):
    from mold_cost.infrastructure.cad import feature_analysis_runtime as runtime

    class _FakeDoc:
        def modelspace(self):
            return _FakeModelspace()

    class _FakeModelspace:
        def query(self, _pattern):
            return []

    class _FakeEzdxf:
        @staticmethod
        def readfile(path):
            assert path == "demo.dxf"
            return fake_doc

    class _FakeViewCalculator:
        def __init__(self, tolerance: float):
            assert tolerance == 5.0

        def calculate_wire_lengths_by_views(self, doc, l, w, t, processing_instructions_old, all_texts):
            assert doc is fake_doc
            assert (l, w, t) == (10.0, 20.0, 30.0)
            assert processing_instructions_old == {"F1": ["工艺A"]}
            assert all_texts == ["快丝割一刀", "说明"]
            return {
                "top_view_wire_length": 11.11,
                "front_view_wire_length": 22.22,
                "side_view_wire_length": 33.33,
                "wire_cut_anomalies": [],
                "wire_cut_details": [{"code": "W1", "expected_count": 1, "matched_count": 1, "total_length": 11.11}],
                "views": {"top_view": True, "front_view": True, "side_view": True},
                "unmatched_red_lines": [],
            }

    fake_doc = _FakeDoc()

    monkeypatch.setattr(runtime, "_load_dependencies", lambda: None)
    monkeypatch.setattr(runtime, "ezdxf", _FakeEzdxf())
    monkeypatch.setattr(runtime, "extract_all_texts", lambda msp: {"texts": ["快丝割一刀", "说明"]})
    monkeypatch.setattr(runtime, "extract_dimensions", lambda doc: (10.0, 20.0, 30.0))
    monkeypatch.setattr(runtime, "parse_processing_instructions_from_texts", lambda texts: ({"F1": ["工艺A"]}, ["工艺A"]))
    monkeypatch.setattr(
        runtime,
        "parse_frame_texts_from_extracted",
        lambda all_text_data, doc: {"FRAME-1": [{"content": "文本1"}, {"content": "文本2"}]},
    )
    monkeypatch.setattr(
        runtime,
        "parse_material_info_from_texts",
        lambda texts: {"quantity": 2, "material": "S136", "heat_treatment": "HRC48", "weight_kg": 1.2345},
    )
    monkeypatch.setattr(runtime, "check_auto_material_from_texts", lambda texts: False)
    monkeypatch.setattr(runtime, "extract_material_preparation", lambda texts: False)
    monkeypatch.setattr(runtime, "ViewWireCalculator", _FakeViewCalculator)
    monkeypatch.setattr(runtime, "calculate_boring_num", lambda details: 3)
    monkeypatch.setattr(
        runtime,
        "detect_chamfers",
        lambda all_texts, instruction_full_texts: {
            "c1_c2_chamfer": 0,
            "c3_c5_chamfer": 0,
            "r1_r2_chamfer": 0,
            "r3_r5_chamfer": 0,
        },
    )
    monkeypatch.setattr(runtime, "detect_oil_tank", lambda all_texts, doc: 0)
    monkeypatch.setattr(runtime, "detect_bevel", lambda all_texts, doc, views: [])
    monkeypatch.setattr(runtime, "detect_grinding_faces", lambda doc, length, width, thickness: 2)
    monkeypatch.setattr(runtime, "should_calculate_water_mill", lambda has_material_preparation, has_auto_material: False)
    monkeypatch.setattr(
        runtime,
        "get_water_mill_data",
        lambda **kwargs: {"thread_ends": kwargs["thread_ends"], "grinding": kwargs["grinding"]},
    )
    monkeypatch.setattr(runtime, "detect_tooth_hole", lambda **kwargs: {"count": 0})

    result = runtime.analyze_dxf_features("demo.dxf")

    assert result is not None
    assert result["length_mm"] == 10.0
    assert result["width_mm"] == 20.0
    assert result["thickness_mm"] == 30.0
    assert result["top_view_wire_length"] == 11.11
    assert result["front_view_wire_length"] == 22.22
    assert result["side_view_wire_length"] == 33.33
    assert result["processing_instructions"] == {"FRAME-1": ["文本1", "文本2"]}
    assert result["quantity"] == 2
    assert result["material"] == "S136"
    assert result["heat_treatment"] == "HRC48"
    assert result["weight_kg"] == 1.234
    assert result["boring_num"] == 3
    assert result["wire_process_note"] == "快丝割一刀"
    assert result["wire_process"] == "fast_cut"
    assert result["water_mill"] == {"thread_ends": 0, "grinding": 2}
    assert result["tooth_hole"] == {"count": 0}
