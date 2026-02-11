# 模具成本核算系统 (Mold Cost Accounting System)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基于AI Agent的智能模具成本核算系统，实现从CAD文件上传到成本报表生成的全自动化流程。系统采用FastAPI异步架构，集成了用户认证、工艺规则管理、价格计算、实时通信等完整功能。

---

## 📋 目录

- [系统概述](#系统概述)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [端口说明](#端口说明)
- [API接口](#api接口)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [部署说明](#部署说明)
- [文档导航](#文档导航)

---

## 🎯 系统概述

模具成本核算系统是一个智能化的成本核算平台，通过AI Agent自动化处理CAD文件，识别特征，计算价格，生成报表。系统支持多用户协作，实时进度推送，完整的审核流程。

### 主要特点

✅ **智能化处理**: AI Agent自动识别CAD特征，智能计算成本  
✅ **异步架构**: FastAPI + asyncpg，高性能异步处理  
✅ **实时通信**: WebSocket + SSE，实时进度推送  
✅ **完整认证**: JWT Token + bcrypt，安全可靠  
✅ **工艺管理**: 灵活的工艺规则和价格配置  
✅ **审核流程**: 完整的任务审核和修改流程  
✅ **文件管理**: MinIO对象存储，支持大文件上传  
✅ **消息队列**: RabbitMQ异步任务处理  

---


## 🚀 核心功能

### 1. 用户认证与权限管理
- 用户登录/登出
- JWT Token认证
- 密码加密（bcrypt + SHA256兼容）
- 登录失败锁定机制
- Token自动刷新（可选）

### 2. CAD文件处理
- 支持.dwg、.prt格式
- 文件上传（最大100MB）
- MinIO对象存储
- 预签名URL生成
- 文件下载和管理

### 3. 智能特征识别
- AI Agent自动识别CAD特征
- 支持多种加工工艺
- 特征参数提取
- 工艺规则匹配

### 4. 成本计算
- 材料成本计算
- 加工成本计算
- NC时间计算
- 水磨、线割等工艺成本
- 总成本汇总

### 5. 工艺规则管理
- 工艺规则CRUD
- 规则版本管理
- 批量操作
- 软删除支持

### 6. 价格项管理
- 价格项CRUD
- 价格版本管理
- 分类管理
- Decimal精度保持

### 7. 聊天会话管理
- 会话创建和管理
- 会话历史记录
- 级联删除（18个关联表）
- 批量操作

### 8. 实时通信
- WebSocket连接
- SSE流式推送
- 进度实时更新
- 多客户端同步

### 9. 审核流程
- 任务提交审核
- 审核通过/驳回
- 修改记录追踪
- 审核历史查询

### 10. 报表导出
- Excel报表生成
- PDF报表生成
- 自定义报表模板
- 批量导出

---

## 🚀 快速开始

### 前置要求

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- RabbitMQ 3.8+
- MinIO (或兼容S3的对象存储)

### 统一启动（推荐）⭐

系统已集成所有服务到单一启动入口，一键启动所有功能。

#### Windows

```bash
# 1. 克隆项目
git clone <repository-url>
cd mold_cost_

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
copy .env.example .env
# 编辑 .env 文件，配置数据库、Redis、RabbitMQ、MinIO等

# 4. 启动所有服务（默认端口 8000）
start.bat

# 或指定端口
start.bat --port 8211

# 仅启动 API Gateway（适合前端开发）
start.bat --api-only
```

#### Linux/macOS

```bash
# 1. 克隆项目
git clone <repository-url>
cd mold_cost_

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库、Redis、RabbitMQ、MinIO等

# 4. 添加执行权限
chmod +x start.sh

# 5. 启动所有服务（默认端口 8000）
./start.sh

# 或指定端口
./start.sh --port 8211

# 仅启动 API Gateway（适合前端开发）
./start.sh --api-only
```

#### 直接使用 Python

```bash
# 启动所有服务（API Gateway + Worker）
python main.py

# 指定端口
python main.py --port 8000

# 仅启动 API Gateway
python main.py --api-only

# 仅启动 Worker
python main.py --worker-only
```

### 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 访问 API 文档
# http://localhost:8000/docs

# 访问 ReDoc
# http://localhost:8000/redoc
```

### 传统启动方式（不推荐）

如果需要分别启动各个服务：

**终端 1 - API Gateway:**
```bash
cd mold_cost_
uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - Orchestrator Worker:**
```bash
cd mold_cost_
python workers/orchestrator_worker.py
```

---

## 🔌 端口说明

### 统一端口方案（推荐）

| 服务 | 端口 | 说明 |
|------|------|------|
| **统一入口** | **8000** | API Gateway + Worker（推荐） |
| API 文档 | 8000/docs | Swagger UI |
| ReDoc | 8000/redoc | API 文档（ReDoc风格） |
| 健康检查 | 8000/health | 服务状态检查 |

### 基础设施端口

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存和会话 |
| RabbitMQ | 5672 | 消息队列 |
| RabbitMQ 管理界面 | 15672 | Web管理界面 |
| MinIO | 9000 | 对象存储 |
| MinIO 控制台 | 9001 | Web控制台 |

### 旧端口方案（已废弃）

| 服务 | 旧端口 | 新端口 | 状态 |
|------|--------|--------|------|
| API Gateway | 8211 | 8000 | ✅ 已迁移 |
| CAD Price Search MCP | 8200 | - | ✅ 已集成 |

---


## 🏗️ 技术架构

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 编程语言 |
| **FastAPI** | 0.104+ | Web框架 |
| **asyncpg** | 0.29+ | 异步PostgreSQL驱动 |
| **Pydantic** | 2.0+ | 数据验证 |
| **LangChain** | 最新 | AI Agent框架 |
| **LangGraph** | 最新 | Agent编排 |

### 数据存储

| 技术 | 版本 | 用途 |
|------|------|------|
| **PostgreSQL** | 14+ | 主数据库 |
| **Redis** | 7+ | 缓存和会话 |
| **MinIO** | 最新 | 对象存储 |

### 消息队列

| 技术 | 版本 | 用途 |
|------|------|------|
| **RabbitMQ** | 3.12+ | 异步任务队列 |

### 认证与安全

| 技术 | 用途 |
|------|------|
| **JWT** | Token认证 |
| **bcrypt** | 密码加密 |
| **CORS** | 跨域支持 |

### 前端技术栈（可选）

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18+ | UI框架 |
| **TypeScript** | 5+ | 类型安全 |
| **Ant Design** | 5+ | UI组件库 |

### 系统架构图

```
┌─────────────┐
│   前端应用   │
│  (React)    │
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌─────────────────────────────────────┐
│         API Gateway (FastAPI)        │
│  ┌──────────┬──────────┬──────────┐ │
│  │  认证    │  文件    │  任务    │ │
│  │  路由    │  路由    │  路由    │ │
│  └──────────┴──────────┴──────────┘ │
└───┬─────────┬─────────┬─────────┬───┘
    │         │         │         │
    ▼         ▼         ▼         ▼
┌────────┐┌────────┐┌────────┐┌────────┐
│PostgreSQL││ Redis  ││RabbitMQ││ MinIO  │
└────────┘└────────┘└────────┘└────────┘
    │                    │
    │                    ▼
    │            ┌──────────────┐
    │            │  AI Agents   │
    │            │  (Workers)   │
    │            └──────────────┘
    │                    │
    └────────────────────┘
```

---


## ⚡ 快速开始

### 前置要求

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- RabbitMQ 3.12+
- MinIO (或使用Docker Compose)
- Git

### 1. 克隆项目

```bash
git clone <repository-url>
cd mold_cost_
```

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库和服务连接：

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mold_cost_db
DB_USER=root
DB_PASSWORD=yunzai123

# Redis配置
REDIS_URL=redis://localhost:6379

# RabbitMQ配置
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=Admin@123

# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# JWT配置
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120

# 日志配置
LOG_LEVEL=INFO
```

### 4. 启动基础设施（使用Docker Compose）

```bash
cd infrastructure
docker-compose up -d
```

这将启动：
- PostgreSQL (端口5432)
- Redis (端口6379)
- RabbitMQ (端口5672, 管理界面15672)
- MinIO (端口9000, 控制台9001)

### 5. 初始化数据库

```bash
# 执行数据库初始化脚本
psql -h localhost -U root -d mold_cost_db -f infrastructure/init-db.sql
```

### 6. 启动API网关

```bash
# 方式1: 使用启动脚本
./start_api_gateway.sh

# 方式2: 直接使用uvicorn
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. 访问系统

- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **RabbitMQ管理**: http://localhost:15672 (guest/guest)
- **MinIO控制台**: http://localhost:9001 (minioadmin/minioadmin)

### 8. 测试登录

使用默认管理员账号：

```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

---


## 🔌 端口说明

### 应用服务端口

| 服务 | 端口 | 说明 | 访问地址 |
|------|------|------|----------|
| **API Gateway** | 8000 | 主API服务 | http://localhost:8000 |
| **API文档** | 8000 | Swagger UI | http://localhost:8000/docs |
| **ReDoc文档** | 8000 | ReDoc UI | http://localhost:8000/redoc |

### 基础设施端口

| 服务 | 端口 | 说明 | 访问地址 |
|------|------|------|----------|
| **PostgreSQL** | 5432 | 数据库 | localhost:5432 |
| **Redis** | 6379 | 缓存 | localhost:6379 |
| **RabbitMQ** | 5672 | 消息队列 | localhost:5672 |
| **RabbitMQ管理** | 15672 | 管理界面 | http://localhost:15672 |
| **MinIO API** | 9000 | 对象存储API | http://localhost:9000 |
| **MinIO控制台** | 9001 | 管理控制台 | http://localhost:9001 |

### MCP服务端口（可选）

| 服务 | 端口 | 说明 |
|------|------|------|
| CAD Parser MCP | 8101 | CAD解析服务 |
| Feature Recognition MCP | 8102 | 特征识别服务 |
| NC Connector MCP | 8103 | NC连接服务 |
| Pricing Server MCP | 8105 | 价格计算服务 |
| Report Generator MCP | 8107 | 报表生成服务 |

### 监控端口（可选）

| 服务 | 端口 | 说明 |
|------|------|------|
| Prometheus | 9090 | 监控指标 |
| Grafana | 3000 | 可视化面板 |

---


## 📡 API接口

### 接口概览

系统提供以下API模块，共计 **50+** 个接口：

| 模块 | 端点数 | 说明 |
|------|--------|------|
| 认证模块 | 4 | 登录、Token验证、密码修改 |
| 任务管理 | 8 | 任务创建、查询、更新、删除 |
| 文件管理 | 6 | 文件上传、下载、预签名URL |
| 工艺规则 | 9 | 工艺规则CRUD、批量操作 |
| 价格项 | 9 | 价格项CRUD、批量操作 |
| 聊天会话 | 7 | 会话管理、历史记录 |
| 特征识别 | 5 | 特征提取、识别结果 |
| 价格计算 | 6 | 成本计算、价格查询 |
| 报表导出 | 4 | Excel/PDF导出 |
| 审核流程 | 5 | 审核提交、通过、驳回 |
| 实时通信 | 3 | WebSocket、SSE |

### 1. 认证模块 (Authentication)

#### 1.1 用户登录
```http
POST /api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**响应**:
```json
{
  "success": true,
  "message": "登录成功",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_info": {
    "user_id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

#### 1.2 Token验证
```http
POST /api/verify-token
Content-Type: application/json

{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### 1.3 修改密码
```http
POST /api/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_password": "newpassword123"
}
```

### 2. 任务管理 (Jobs)

#### 2.1 创建任务
```http
POST /api/v1/jobs
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_name": "模具001",
  "description": "测试任务"
}
```

#### 2.2 获取任务列表
```http
GET /api/v1/jobs?page=1&page_size=10&status=pending
Authorization: Bearer <token>
```

#### 2.3 获取任务详情
```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <token>
```

#### 2.4 更新任务
```http
PUT /api/v1/jobs/{job_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_name": "模具001-修改",
  "status": "processing"
}
```

#### 2.5 删除任务
```http
DELETE /api/v1/jobs/{job_id}
Authorization: Bearer <token>
```

### 3. 文件管理 (Files)

#### 3.1 上传文件
```http
POST /api/v1/files/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary>
job_id: <uuid>
```

#### 3.2 获取预签名URL
```http
GET /api/v1/files/presigned-url?file_path=uploads/test.dwg
Authorization: Bearer <token>
```

#### 3.3 下载文件
```http
GET /api/v1/files/download/{file_id}
Authorization: Bearer <token>
```

### 4. 工艺规则 (Process Rules)

#### 4.1 创建工艺规则
```http
POST /api/process-rules
Authorization: Bearer <token>
Content-Type: application/json

{
  "rule_name": "慢丝割一修一",
  "feature_type": "wire_cut",
  "conditions": {
    "slow_and_one": true
  },
  "version_id": "v1.0"
}
```

#### 4.2 获取规则列表
```http
GET /api/process-rules?page=1&page_size=10&version_id=v1.0
Authorization: Bearer <token>
```

#### 4.3 更新规则
```http
PUT /api/process-rules/{rule_id}
Authorization: Bearer <token>
```

#### 4.4 删除规则
```http
DELETE /api/process-rules/{rule_id}
Authorization: Bearer <token>
```

#### 4.5 批量删除
```http
POST /api/process-rules/batch-delete
Authorization: Bearer <token>
Content-Type: application/json

{
  "rule_ids": ["uuid1", "uuid2"]
}
```

### 5. 价格项 (Price Items)

#### 5.1 创建价格项
```http
POST /api/price-items
Authorization: Bearer <token>
Content-Type: application/json

{
  "item_name": "材料单价",
  "category": "material",
  "unit_price": 100.50,
  "version_id": "v1.0"
}
```

#### 5.2 获取价格项列表
```http
GET /api/price-items?page=1&page_size=10&category=material
Authorization: Bearer <token>
```

### 6. 聊天会话 (Chat Sessions)

#### 6.1 获取会话列表
```http
GET /api/chat-sessions?user_id=<uuid>&limit=10
Authorization: Bearer <token>
```

#### 6.2 更新会话名称
```http
PUT /api/chat-sessions/{session_id}/name
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_name": "新会话名称"
}
```

#### 6.3 删除会话
```http
DELETE /api/chat-sessions/{session_id}
Authorization: Bearer <token>
```

### 7. 实时通信

#### 7.1 WebSocket连接
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{job_id}?token=<token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('进度更新:', data);
};
```

#### 7.2 SSE流式推送
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/chat/stream?job_id=<uuid>&token=<token>'
);

eventSource.onmessage = (event) => {
  console.log('消息:', event.data);
};
```

### 完整API文档

访问 **http://localhost:8000/docs** 查看完整的交互式API文档（Swagger UI）

---


## 📁 项目结构

```
mold_cost_/
├── api_gateway/                    # API网关服务
│   ├── routers/                    # 路由模块
│   │   ├── account/                # 账户系统路由
│   │   │   ├── auth.py             # 认证路由
│   │   │   ├── process_rules.py   # 工艺规则路由
│   │   │   ├── price_items.py     # 价格项路由
│   │   │   └── chat_sessions.py   # 聊天会话路由
│   │   ├── jobs.py                 # 任务管理路由
│   │   ├── file_router.py          # 文件管理路由
│   │   ├── interactions.py         # 交互路由
│   │   ├── review_router.py        # 审核路由
│   │   ├── chat_router.py          # 聊天路由
│   │   ├── features.py             # 特征识别路由
│   │   ├── pricing.py              # 价格计算路由
│   │   ├── reports.py              # 报表导出路由
│   │   └── websocket_router.py     # WebSocket路由
│   ├── services/                   # 服务层
│   │   ├── account/                # 账户系统服务
│   │   │   ├── auth_service.py     # 认证服务
│   │   │   ├── process_rule_service.py  # 工艺规则服务
│   │   │   ├── price_item_service.py    # 价格项服务
│   │   │   └── chat_session_service.py  # 聊天会话服务
│   │   ├── job_service.py          # 任务服务
│   │   ├── file_service.py         # 文件服务
│   │   └── interaction_service.py  # 交互服务
│   ├── models/                     # 数据模型
│   │   ├── account/                # 账户系统模型
│   │   │   ├── auth_models.py      # 认证模型
│   │   │   ├── process_rule_models.py   # 工艺规则模型
│   │   │   ├── price_item_models.py     # 价格项模型
│   │   │   └── chat_session_models.py   # 聊天会话模型
│   │   └── interaction_models.py   # 交互模型
│   ├── repositories/               # 数据访问层
│   │   ├── job_repository.py       # 任务仓储
│   │   ├── interaction_repository.py    # 交互仓储
│   │   ├── review_repository.py    # 审核仓储
│   │   └── ...
│   ├── utils/                      # 工具函数
│   │   ├── account/                # 账户系统工具
│   │   │   ├── password.py         # 密码加密
│   │   │   └── jwt_helper.py       # JWT工具
│   │   ├── rabbitmq_client.py      # RabbitMQ客户端
│   │   ├── redis_client.py         # Redis客户端
│   │   ├── minio_client.py         # MinIO客户端
│   │   └── ...
│   ├── dependencies.py             # 依赖注入
│   ├── config.py                   # 配置管理
│   ├── main.py                     # 主入口
│   └── websocket.py                # WebSocket管理
├── agents/                         # AI Agent层
│   ├── action_handlers/            # 动作处理器
│   │   ├── base_handler.py         # 基础处理器
│   │   ├── feature_recognition_handler.py  # 特征识别
│   │   ├── price_calculation_handler.py    # 价格计算
│   │   └── ...
│   ├── orchestrator_agent.py       # 编排Agent
│   ├── interaction_agent.py        # 交互Agent
│   ├── decision_agent.py           # 决策Agent
│   ├── cad_agent.py                # CAD处理Agent
│   ├── pricing_agent.py            # 价格Agent
│   └── ...
├── shared/                         # 共享模块
│   ├── database.py                 # 数据库连接
│   ├── models.py                   # 共享模型
│   ├── schemas.py                  # 共享Schema
│   ├── logging_config.py           # 日志配置
│   ├── security.py                 # 安全工具
│   ├── permissions.py              # 权限管理
│   └── validators/                 # 验证器
│       ├── business_validator.py   # 业务验证
│       ├── completeness_validator.py    # 完整性验证
│       └── ...
├── scripts/                        # 脚本工具
│   ├── cad_chaitu/                 # CAD拆图
│   ├── calculate/                  # 价格计算
│   ├── feature_recognition/        # 特征识别
│   └── search/                     # 搜索工具
├── workers/                        # 后台Worker
│   ├── orchestrator_worker.py      # 编排Worker
│   ├── pricing_recalculate_worker.py    # 价格重算Worker
│   └── all_tasks_worker.py         # 全任务Worker
├── consumers/                      # 消息消费者
│   └── review_consumer.py          # 审核消费者
├── mcp_services/                   # MCP服务（可选）
│   ├── cad_parser_mcp/             # CAD解析服务
│   ├── pricing_server_mcp/         # 价格计算服务
│   └── ...
├── infrastructure/                 # 基础设施
│   ├── docker-compose.yml          # Docker编排
│   ├── init-db.sql                 # 数据库初始化
│   └── add-comments.sql            # 数据库注释
├── docs/                           # 文档
│   ├── NC_3D_Workflow_API_Reference.md  # API参考
│   ├── QUICK_START.md              # 快速开始
│   └── ...
├── tests/                          # 测试
├── examples/                       # 示例代码
├── logs/                           # 日志文件
├── .env                            # 环境变量
├── .env.example                    # 环境变量示例
├── requirements.txt                # Python依赖
├── start_api_gateway.sh            # 启动脚本
└── README.md                       # 本文件
```

---


## 💻 开发指南

### 环境配置

#### 1. Python环境

```bash
# 推荐使用pyenv管理Python版本
pyenv install 3.11.0
pyenv local 3.11.0

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 如果有
```

#### 2. 数据库配置

```bash
# 创建数据库
createdb -U postgres mold_cost_db

# 执行初始化脚本
psql -U postgres -d mold_cost_db -f infrastructure/init-db.sql

# 添加注释
psql -U postgres -d mold_cost_db -f infrastructure/add-comments.sql
```

#### 3. 环境变量

复制 `.env.example` 到 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 代码规范

#### Python代码风格

- 遵循 PEP 8 规范
- 使用 Black 格式化代码
- 使用 isort 排序导入
- 使用 flake8 检查代码质量
- 使用 mypy 进行类型检查

```bash
# 格式化代码
black .

# 排序导入
isort .

# 检查代码
flake8 .

# 类型检查
mypy .
```

#### 提交规范

使用 Conventional Commits 规范：

```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

示例：
```bash
git commit -m "feat: 添加工艺规则批量删除功能"
git commit -m "fix: 修复登录失败次数统计错误"
git commit -m "docs: 更新API文档"
```

### 测试

#### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_auth.py

# 运行特定测试函数
pytest tests/test_auth.py::test_login

# 生成覆盖率报告
pytest --cov=api_gateway --cov-report=html
```

#### 编写测试

```python
import pytest
from fastapi.testclient import TestClient
from api_gateway.main import app

client = TestClient(app)

def test_login_success():
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
```

### 调试

#### 使用VSCode调试

创建 `.vscode/launch.json`：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "api_gateway.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

#### 日志调试

```python
from shared.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 添加新功能

#### 1. 添加新的API端点

```python
# api_gateway/routers/my_feature.py
from fastapi import APIRouter, Depends
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/my-feature", tags=["我的功能"])

@router.get("/")
async def get_items(current_user = Depends(get_current_user)):
    """获取项目列表"""
    return {"items": []}
```

#### 2. 注册路由

```python
# api_gateway/main.py
from .routers import my_feature

app.include_router(my_feature.router)
```

#### 3. 添加服务层

```python
# api_gateway/services/my_service.py
class MyService:
    async def get_items(self):
        # 业务逻辑
        return []
```

#### 4. 添加数据模型

```python
# api_gateway/models/my_models.py
from pydantic import BaseModel

class MyItem(BaseModel):
    id: str
    name: str
```

### 性能优化

#### 1. 数据库查询优化

```python
# 使用索引
# 批量查询
# 避免N+1查询
# 使用连接池
```

#### 2. 缓存策略

```python
from api_gateway.utils.redis_client import redis_client

# 缓存查询结果
async def get_cached_data(key: str):
    cached = await redis_client.get(key)
    if cached:
        return cached
    
    data = await fetch_from_db()
    await redis_client.set(key, data, expire=3600)
    return data
```

#### 3. 异步处理

```python
# 使用异步函数
async def process_task():
    result = await async_operation()
    return result

# 并发处理
import asyncio
results = await asyncio.gather(
    task1(),
    task2(),
    task3()
)
```

---


## 🚀 部署说明

### 生产环境部署

#### 1. 环境准备

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv postgresql-client redis-tools

# 创建应用目录
sudo mkdir -p /opt/mold_cost
sudo chown $USER:$USER /opt/mold_cost
cd /opt/mold_cost
```

#### 2. 部署应用

```bash
# 克隆代码
git clone <repository-url> .

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 修改生产环境配置
```

#### 3. 配置Systemd服务

创建 `/etc/systemd/system/mold-cost-api.service`：

```ini
[Unit]
Description=Mold Cost API Gateway
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/mold_cost
Environment="PATH=/opt/mold_cost/venv/bin"
ExecStart=/opt/mold_cost/venv/bin/uvicorn api_gateway.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable mold-cost-api
sudo systemctl start mold-cost-api
sudo systemctl status mold-cost-api
```

#### 4. 配置Nginx反向代理

创建 `/etc/nginx/sites-available/mold-cost`：

```nginx
upstream mold_cost_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 日志
    access_log /var/log/nginx/mold-cost-access.log;
    error_log /var/log/nginx/mold-cost-error.log;

    # 客户端最大上传大小
    client_max_body_size 100M;

    # API代理
    location /api {
        proxy_pass http://mold_cost_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket代理
    location /ws {
        proxy_pass http://mold_cost_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 静态文件（如果有前端）
    location / {
        root /opt/mold_cost/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/mold-cost /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Docker部署

#### 1. 构建镜像

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

构建镜像：

```bash
docker build -t mold-cost-api:latest .
```

#### 2. 使用Docker Compose

创建 `docker-compose.prod.yml`：

```yaml
version: '3.8'

services:
  api:
    image: mold-cost-api:latest
    container_name: mold_cost_api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=postgres
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_HOST=rabbitmq
      - MINIO_ENDPOINT=minio:9000
    depends_on:
      - postgres
      - redis
      - rabbitmq
      - minio
    networks:
      - mold_cost_network

  postgres:
    image: postgres:15-alpine
    container_name: mold_cost_postgres
    restart: always
    environment:
      POSTGRES_DB: mold_cost_db
      POSTGRES_USER: root
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - mold_cost_network

  redis:
    image: redis:7-alpine
    container_name: mold_cost_redis
    restart: always
    networks:
      - mold_cost_network

  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    container_name: mold_cost_rabbitmq
    restart: always
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    networks:
      - mold_cost_network

  minio:
    image: minio/minio:latest
    container_name: mold_cost_minio
    restart: always
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    networks:
      - mold_cost_network

volumes:
  postgres_data:
  minio_data:

networks:
  mold_cost_network:
    driver: bridge
```

启动服务：

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 监控和日志

#### 1. 日志管理

```bash
# 查看应用日志
sudo journalctl -u mold-cost-api -f

# 查看Nginx日志
sudo tail -f /var/log/nginx/mold-cost-access.log
sudo tail -f /var/log/nginx/mold-cost-error.log

# 查看应用日志文件
tail -f logs/app.log
```

#### 2. 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查数据库连接
psql -h localhost -U root -d mold_cost_db -c "SELECT 1"

# 检查Redis连接
redis-cli ping

# 检查RabbitMQ
rabbitmqctl status
```

### 备份和恢复

#### 数据库备份

```bash
# 备份数据库
pg_dump -h localhost -U root mold_cost_db > backup_$(date +%Y%m%d).sql

# 恢复数据库
psql -h localhost -U root mold_cost_db < backup_20260210.sql
```

#### MinIO备份

```bash
# 使用mc工具备份
mc mirror myminio/mold-cost /backup/minio/
```

---


## 📚 文档导航

### 快速入门

- **[快速开始指南](docs/QUICK_START.md)** - 5分钟快速上手
- **[API快速参考](docs/NC_3D_Workflow_API_Reference.md)** - API接口速查
- **[Postman测试集合](docs/API_POSTMAN_COLLECTION.json)** - 导入即用

### 前端对接

- **[前端对接总览](docs/README_FRONTEND.md)** ⭐ 前端开发者必读
- **[前端快速开始](docs/FRONTEND_QUICKSTART.md)** - React集成示例
- **[前端集成指南](docs/FRONTEND_INTEGRATION.md)** - 详细集成步骤
- **[Vue集成示例](docs/FRONTEND_VUE_EXAMPLE.md)** - Vue 3示例
- **[对接检查清单](docs/FRONTEND_CHECKLIST.md)** - 分步骤检查
- **[API调用流程](docs/API_CALL_FLOW.md)** - 系统架构和调用链路

### 团队协作

- **[团队协作完整指南](TEAM_GUIDE.md)** ⭐ 新人第一份文档
- **[团队协作指南](docs/team-collaboration.md)** - Git工作流、接口约定
- **[协作工作流程](docs/collaboration-workflow.md)** - 可视化协作流程
- **[协作总结](docs/COLLABORATION_SUMMARY.md)** - 协作原则和最佳实践

### 技术文档

- **[项目结构说明](docs/project-structure.md)** - 详细的目录结构
- **[项目搭建总结](PROJECT_SETUP_SUMMARY.md)** - 项目架构说明
- **[认证与权限管理](docs/auth-and-permission.md)** - 权限系统设计
- **[第二期功能说明](docs/phase2-features.md)** - 预留功能接口

### 迁移文档

- **[迁移完整性审计](MIGRATION_AUDIT_COMPLETE.md)** - 账户系统迁移审计
- **[账户合并计划](ACCOUNT_MERGE_PLAN.md)** - 合并方案
- **[合并执行计划](MERGE_EXECUTION_DETAILED_PLAN.md)** - 详细执行步骤
- **[合并进度](MERGE_PROGRESS.md)** - 当前进度

### API文档

- **[Swagger UI](http://localhost:8000/docs)** - 交互式API文档
- **[ReDoc](http://localhost:8000/redoc)** - 美观的API文档
- **[API参考手册](docs/NC_3D_Workflow_API_Reference.md)** - 完整API说明

---

## 🔧 常见问题

### 1. 数据库连接失败

**问题**: `could not connect to server: Connection refused`

**解决方案**:
```bash
# 检查PostgreSQL是否运行
sudo systemctl status postgresql

# 检查连接配置
psql -h localhost -U root -d mold_cost_db

# 检查.env文件配置
cat .env | grep DB_
```

### 2. Redis连接失败

**问题**: `Error connecting to Redis`

**解决方案**:
```bash
# 检查Redis是否运行
redis-cli ping

# 检查Redis配置
cat .env | grep REDIS_URL
```

### 3. RabbitMQ连接失败

**问题**: `Connection to RabbitMQ failed`

**解决方案**:
```bash
# 检查RabbitMQ状态
sudo systemctl status rabbitmq-server

# 检查用户权限
sudo rabbitmqctl list_users

# 重置密码
sudo rabbitmqctl change_password admin Admin@123
```

### 4. 文件上传失败

**问题**: `File upload failed: 413 Request Entity Too Large`

**解决方案**:
```bash
# 修改Nginx配置
sudo nano /etc/nginx/nginx.conf
# 添加: client_max_body_size 100M;

# 重启Nginx
sudo systemctl reload nginx
```

### 5. Token过期

**问题**: `Token expired`

**解决方案**:
```python
# 前端自动刷新token
if (response.status === 401) {
  // 重新登录或刷新token
  await refreshToken();
}
```

### 6. CORS错误

**问题**: `Access-Control-Allow-Origin error`

**解决方案**:
```python
# 检查main.py中的CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📞 联系方式

### 技术支持

- **项目负责人**: ZZH
- **邮箱**: support@example.com
- **文档**: http://localhost:8000/docs

### 问题反馈

- **GitHub Issues**: <repository-url>/issues
- **技术讨论**: 加入开发者群组

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

感谢所有为本项目做出贡献的开发者！

---

## 📝 更新日志

### v2.0.0 (2026-02-10)
- ✅ 完成账户系统迁移（从mold_cost_account）
- ✅ 集成认证模块（登录、Token验证、密码修改）
- ✅ 集成工艺规则管理（完整CRUD）
- ✅ 集成价格项管理（完整CRUD）
- ✅ 集成聊天会话管理（含级联删除）
- ✅ 异步架构升级（Flask → FastAPI）
- ✅ 数据库驱动升级（psycopg2 → asyncpg）
- ✅ 完整的API文档（Swagger + ReDoc）

### v1.0.0 (2026-01-XX)
- ✅ 初始版本发布
- ✅ 基础架构搭建
- ✅ AI Agent集成
- ✅ 文件上传功能
- ✅ 实时通信功能

---

**最后更新**: 2026-02-10  
**文档版本**: v2.0.0

