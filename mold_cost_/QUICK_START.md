# 快速开始 - 模具成本核算系统

## ⚡ 一键启动

### Windows
```bash
start.bat
```

### Linux/macOS
```bash
./start.sh
```

**这会启动：**
- ✅ API Gateway (端口 8000) - HTTP 接口
- ✅ Orchestrator Worker - 后台任务处理

**不会启动：**
- ❌ MCP 服务 - 需要单独启动（可选）

---

## 🎯 启动模式详解

### 模式 1: 完整模式（推荐）

```bash
python main.py
```

**包含：**
- ✅ API Gateway - 所有 HTTP 接口
- ✅ Worker - CAD 解析、价格计算、任务处理

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

## 🔌 MCP 服务（可选）

### 什么是 MCP？

MCP (Model Context Protocol) 是独立的微服务，提供：
- CAD 文件解析
- 特征识别
- 价格搜索和计算

### 是否需要启动？

**不是必需的，但推荐启动以获得最佳性能。**

| 场景 | 是否需要 MCP | 说明 |
|------|-------------|------|
| 前端开发 | ❌ 不需要 | 只需要 API 接口 |
| 后端开发 | ⚠️ 可选 | Worker 会使用本地脚本 |
| 完整测试 | ✅ 推荐 | 获得最佳性能 |
| 生产环境 | ✅ 推荐 | 支持分布式部署 |

### 如何启动 MCP？

**终端 1: 启动主服务**
```bash
python main.py
```

**终端 2: 启动 MCP 服务**
```bash
cd mcp_services/cad_price_search_mcp
python server.py
```

---

## 📍 访问地址

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **ReDoc**: http://localhost:8000/redoc
- **MCP 服务**: http://localhost:8200 (如果启动)

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

### 端口被占用
```bash
# 更换端口
python main.py --port 8001
```

### 服务连接失败
```bash
# 检查基础设施服务
curl http://localhost:8000/health
```

### 环境变量未加载
```bash
# 验证 .env 文件
cat .env
```

### Worker 不处理任务

**原因：** 可能没有启动 Worker

**解决：**
```bash
# 确保启动了 Worker
python main.py  # 默认包含 Worker

# 或检查日志
# 应该看到 "✅ 进度发布器初始化成功"
```

---

## 📊 功能对比

| 功能 | API Only | API + Worker | + MCP |
|------|----------|--------------|-------|
| 用户登录 | ✅ | ✅ | ✅ |
| 文件上传 | ✅ | ✅ | ✅ |
| CAD 解析 | ❌ | ⚠️ 本地 | ✅ 快速 |
| 价格计算 | ❌ | ⚠️ 本地 | ✅ 快速 |
| 任务处理 | ❌ | ✅ | ✅ |

---

## 📚 详细文档

- [架构组件说明](docs/ARCHITECTURE_COMPONENTS.md) - 详细了解各组件
- [统一启动文档](docs/UNIFIED_STARTUP.md) - 完整启动指南
- [启动流程说明](docs/STARTUP_GUIDE.md) - 传统启动方式
- [完整 README](README.md) - 项目概述

---

## 🎉 就这么简单！

**最简单的方式：**
```bash
# Windows
start.bat

# Linux/macOS
./start.sh
```

**一个命令，启动整个系统！**

**如果需要最佳性能，再启动 MCP：**
```bash
cd mcp_services/cad_price_search_mcp
python server.py
```

