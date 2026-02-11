# 快速开始 - 模具成本核算系统

## ⚡ 完整启动（两个终端）

### ⚠️ 重要：需要启动两个服务

系统需要在**两个终端窗口**中分别启动：

#### 终端 1: 主服务（API + Worker）

**Windows:**
```bash
cd mold_cost_
start.bat
```

**Linux/macOS:**
```bash
cd mold_cost_
./start.sh
```

#### 终端 2: MCP 服务（CAD 解析 + 价格计算）

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

### 启动说明

**终端 1 启动：**
- ✅ API Gateway (端口 8000) - HTTP 接口
- ✅ Orchestrator Worker - 后台任务处理

**终端 2 启动：**
- ✅ MCP 服务 (端口 8200) - CAD 解析、价格计算

**如果只启动终端 1：**
- ✅ API 接口可用
- ❌ CAD 解析失败（连接错误）
- ❌ 价格计算失败（连接错误）

---

## 🎯 启动模式详解

### 模式 1: 完整模式（推荐）⭐

**终端 1:**
```bash
python main.py
```

**终端 2:**
```bash
cd mcp_services
start_mcp.bat  # Windows
./start_mcp.sh  # Linux/macOS
```

**包含：**
- ✅ API Gateway - 所有 HTTP 接口
- ✅ Worker - CAD 解析、价格计算、任务处理
- ✅ MCP 服务 - 高性能 CAD 和价格处理

**适合：**
- 完整功能测试
- 后端开发
- 生产环境

### 模式 2: 仅 API（前端开发）

```bash
python main.py --api-only
```

**包含：**
- ✅ API Gateway - 所有 HTTP 接口
- ❌ Worker - 不处理后台任务
- ❌ MCP 服务 - 不需要

**适合：**
- 前端开发
- API 测试
- 不需要 CAD 解析和价格计算

### 模式 3: 仅 Worker（后台任务）

```bash
python main.py --worker-only
```

**包含：**
- ❌ API Gateway
- ✅ Worker - 后台任务处理

**适合：**
- 独立 Worker 节点
- 分布式部署

### 模式 4: 指定端口

```bash
python main.py --port 8211
```

---

## 🔌 MCP 服务（必需）

### 什么是 MCP？

MCP (Model Context Protocol) 是独立的微服务，提供：
- CAD 文件解析（DWG → DXF）
- 特征识别
- 价格搜索和计算

### ⚠️ 是否需要启动？

**是的，必须启动！** 否则会出现连接错误：

```
[WinError 10061] 由于目标计算机积极拒绝，无法连接。
HTTPConnectionPool(host='localhost', port=8200): Max retries exceeded
```

### 如何启动 MCP？

**方式 1: 使用启动脚本（推荐）**

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

**方式 2: 直接启动**

```bash
cd mold_cost_/mcp_services/cad_price_search_mcp
python server.py
```

### 启动顺序

**推荐顺序：**
1. 先启动 MCP 服务（终端 2）
2. 再启动主服务（终端 1）

**也可以反过来：**
1. 先启动主服务（终端 1）
2. 再启动 MCP 服务（终端 2）

Worker 会自动重试连接 MCP 服务。

---

## 📍 访问地址

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **ReDoc**: http://localhost:8000/redoc
- **MCP 服务健康检查**: http://localhost:8200/health

### 验证服务启动

```bash
# 检查主服务
curl http://localhost:8000/health

# 检查 MCP 服务
curl http://localhost:8200/health
```

---

## ✅ 前置检查

- [ ] PostgreSQL 已启动 (端口 5432)
- [ ] Redis 已启动 (端口 6379)
- [ ] RabbitMQ 已启动 (端口 5672)
- [ ] MinIO 已启动 (端口 9000)
- [ ] `.env` 文件已配置

---

## 🔧 环境配置

最小配置 `.env`:

```bash
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mold_cost
DB_USER=postgres
DB_PASSWORD=root

# Redis
REDIS_URL=redis://localhost:6379

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET=mold-cost
MINIO_BUCKET_FILES=mold-cost

# ODA Converter
ODA_FILE_CONVERTER_PATH=D:\\workspace\\ODA\\ODAFileConverter.exe

# MCP 服务地址（可选）
CAD_PRICE_SEARCH_MCP_URL=http://localhost:8200
```

---

## 🚨 常见问题

### 连接错误：端口 8200 被拒绝

**错误信息：**
```
[WinError 10061] 由于目标计算机积极拒绝，无法连接。
HTTPConnectionPool(host='localhost', port=8200): Max retries exceeded
```

**原因：** MCP 服务没有启动

**解决：** 在新终端启动 MCP 服务
```bash
cd mold_cost_/mcp_services
start_mcp.bat  # Windows
./start_mcp.sh  # Linux/macOS
```

### 端口被占用
```bash
# 更换主服务端口
python main.py --port 8001

# 更换 MCP 端口（需要同步修改 .env）
set CAD_PRICE_SEARCH_MCP_PORT=8201  # Windows
export CAD_PRICE_SEARCH_MCP_PORT=8201  # Linux/macOS
```

### 服务连接失败
```bash
# 检查基础设施服务
curl http://localhost:8000/health
curl http://localhost:8200/health
```

### 环境变量未加载
```bash
# 验证 .env 文件
cat .env
```

### Worker 不处理任务

**原因：** 可能没有启动 Worker 或 MCP 服务

**解决：**
```bash
# 确保启动了 Worker
python main.py  # 默认包含 Worker

# 确保启动了 MCP 服务
cd mcp_services
start_mcp.bat  # Windows
```

---

## 📊 功能对比

| 功能 | API Only | API + Worker | API + Worker + MCP |
|------|----------|--------------|-------------------|
| 用户登录 | ✅ | ✅ | ✅ |
| 文件上传 | ✅ | ✅ | ✅ |
| CAD 解析 | ❌ | ❌ 连接错误 | ✅ 正常 |
| 价格计算 | ❌ | ❌ 连接错误 | ✅ 正常 |
| 任务处理 | ❌ | ⚠️ 部分失败 | ✅ 正常 |

**结论：** 完整功能需要同时启动主服务和 MCP 服务

---

## 📚 详细文档

- [MCP 启动指南](docs/MCP_STARTUP_GUIDE.md) - **解决连接错误的完整指南**
- [架构组件说明](docs/architecture/ARCHITECTURE_COMPONENTS.md) - 详细了解各组件
- [统一启动文档](docs/UNIFIED_STARTUP.md) - 完整启动指南
- [MCP 调用流程](docs/mcp/MCP_CALL_FLOW.md) - MCP 调用机制详解
- [完整 README](README.md) - 项目概述

---

## 🎉 快速启动总结

**最简单的方式（两个终端）：**

**终端 1:**
```bash
cd mold_cost_
start.bat  # Windows
./start.sh  # Linux/macOS
```

**终端 2:**
```bash
cd mold_cost_/mcp_services
start_mcp.bat  # Windows
./start_mcp.sh  # Linux/macOS
```

**两个命令，启动完整系统！** ✅

