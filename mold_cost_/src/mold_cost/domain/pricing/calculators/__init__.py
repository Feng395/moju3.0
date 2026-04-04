"""定价计算领域包。"""

from __future__ import annotations


def describe_legacy_calculator_scope() -> str:
    """返回当前计算器领域的迁移说明。"""
    return "当前 calculators 逻辑仍主要复用 scripts/calculate，后续按模块逐步下沉到本目录。"


__all__ = ["describe_legacy_calculator_scope"]
