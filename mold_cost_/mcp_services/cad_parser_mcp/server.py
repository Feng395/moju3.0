"""
CAD解析MCP服务
负责人：人员D
端口：8101
"""
from mcp.server import Server
from mcp.types import Tool, TextContent
import json

app = Server("cad-parser-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="parse_dwg",
            description="解析DWG文件，提取图层、实体、标注等信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "DWG文件路径"}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="parse_prt",
            description="解析PRT文件，提取3D实体信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "PRT文件路径"}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="split_subgraphs",
            description="拆分子图（按图层、封闭轮廓、空间位置）",
            inputSchema={
                "type": "object",
                "properties": {
                    "dwg_data": {"type": "object", "description": "DWG解析数据"},
                    "strategy": {
                        "type": "string",
                        "enum": ["layer", "contour", "spatial"],
                        "description": "拆图策略"
                    }
                },
                "required": ["dwg_data"]
            }
        ),
        Tool(
            name="extrude_2d",
            description="2D转3D拉伸（第二期功能）",
            inputSchema={
                "type": "object",
                "properties": {
                    "contour": {"type": "object", "description": "2D轮廓"},
                    "height": {"type": "number", "description": "拉伸高度(mm)"}
                },
                "required": ["contour", "height"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """调用工具"""
    if name == "parse_dwg":
        # TODO: 实现DWG解析逻辑
        result = {"layers": [], "entities": []}
        return [TextContent(type="text", text=json.dumps(result))]
    
    elif name == "split_subgraphs":
        # TODO: 实现拆图逻辑
        result = {"subgraphs": []}
        return [TextContent(type="text", text=json.dumps(result))]
    
    return [TextContent(type="text", text="Tool not implemented")]

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
