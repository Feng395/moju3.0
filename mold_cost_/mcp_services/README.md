# MCP Services 模块

## 📋 概述

MCP (Model Context Protocol) Services 是独立的微服务模块，提供 CAD 解析、价格计算等高性能处理能力。这些服务通过 HTTP API 被主系统调用。

## 📁 目录结构

```
mcp_services/
├── cad_price_search_mcp/    # CAD 价格搜索服务（整合所有功能）
│   └── server.py
├── main.py                  # 统一启动入口
├── start_mcp.bat           # Windows 启动脚本
└── start_mcp.sh            # Linux/macOS 启动脚本
```

## 🚀 快速启动

### 方式1: 使用启动脚本（推荐）

**Windows:**
```bash
cd mold_cost_/mcp_services
.\start_mcp.bat
```

**Linux/macOS:**
```bash
cd mold_cost_/mcp_services
chmod +x start_mcp.sh
./start_mcp.sh
```

### 方式2: 直接启动

```bash
# 启动 CAD 价格搜索服务（端口 8200）
cd mold_cost_/mcp_services/cad_price_search_mcp
python server.py
```

### 方式3: 使用统一入口

```bash
cd mold_cost_/mcp_services
python main.py
```

## 🔌 服务说明

### CAD Price Search MCP（整合服务）

**端口**: 8200  
**功能**: 整合了 CAD 解析、价格搜索和价格计算的完整服务

**提供的功能**:
- **CAD 处理** (3 个工具)
  - 完整的 CAD 处理流程（拆图 + 特征识别）
  - 单独的 CAD 拆图功能
  - 单独的特征识别功能

- **价格搜索** (12 个工具)
  - 基础信息搜索
  - 材料信息搜索
  - 热处理信息搜索
  - 齿孔信息搜索
  - 水磨信息搜索
  - 线切割信息搜索
  - NC 信息搜索
  - 密度信息搜索
  - 等...

- **价格计算** (23 个工具)
  - 材料成本计算
  - 热处理成本计算
  - 重量计算
  - 齿孔成本计算
  - 水磨成本计算
  - 线切割成本计算
  - NC 成本计算
  - 总成本计算
  - 等...

**健康检查**:
```bash
curl http://localhost:8200/health
```

**调用示例**:
```python
import requests

# 通过 HTTP 调用工具
response = requests.post('http://localhost:8200/call_tool', json={
    'tool_name': 'process_cad_and_features',
    'arguments': {
        'job_id': 'job-123',
        'dwg_url': 'path/to/file.dwg'
    }
})

# 价格搜索
response = requests.post('http://localhost:8200/call_tool', json={
    'tool_name': 'search_material',
    'arguments': {
        'job_id': 'job-123',
        'subgraph_ids': []
    }
})
```

## ⚙️ 配置

### 环境变量

```bash
# MCP 服务配置
CAD_PRICE_SEARCH_MCP_PORT=8200
CAD_PRICE_SEARCH_MCP_HOST=0.0.0.0
CAD_PRICE_SEARCH_MCP_URL=http://localhost:8200

# ODA 转换器路径
ODA_FILE_CONVERTER_PATH=D:\\workspace\\ODA\\ODAFileConverter.exe

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mold_cost_db
```

## 🔄 与主系统集成

### 在 Agent 中调用

```python
from shared.mcp_client import MCPClient

# 创建客户端
client = MCPClient(base_url="http://localhost:8200")

# 调用 CAD 解析
result = await client.call(
    service="cad_parser",
    method="parse",
    params={"file_path": "path/to/file.dwg"}
)

# 调用价格搜索
result = await client.call(
    service="price_search",
    method="search",
    params={"material": "45#钢"}
)
```

## 🐳 Docker 部署

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY mcp_services/ ./mcp_services/

EXPOSE 8200

CMD ["python", "mcp_services/cad_price_search_mcp/server.py"]
```

### Docker Compose

```yaml
services:
  mcp_service:
    build: .
    ports:
      - "8200:8200"
    environment:
      - DB_HOST=postgres
      - ODA_FILE_CONVERTER_PATH=/opt/oda/ODAFileConverter
    volumes:
      - ./uploads:/app/uploads
    restart: always
```

## 📊 监控

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8200/health

# 预期响应
{
  "status": "healthy",
  "service": "cad_price_search_mcp",
  "version": "1.0.0"
}
```

### 日志查看

```bash
# 查看服务日志
tail -f logs/mcp_service.log
```

## 🧪 测试

### 单元测试

```bash
pytest tests/mcp_services/
```

### 集成测试

```bash
# 启动服务
python mcp_services/cad_price_search_mcp/server.py &

# 运行测试
pytest tests/integration/test_mcp_integration.py
```

## ⚠️ 常见问题

### 1. 连接被拒绝

**错误**: `[WinError 10061] 由于目标计算机积极拒绝，无法连接`

**原因**: MCP 服务未启动

**解决**: 启动 MCP 服务
```bash
cd mcp_services
start_mcp.bat  # Windows
./start_mcp.sh  # Linux/macOS
```

### 2. 端口被占用

**错误**: `Address already in use`

**解决**: 更换端口或停止占用进程
```bash
# 查找占用进程
netstat -ano | findstr :8200  # Windows
lsof -i :8200  # Linux/macOS

# 更换端口
set CAD_PRICE_SEARCH_MCP_PORT=8201
```

### 3. ODA 转换器路径错误

**错误**: `ODAFileConverter not found`

**解决**: 配置正确的 ODA 路径
```bash
# 在 .env 文件中设置
ODA_FILE_CONVERTER_PATH=D:\\workspace\\ODA\\ODAFileConverter.exe
```

## 📚 相关文档

- [Agents 文档](../agents/README.md)
- [Scripts 文档](../scripts/README.md)
- [主项目文档](../README.md)
- [快速开始](../QUICK_START.md)

## 🤝 贡献指南

1. 遵循微服务架构原则
2. 保持服务独立性
3. 添加健康检查接口
4. 编写 API 文档
5. 实现错误处理

## 📞 联系方式

如有问题，请联系 MCP Services 团队或提交 Issue。
