"""Legacy agent factory module."""

from __future__ import annotations

import os
from typing import Optional

import requests

from shared.mcp_client import MCPClient
from shared.progress_publisher import ProgressPublisher
from shared.unified_logging import get_logger

logger = get_logger(__name__)

_cad_mcp_client: Optional[MCPClient] = None
_progress_publisher: Optional[ProgressPublisher] = None
_cad_agent = None
_pricing_agent = None
_nc_time_agent = None
_orchestrator_agent = None
_cad_agent_mcp_mode: Optional[bool] = None


def get_mcp_client() -> MCPClient:
    """Return the shared MCP client used by CAD compatibility agents."""
    global _cad_mcp_client
    if _cad_mcp_client is None:
        mcp_url = os.getenv("CAD_PRICE_SEARCH_MCP_URL", "http://localhost:8200")
        _cad_mcp_client = MCPClient(base_url=mcp_url, timeout=7200)
    return _cad_mcp_client


def get_cad_mcp_client() -> MCPClient:
    return get_mcp_client()


def get_price_search_mcp_client() -> MCPClient:
    return get_mcp_client()


def get_progress_publisher() -> ProgressPublisher:
    global _progress_publisher
    if _progress_publisher is None:
        _progress_publisher = ProgressPublisher()
    return _progress_publisher


def check_mcp_health() -> bool:
    """Best-effort MCP health check used by the remaining CAD compatibility path."""
    try:
        response = requests.get(f"{get_mcp_client().base_url}/health", timeout=3)
        if response.status_code != 200:
            return False
        return response.json().get("status") == "healthy"
    except Exception:
        return False


def get_cad_agent():
    """Return the CAD agent, still switching between MCP and local implementations."""
    global _cad_agent, _cad_agent_mcp_mode

    mcp_available = check_mcp_health()
    if _cad_agent is not None and _cad_agent_mcp_mode == mcp_available:
        return _cad_agent

    progress_publisher = get_progress_publisher()
    if mcp_available:
        from .cad_agent import CADAgent

        _cad_agent = CADAgent(
            mcp_client=get_mcp_client(),
            progress_publisher=progress_publisher,
        )
        logger.info("CADAgent created in MCP mode")
    else:
        from .cad_agent_local import CADAgentLocal

        _cad_agent = CADAgentLocal(progress_publisher=progress_publisher)
        logger.info("CADAgent created in local mode")

    _cad_agent_mcp_mode = mcp_available
    return _cad_agent


def get_pricing_agent():
    """Return the pricing compatibility wrapper backed by `pricing_service`."""
    global _pricing_agent
    if _pricing_agent is None:
        from .pricing_agent_local import PricingAgentLocal

        _pricing_agent = PricingAgentLocal(progress_publisher=get_progress_publisher())
        logger.info("PricingAgent compatibility wrapper created")
    return _pricing_agent


def get_nc_time_agent():
    global _nc_time_agent
    if _nc_time_agent is None:
        from .nc_time_agent import NCTimeAgent

        _nc_time_agent = NCTimeAgent(progress_publisher=get_progress_publisher())
    return _nc_time_agent


def get_orchestrator_agent():
    """Return the orchestrator singleton."""
    global _orchestrator_agent
    if _orchestrator_agent is None:
        from .orchestrator_agent import OrchestratorAgent

        _orchestrator_agent = OrchestratorAgent(progress_publisher=get_progress_publisher())
        _orchestrator_agent.register_agents(
            cad_agent=get_cad_agent(),
            nc_time_agent=get_nc_time_agent(),
            pricing_agent=get_pricing_agent(),
        )
    return _orchestrator_agent


from .base_agent import BaseAgent, OpResult
from .cad_agent import CADAgent
from .nc_time_agent import NCTimeAgent
from .orchestrator_agent import OrchestratorAgent
from .pricing_agent import PricingAgent

__all__ = [
    "BaseAgent",
    "CADAgent",
    "NCTimeAgent",
    "OpResult",
    "OrchestratorAgent",
    "PricingAgent",
    "check_mcp_health",
    "get_cad_agent",
    "get_cad_mcp_client",
    "get_mcp_client",
    "get_nc_time_agent",
    "get_orchestrator_agent",
    "get_price_search_mcp_client",
    "get_pricing_agent",
    "get_progress_publisher",
]

