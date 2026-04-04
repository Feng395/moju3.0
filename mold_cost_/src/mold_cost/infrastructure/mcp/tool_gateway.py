"""MCP 工具网关。"""

from __future__ import annotations

from functools import lru_cache


class MCPToolGateway:
    """对 legacy MCP 服务做统一入口封装。"""

    @staticmethod
    @lru_cache(maxsize=1)
    def load_legacy_server_module():
        """懒加载历史 MCP 服务模块。"""
        from mcp_services.cad_price_search_mcp import server as legacy_server

        return legacy_server


tool_gateway = MCPToolGateway()
