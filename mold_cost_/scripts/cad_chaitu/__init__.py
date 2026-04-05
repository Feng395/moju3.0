#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CAD 拆图兼容包导出。"""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "DWGConverter": ".converter",
    "ProfessionalDrawingNumberExtractor": ".number_extractor",
    "IntelligentTextProcessor": ".text_processor",
    "RelaxedCuttingDetector": ".cutting_detector",
    "OptimizedCADBlockAnalyzer": ".block_analyzer",
    "CADAnalysisSystem": ".cad_system",
    "DatabaseManager": ".database",
    "FileStorageManager": ".storage",
    "extract_model_code_from_source": ".utils",
    "chaitu_process": ".main",
    "init_managers": ".main",
}


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)


__all__ = list(_EXPORTS)
