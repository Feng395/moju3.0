"""Tests for the src-owned CAD block analyzer boundary."""

from __future__ import annotations

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_block_analyzer_initializes_src_owned_helpers():
    pytest.importorskip("ezdxf")
    from mold_cost.infrastructure.cad.block_analyzer import OptimizedCADBlockAnalyzer

    analyzer = OptimizedCADBlockAnalyzer()

    assert analyzer.text_processor.__class__.__module__ == "mold_cost.infrastructure.cad.text_processor"
    assert analyzer.cutting_detector.__class__.__module__ == "mold_cost.infrastructure.cad.cutting_detector"
    assert analyzer.number_extractor.__class__.__module__ == "mold_cost.infrastructure.cad.number_extractor"
