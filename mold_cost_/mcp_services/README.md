# MCP Services 模块

## 📋 概述

MCP (Model Context Protocol) Services 是独立的微服务模块，提供 CAD 解析、价格计算等高性能处理能力。这些服务通过 HTTP API 被主系统调用。

## 📁 目录结构

```
mcp_services/
├── cad_parser_mcp/          # CAD 解析服务
│   └── server.py
├── cad_price_search_mcp/    # CAD 价格搜索服务（主要）
│   └── server.py
├── pricing_server_mcp/      # 价格计算服务
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
start_mcp.bat
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

### 1. CAD Price Search MCP (主要服务)

**端口**: 8200  
**功能**: CAD 文件解析和价格搜索

**提供的接口**:
- CAD 文件格式转换
- 特征识别
- 价格数据搜索
- 材料信息查询

**健康检查**:
```bash
curl http://localhost:8200/health
```

**调用示例**:
```python
import requests

# CAD 解析
response = requests.post('http://localhost:8200/parse', json={
    'file_path': 'path/to/file.dwg',
    'job_id': 'job-123'
})

# 价格搜索
response = requests.post('http://localhost:8200/search_price', json={
    'material': '45#钢',
    'process_type': 'NC'
})
```

### 2. CAD Parser MCP

**端口**: 8101  
**功能**: 专注于 CAD 文件解析

**提供的接口**:
- DWG → DXF 转换
- 图层分析
- 文本提取
- 图块识别

### 3. Pricing Server MCP

**端口**: 8105  
**功能**: 价格计算服务

**提供的接口**:
- 材料价格计算
- 加工成本计算
- 总价汇总

## ⚙️ 配置

### 环境变量

```bash
# MCP 服务端口
CAD_PRICE_SEARCH_MCP_PORT=8200
CAD_PARSER_MCP_PORT=8101
PRICING_SERVER_MCP_PORT=8105

# MCP 服务地址
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
