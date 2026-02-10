"""
CADAgent - CAD解析Agent
负责人：人员F
"""
from typing import Dict, Any
from .base_agent import BaseAgent, OpResult

class CADAgent(BaseAgent):
    """
    CAD解析Agent
    调用cad-parser-mcp服务进行DWG/PRT解析和拆图
    """
    
    def __init__(self, mcp_client):
        super().__init__("CADAgent")
        self.mcp_client = mcp_client
    
    async def process(self, context: Dict[str, Any]) -> OpResult:
        """处理CAD解析"""
        try:
            # 调用MCP服务解析DWG
            dwg_result = await self.mcp_client.call_tool(
                "cad-parser-mcp",
                "parse_dwg",
                {"file_path": context.get("dwg_file_path")}
            )
            
            # 调用MCP服务拆图
            split_result = await self.mcp_client.call_tool(
                "cad-parser-mcp",
                "split_subgraphs",
                {"dwg_data": dwg_result}
            )
            
            return OpResult(
                status="ok",
                data=split_result,
                message=f"成功拆分为 {len(split_result.get('subgraphs', []))} 个子图"
            )
        except Exception as e:
            self.logger.error(f"CAD parsing failed: {e}")
            return OpResult(status="error", message=str(e))
