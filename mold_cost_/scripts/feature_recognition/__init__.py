# -*- coding: utf-8 -*-
"""
Feature recognition package exports.

Keep the legacy public API stable while avoiding eager import of the heavy
`feature_recognition.py` module during package initialization.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "batch_feature_recognition_process",
    "analyze_dxf_features",
    "get_subgraphs_from_db",
    "save_features_to_db",
]


def __getattr__(name: str):
    # 中文说明：保持旧包导出不变，但把重型脚本的 import 延后到真正使用时。
    if name not in __all__:
        raise AttributeError(name)
    module = import_module(".feature_recognition", __name__)
    return getattr(module, name)
