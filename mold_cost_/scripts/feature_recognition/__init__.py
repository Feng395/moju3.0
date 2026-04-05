# -*- coding: utf-8 -*-
"""
特征识别包导出层。

这里保留 legacy 公开接口名称，同时通过惰性导入避免在包初始化阶段
直接加载重量级 `feature_recognition.py`，减少副作用扩散。
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
