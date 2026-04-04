"""任务路由兼容导出。"""

from __future__ import annotations


def get_jobs_router():
    """获取主 jobs 路由。"""
    from api_gateway.routers.jobs import router

    return router


def get_legacy_jobs_router():
    """获取 legacy jobs 路由。"""
    from api_gateway.routers.jobs import router_legacy

    return router_legacy


__all__ = ["get_jobs_router", "get_legacy_jobs_router"]
