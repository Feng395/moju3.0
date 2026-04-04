"""MCP 服务兼容入口。"""

from __future__ import annotations


def get_server_module():
    """懒加载当前 MCP 服务模块。"""
    from mcp_services.cad_price_search_mcp import server as legacy_server

    return legacy_server


__all__ = ["get_server_module"]
