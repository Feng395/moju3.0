"""API 接口层统一应用入口。"""

from __future__ import annotations


def get_app():
    """懒加载当前主 API 应用。"""
    from api_gateway.main import app

    return app


app = get_app()

__all__ = ["app", "get_app"]
