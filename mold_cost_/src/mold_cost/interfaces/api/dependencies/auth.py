"""Src-owned API auth dependency wrappers."""

from __future__ import annotations


async def get_current_user(*args, **kwargs):
    """兼容包装：当前仍复用既有 JWT 鉴权实现，路由层不再直接依赖 api_gateway 包路径。"""
    from api_gateway.auth import get_current_user as legacy_get_current_user

    return await legacy_get_current_user(*args, **kwargs)


__all__ = ["get_current_user"]
