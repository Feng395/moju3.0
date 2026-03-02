"""
Agent 模块
提供统一的 Agent 实例获取接口

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/__init__.py
- 合并策略：直接使用 mold_cost-main 版本（mold_cost_ 无此文件）
- 主要功能：
  1. 全局单例管理（支持 MCP 动态切换）
  2. MCP 客户端统一获取
  3. 各 Agent 实例获取接口
"""
from shared.unified_logging import get_logger
import logging
from typing import Optional
from shared.mcp_client import MCPClient
from shared.progress_publisher import ProgressPublisher

logger = get_logger(__name__)

# 全局单例
_cad_mcp_client: Optional[MCPClient] = None
_price_search_mcp_client: Optional[MCPClient] = None
_progress_publisher: Optional[ProgressPublisher] = None
_cad_agent = None
_pricing_agent = None
_nc_time_agent = None
_orchestrator_agent = None

# 记录上次创建 agent 时的 MCP 状态，用于检测变化
_cad_agent_mcp_mode: Optional[bool] = None
_pricing_agent_mcp_mode: Optional[bool] = None


def check_mcp_health() -> bool:
    """
    检测 MCP 服务是否可用（实时检测，不缓存）
    
    Returns:
        bool: True 表示 MCP 可用
    """
    try:
        import requests
        mcp_client = get_mcp_client()
        response = requests.get(f"{mcp_client.base_url}/health", timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                return True
    except Exception:
        pass
    return False


def get_mcp_client() -> MCPClient:
    """获取统一的 MCP 客户端单例（CAD + 价格搜索 + 计算）"""
    global _cad_mcp_client
    if _cad_mcp_client is None:
        import os
        mcp_url = os.getenv("CAD_PRICE_SEARCH_MCP_URL", "http://localhost:8200")
        _cad_mcp_client = MCPClient(base_url=mcp_url, timeout=7200)  # 2小时超时
    return _cad_mcp_client


def get_cad_mcp_client() -> MCPClient:
    """获取 CAD MCP 客户端（使用统一的 MCP 服务）"""
    return get_mcp_client()


def get_price_search_mcp_client() -> MCPClient:
    """获取 Price Search MCP 客户端（使用统一的 MCP 服务）"""
    return get_mcp_client()


def get_progress_publisher() -> ProgressPublisher:
    """获取进度发布器单例"""
    global _progress_publisher
    if _progress_publisher is None:
        _progress_publisher = ProgressPublisher()
    return _progress_publisher


def get_cad_agent():
    """
    获取 CAD Agent
    每次调用都检测 MCP 可用性，MCP 状态变化时自动切换 agent
    """
    global _cad_agent, _cad_agent_mcp_mode
    
    mcp_available = check_mcp_health()
    
    # 如果 MCP 状态没变且 agent 已存在，直接返回
    if _cad_agent is not None and _cad_agent_mcp_mode == mcp_available:
        return _cad_agent
    
    # MCP 状态变化或首次创建，重新创建 agent
    if _cad_agent is not None:
        old_mode = "MCP" if _cad_agent_mcp_mode else "本地脚本"
        new_mode = "MCP" if mcp_available else "本地脚本"
        logger.info(f"🔄 CADAgent 模式切换: {old_mode} → {new_mode}")
    
    progress_publisher = get_progress_publisher()
    
    if mcp_available:
        from .cad_agent import CADAgent
        _cad_agent = CADAgent(
            mcp_client=get_mcp_client(),
            progress_publisher=progress_publisher
        )
        logger.info("✅ CADAgent 创建成功（MCP 模式）")
    else:
        from .cad_agent_local import CADAgentLocal
        _cad_agent = CADAgentLocal(
            progress_publisher=progress_publisher
        )
        logger.info("✅ CADAgent 创建成功（本地脚本模式）")
    
    _cad_agent_mcp_mode = mcp_available
    return _cad_agent


def get_pricing_agent():
    """
    获取 Pricing Agent
    每次调用都检测 MCP 可用性，MCP 状态变化时自动切换 agent
    """
    global _pricing_agent, _pricing_agent_mcp_mode
    
    mcp_available = check_mcp_health()
    
    # 如果 MCP 状态没变且 agent 已存在，直接返回
    if _pricing_agent is not None and _pricing_agent_mcp_mode == mcp_available:
        return _pricing_agent
    
    # MCP 状态变化或首次创建，重新创建 agent
    if _pricing_agent is not None:
        old_mode = "MCP" if _pricing_agent_mcp_mode else "本地脚本"
        new_mode = "MCP" if mcp_available else "本地脚本"
        logger.info(f"🔄 PricingAgent 模式切换: {old_mode} → {new_mode}")
    
    progress_publisher = get_progress_publisher()
    
    if mcp_available:
        from .pricing_agent import PricingAgent
        _pricing_agent = PricingAgent(
            price_search_mcp_client=get_mcp_client(),
            progress_publisher=progress_publisher
        )
        logger.info("✅ PricingAgent 创建成功（MCP 模式）")
    else:
        from .pricing_agent_local import PricingAgentLocal
        _pricing_agent = PricingAgentLocal(
            progress_publisher=progress_publisher
        )
        logger.info("✅ PricingAgent 创建成功（本地脚本模式）")
    
    _pricing_agent_mcp_mode = mcp_available
    return _pricing_agent


def get_nc_time_agent():
    """获取 NCTimeAgent 单例"""
    global _nc_time_agent
    
    if _nc_time_agent is None:
        from .nc_time_agent import NCTimeAgent
        progress_publisher = get_progress_publisher()
        _nc_time_agent = NCTimeAgent(progress_publisher=progress_publisher)
    
    return _nc_time_agent


def get_orchestrator_agent():
    """
    获取 OrchestratorAgent 单例
    
    用于完整的自动化流程
    """
    global _orchestrator_agent
    
    if _orchestrator_agent is None:
        from .orchestrator_agent import OrchestratorAgent
        
        progress_publisher = get_progress_publisher()
        _orchestrator_agent = OrchestratorAgent(progress_publisher=progress_publisher)
        
        # 注册其他 Agent
        _orchestrator_agent.register_agents(
            cad_agent=get_cad_agent(),
            nc_time_agent=get_nc_time_agent(),
            pricing_agent=get_pricing_agent()
        )
    
    return _orchestrator_agent


# 导出常用的 Agent 类（供直接实例化使用）
from .base_agent import BaseAgent, OpResult
from .cad_agent import CADAgent
from .pricing_agent import PricingAgent
from .nc_time_agent import NCTimeAgent
from .orchestrator_agent import OrchestratorAgent

__all__ = [
    # 工厂函数
    "get_cad_agent",
    "get_pricing_agent",
    "get_nc_time_agent",
    "get_orchestrator_agent",
    "get_mcp_client",
    "get_progress_publisher",
    "check_mcp_health",
    
    # Agent 类
    "BaseAgent",
    "OpResult",
    "CADAgent",
    "PricingAgent",
    "NCTimeAgent",
    "OrchestratorAgent",
]
