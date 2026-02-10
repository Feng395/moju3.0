"""
PricingAgent - 价格计算Agent
负责人：人员E
"""
from typing import Dict, Any
from .base_agent import BaseAgent, OpResult

class PricingAgent(BaseAgent):
    """
    价格计算Agent
    调用pricing-server-mcp服务进行价格匹配和成本计算
    """
    
    def __init__(self, mcp_client):
        super().__init__("PricingAgent")
        self.mcp_client = mcp_client
    
    async def process(self, context: Dict[str, Any]) -> OpResult:
        """处理价格计算"""
        try:
            # 调用MCP服务进行价格匹配
            result = await self.mcp_client.call_tool(
                "pricing-server-mcp",
                "calculate_cost",
                {
                    "subgraphs": context.get("subgraphs"),
                    "version_id": context.get("version_id", "v1.0")
                }
            )
            
            return OpResult(
                status="ok",
                data=result,
                message="价格计算完成"
            )
        except Exception as e:
            self.logger.error(f"Pricing calculation failed: {e}")
            return OpResult(status="error", message=str(e))
