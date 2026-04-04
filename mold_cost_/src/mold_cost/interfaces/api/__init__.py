"""API 接口层导出。"""

from __future__ import annotations


def get_app():
    """懒加载当前主 API 应用。"""
    from .app import get_app as _get_app

    return _get_app()


def get_legacy_cad_app():
    """懒加载历史 CAD 兼容 API 应用。"""
    from .legacy_cad_api import app as legacy_cad_app

    return legacy_cad_app


__all__ = ["get_app", "get_legacy_cad_app"]
