"""Tests for src-owned CAD deep analyzer helpers."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_text_processor_keeps_meaningful_text_and_filters_noise():
    from mold_cost.infrastructure.cad.text_processor import IntelligentTextProcessor

    processor = IntelligentTextProcessor()
    result = processor.process_text_list(
        [
            {"content": "品名:下模座"},
            {"content": "100.0"},
            {"content": "M8x1.25"},
            {"content": "A"},
            {"content": "A"},
            {"content": "A"},
        ]
    )

    assert [item["content"] for item in result] == ["品名:下模座", "A", "A", "A"]


def test_cutting_detector_detects_reference_points_from_three_circles():
    from mold_cost.infrastructure.cad.cutting_detector import RelaxedCuttingDetector

    detector = RelaxedCuttingDetector()
    result = detector.detect_cutting_contours_in_region(
        bounds={"min_x": -1, "max_x": 20, "min_y": -1, "max_y": 20},
        entities=[
            {"type": "CIRCLE", "center": (0.0, 0.0), "perimeter": 10.0, "entity_color": 1, "layer": "0"},
            {"type": "CIRCLE", "center": (10.0, 0.0), "perimeter": 10.0, "entity_color": 1, "layer": "0"},
            {"type": "CIRCLE", "center": (0.0, 10.0), "perimeter": 10.0, "entity_color": 1, "layer": "0"},
        ],
        layer_colors={},
    )

    assert result["contour_count"] == 3
    assert result["reference_count"] == 3
    assert result["type_distribution"] == {"CIRCLE": 3}
