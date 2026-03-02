# MCP 服务端口占用分析报告

## 问题
虽然环境变量中配置了三个端口：
- `CAD_PRICE_SEARCH_MCP_PORT=8200`
- `CAD_PARSER_MCP_PORT=8101`
- `PRICING_SERVER_MCP_PORT=8105`

但实际启动时只启动了 8200 端口，是否还会占用 8101 和 8105？

## 分析结果

### ❌ 不会占用 8101 和 8105 端口

经过代码分析，确认：

1. **实际只启动一个服务（端口 8200）**
   - 启动脚本 `start_mcp.bat` 和 `start_mcp.sh` 只启动 `cad_price_search_mcp`
   - `main.py` 也只启动 `cad_price_search_mcp` 服务

2. **8101 和 8105 的服务是独立的（但未启动）**
   - `cad_parser_mcp/server.py` - 设计端口 8101（未被调用）
   - `pricing_server_mcp/server.py` - 设计端口 8105（未被调用）
   - 这两个服务有独立的 `if __name__ == "__main__"` 入口，但没有被启动

3. **功能已整合到 8200 服务中**
   - `cad_price_search_mcp/server.py` 整合了所有功能：
     - CAD 处理功能（拆图、特征识别）
     - 价格搜索功能（12 个搜索工具）
     - 价格计算功能（23 个计算工具）
   - 总共提供 38 个工具（CAD 可用时）或 35 个工具（CAD 不可用时）

## 代码证据

### 1. 启动脚本只启动 8200

**start_mcp.bat:**
```batch
echo [INFO] 正在启动 MCP 服务...
echo [INFO] 端口: 8200
python main.py %*
```

**main.py:**
```python
def parse_args():
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CAD_PRICE_SEARCH_MCP_PORT", "8200")),
        help="监听端口（默认: 8200）"
    )
    # ...

def main():
    from cad_price_search_mcp.server import create_app
    # 只创建一个应用
    app = create_app(host=args.host, port=args.port)
    uvicorn.run(app, host=args.host, port=args.port)
```

### 2. 8101 和 8105 服务未被调用

**cad_parser_mcp/server.py:**
```python
"""
CAD解析MCP服务
端口：8101
"""
# ... 工具定义 ...

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())  # ❌ 这段代码从未被执行
```

**pricing_server_mcp/server.py:**
```python
"""
价格计算MCP服务
端口：8105
"""
# ... 工具定义 ...

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())  # ❌ 这段代码从未被执行
```

### 3. 功能已整合到 cad_price_search_mcp

**cad_price_search_mcp/server.py:**
```python
@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具 - CAD工具 + 价格工具"""
    tools = []
    
    # ========== CAD 处理工具 ==========
    cad_tools = [
        Tool(name="process_cad_and_features", ...),
        Tool(name="cad_chaitu", ...),
        Tool(name="feature_recognition", ...)
    ]
    
    # ========== 价格搜索工具 (12个) ==========
    search_tool_configs = [
        ("search_base_itemcode", ...),
        ("search_material", ...),
        # ... 共 12 个
    ]
    
    # ========== 价格计算工具 (23个) ==========
    calculate_tool_configs = [
        ("calculate_material_cost", ...),
        ("calculate_heat_treatment_cost", ...),
        # ... 共 23 个
    ]
```

## 环境变量配置的作用

虽然 `.env` 中配置了这些 URL：
```bash
CAD_PARSER_MCP_URL=http://localhost:8101
PRICING_SERVER_MCP_URL=http://localhost:8105
```

但经过搜索，**没有任何代码实际使用这些配置**：
- 没有 HTTP 请求调用这些 URL
- 没有服务启动监听这些端口
- 这些配置可能是早期设计的遗留配置

## 结论

### 当前架构
```
┌─────────────────────────────────────────┐
│  MCP 服务 (端口 8200)                    │
│  cad_price_search_mcp/server.py         │
├─────────────────────────────────────────┤
│  ✅ CAD 处理 (3 工具)                    │
│     - process_cad_and_features          │
│     - cad_chaitu                        │
│     - feature_recognition               │
├─────────────────────────────────────────┤
│  ✅ 价格搜索 (12 工具)                   │
│     - search_base_itemcode              │
│     - search_material                   │
│     - ...                               │
├─────────────────────────────────────────┤
│  ✅ 价格计算 (23 工具)                   │
│     - calculate_material_cost           │
│     - calculate_heat_treatment_cost     │
│     - ...                               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  未使用的服务 (不占用端口)               │
├─────────────────────────────────────────┤
│  ❌ cad_parser_mcp (8101)               │
│  ❌ pricing_server_mcp (8105)           │
└─────────────────────────────────────────┘
```

### 回答你的问题

**不会占用 8101 和 8105 端口。**

原因：
1. 启动脚本只启动 `cad_price_search_mcp` 服务（8200）
2. `cad_parser_mcp` 和 `pricing_server_mcp` 是独立的服务文件，但从未被启动
3. 所有功能已经整合到 8200 服务中
4. 8101 和 8105 的配置是遗留配置，没有实际使用

### 建议

1. **清理遗留配置**
   - 可以从 `.env` 中删除 `CAD_PARSER_MCP_URL` 和 `PRICING_SERVER_MCP_URL`
   - 可以从 `shared/config.py` 中删除这些配置项

2. **清理遗留代码**
   - 如果不需要独立部署，可以删除：
     - `mcp_services/cad_parser_mcp/`
     - `mcp_services/pricing_server_mcp/`

3. **更新文档**
   - 更新 `mcp_services/README.md`，说明只有一个服务（8200）
   - 删除关于 8101 和 8105 的说明

## 验证方法

可以通过以下命令验证端口占用：

```bash
# Windows
netstat -ano | findstr "8200 8101 8105"

# 应该只看到 8200 被占用，8101 和 8105 没有任何输出
```
