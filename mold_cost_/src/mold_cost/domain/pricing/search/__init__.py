"""定价搜索领域包。"""

from __future__ import annotations


def describe_legacy_search_scope() -> str:
    """返回当前搜索领域的迁移说明。"""
    return "当前 search 逻辑仍主要复用 scripts/search，后续按模块逐步下沉到本目录。"


__all__ = ["describe_legacy_search_scope"]
