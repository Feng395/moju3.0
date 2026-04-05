"""Tests for the src-owned CAD drawing number extractor."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_number_extractor_prefers_explicit_number_label():
    from mold_cost.infrastructure.cad.number_extractor import ProfessionalDrawingNumberExtractor

    extractor = ProfessionalDrawingNumberExtractor()
    result = extractor.extract_region_filename_by_patterns(
        {
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100},
            "texts": [
                {"content": "编号: PS-01", "position": (10, 90), "layer": "0"},
                {"content": "尺寸 100", "position": (50, 50), "layer": "dim"},
            ],
        }
    )

    assert result == "PS-01"


def test_number_extractor_falls_back_to_top_left_code():
    from mold_cost.infrastructure.cad.number_extractor import ProfessionalDrawingNumberExtractor

    extractor = ProfessionalDrawingNumberExtractor()
    result = extractor.extract_region_filename_by_patterns(
        {
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 200, "max_y": 200},
            "texts": [
                {"content": "PS-09", "position": (10, 190), "layer": "0"},
                {"content": "加工说明", "position": (120, 80), "layer": "0"},
            ],
        }
    )

    assert result == "PS-09"


def test_number_extractor_filters_dimension_noise_for_backup_path():
    from mold_cost.infrastructure.cad.number_extractor import ProfessionalDrawingNumberExtractor

    extractor = ProfessionalDrawingNumberExtractor()
    result = extractor.extract_drawing_number_from_region(
        {
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 120, "max_y": 120},
            "texts": [
                {"content": "100.0", "position": (40, 60), "layer": "0"},
                {"content": "B12", "position": (12, 108), "layer": "0"},
                {"content": "M8", "position": (50, 45), "layer": "0"},
            ],
        }
    )

    assert result == "B12"
