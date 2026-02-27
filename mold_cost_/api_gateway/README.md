# API Gateway 模块

## 📋 概述

API Gateway 是模具成本核算系统的统一入口，基于 FastAPI 构建的高性能异步 Web 服务。负责处理所有 HTTP 请求、WebSocket 连接、用户认证、权限控制和请求路由。

## 🎯 核心功能

- ✅ **RESTful API** - 完整的 REST 接口
- ✅ **WebSocket** - 实时双向通信
- ✅ **JWT 认证** - 安全的 Token 认证
- ✅ **权限控制** - 基于角色的访问控制
- ✅ **请求验证** - Pydantic 数据验证
- ✅ **异步处理** - 高性能异步架构
- ✅ **API 文档** - 自动生成 Swagger/ReDoc 文档
- ✅ **CORS 支持** - 跨域资源共享
- ✅ **日志记录** - 完整的请求日志

## 📁 目录结构

```
api_gateway/
├── routers/                    # 路由模块
│   ├── account/               # 账户系统路由
│   │   ├── auth.py           # 认证路由（登录、Token验证）
│   │   ├── process_rules.py  # 工艺规则管理
│   │   ├── price_items.py    # 价格项管理
│   │   └── chat_sessions.py  # 聊天会话管理
│   ├── jobs.py               # 任务管理路由
│   ├── file_router.py        # 文件管理路由
│   ├── interactions.py       # 交互路由
│   ├── review_router.py      # 审核路由
│   ├── chat_router.py        # 聊天路由
│   └── websocket_router.py   # WebSocket路由
├── services/                  # 服务层
│   ├── account/              # 账户系统服务
│   │   ├── auth_service.py   # 认证服务
│   │   ├── process_rule_service.py  # 工艺规则服务
│   │   ├── price_item_service.py    # 价格项服务
│   │   └── chat_session_service.py  # 聊天会话服务
│   ├── job_service.py        # 任务服务
│   ├── file_service.py       # 文件服务
│   └── interaction_service.py # 交互服务
├── models/                    # 数据模型
│   ├── account/              # 账户系统模型
│   │   ├── auth_models.py    # 认证模型
│   │   ├── process_rule_models.py   # 工艺规则模型
│   │   ├── price_item_models.py     # 价格项模型
│   │   └── chat_session_models.py   # 聊天会话模型
│   └── interaction_models.py # 交互模型
├── repositories/              # 数据访问层
│   ├── job_repository.py     # 任务仓储
│   ├── interaction_repository.py    # 交互仓储
│   ├── review_repository.py  # 审核仓储
│   ├── chat_history_repository.py   # 聊天历史仓储
│   ├── process_rules_repository.py  # 工艺规则仓储
│   └── audit_repository.py   # 审计日志仓储
├── utils/                     # 工具函数
│   ├── account/              # 账户系统工具
│   │   ├── password.py       # 密码加密
│   │   └── jwt_helper.py     # JWT工具
│   ├── rabbitmq_client.py    # RabbitMQ客户端
│   ├── redis_client.py       # Redis客户端
│   ├── minio_client.py       # MinIO客户端
│   ├── chat_logger.py        # 聊天日志
│   ├── encryption.py         # 加密工具
│   ├── message_formatter.py  # 消息格式化
│   ├── snapshot_manager.py   # 快照管理
│   └── validators.py         # 验证器
├── dependencies.py            # 依赖注入
├── config.py                  # 配置管理
├── database.py                # 数据库连接
├── auth.py                    # 认证中间件
├── main.py                    # 主入口
└── websocket.py               # WebSocket管理
```



`api_gateway` 就是传统意义上的后端，采用了经典的分层架构：

## API Gateway 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      api_gateway                            │
├─────────────────────────────────────────────────────────────┤
│  routers/              ← Controller 层                      │
│  ├── jobs.py           处理 HTTP 请求/响应                   │
│  ├── interactions.py   路由定义                              │
│  ├── review_router.py  参数验证                              │
│  └── ...                                                    │
├─────────────────────────────────────────────────────────────┤
│  services/             ← Service 层                         │
│  ├── job_service.py    业务逻辑处理                          │
│  ├── file_service.py   事务管理                              │
│  └── interaction_service.py 调用 Repository                 │
├─────────────────────────────────────────────────────────────┤
│  repositories/         ← Mapper/DAO 层                      │
│  ├── job_repository.py 数据库操作                            │
│  ├── audit_repository.py SQL 查询                           │
│  └── snapshot_repository.py 数据访问                        │
├─────────────────────────────────────────────────────────────┤
│  utils/                ← 基础设施                           │
│  ├── minio_client.py   MinIO 客户端                          │
│  ├── redis_client.py   Redis 客户端                          │
│  ├── rabbitmq_client.py RabbitMQ 客户端                     │
│  └── validators.py     工具函数                              │
├─────────────────────────────────────────────────────────────┤
│  models/               ← 数据模型                           │
│  └── interaction_models.py Pydantic 模型                     │
└─────────────────────────────────────────────────────────────┘
```

### 对比传统后端架构

| 层级           | api_gateway         | 传统后端   | 职责                         |
| -------------- | ------------------- | ---------- | ---------------------------- |
| **Controller** | `routers/*.py`      | Controller | 接收请求、参数校验、返回响应 |
| **Service**    | `services/*.py`     | Service    | 业务逻辑、事务编排           |
| **Repository** | `repositories/*.py` | Mapper/DAO | 数据库操作、SQL              |
| **Utils**      | `utils/*.py`        | -          | 外部服务客户端、工具         |

### 代码示例

**Controller (routers/jobs.py)**:

```python
@router.post("/upload")
async def upload_files(dwg_file: UploadFile = File(...)):
    # 参数校验、调用 Service
    result = await job_service.create_job_from_upload(...)
    return result
```

**Service (services/job_service.py)**:

```python
async def create_job_from_upload(self, db, user_id, dwg_file):
    # 业务逻辑
    dwg_info = await self._upload_files(dwg_file)
    job_id = await self.job_repo.create_job(db, job_id, user_id, dwg_info)
    await self._publish_job_message(job_id)
    return {"job_id": job_id}
```

**Repository (repositories/job_repository.py)**:

```python
async def create_job(self, db, job_id, user_id, dwg_info):
    # 数据库操作
    sql = text("INSERT INTO jobs ...")
    await db.execute(sql, {...})
```

所以 `api_gateway` 确实是传统后端，**Agents 才是真正的 AI 智能层**，负责复杂的业务决策和编排。



## 🚀 快速开始

### 启动服务

```bash
# 开发模式
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 访问文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## ==📡 API 路由==

### 1. 认证模块 (`/api`)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/login` | 用户登录 | ❌ |
| POST | `/api/verify-token` | Token验证 | ❌ |
| POST | `/api/change-password` | 修改密码 | ✅ |
| POST | `/api/logout` | 用户登出 | ✅ |

### 2. 任务管理 (`/api/v1/jobs`)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/jobs` | 创建任务 | ✅ |
| GET | `/api/v1/jobs` | 获取任务列表 | ✅ |
| GET | `/api/v1/jobs/{job_id}` | 获取任务详情 | ✅ |
| PUT | `/api/v1/jobs/{job_id}` | 更新任务 | ✅ |
| DELETE | `/api/v1/jobs/{job_id}` | 删除任务 | ✅ |

### 3. 文件管理 (`/api/v1/files`)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/files/upload` | 上传文件 | ✅ |
| GET | `/api/v1/files/presigned-url` | 获取预签名URL | ✅ |
| GET | `/api/v1/files/download/{file_id}` | 下载文件 | ✅ |
| DELETE | `/api/v1/files/{file_id}` | 删除文件 | ✅ |

### 4. 工艺规则 (`/api/process-rules`)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/process-rules` | 创建规则 | ✅ |
| GET | `/api/process-rules` | 获取规则列表 | ✅ |
| GET | `/api/process-rules/{rule_id}` | 获取规则详情 | ✅ |
| PUT | `/api/process-rules/{rule_id}` | 更新规则 | ✅ |
| DELETE | `/api/process-rules/{rule_id}` | 删除规则 | ✅ |
| POST | `/api/process-rules/batch-delete` | 批量删除 | ✅ |

### 5. 价格项 (`/api/price-items`)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/price-items` | 创建价格项 | ✅ |
| GET | `/api/price-items` | 获取价格项列表 | ✅ |
| GET | `/api/price-items/{item_id}` | 获取价格项详情 | ✅ |
| PUT | `/api/price-items/{item_id}` | 更新价格项 | ✅ |
| DELETE | `/api/price-items/{item_id}` | 删除价格项 | ✅ |

### 6. 聊天会话 (`/api/chat-sessions`)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/chat-sessions` | 获取会话列表 | ✅ |
| PUT | `/api/chat-sessions/{session_id}/name` | 更新会话名称 | ✅ |
| DELETE | `/api/chat-sessions/{session_id}` | 删除会话 | ✅ |

### 7. WebSocket (`/ws`)

| 路径 | 说明 | 认证 |
|------|------|------|
| `/ws/{job_id}` | 任务进度推送 | ✅ (Query参数) |

## 🔐 认证与授权

### JWT Token 认证

```python
# 登录获取 Token
POST /api/login
{
    "username": "admin",
    "password": "admin123"
}

# 响应
{
    "success": true,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user_info": {
        "user_id": "uuid",
        "username": "admin",
        "role": "admin"
    }
}

# 使用 Token
GET /api/v1/jobs
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 依赖注入

```python
from api_gateway.dependencies import get_current_user

@router.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"user": current_user}
```

## 🛠️ 服务层架构

### 三层架构

```
Router (路由层)
    ↓
Service (服务层)
    ↓
Repository (数据访问层)
    ↓
Database (数据库)
```

### 示例代码

```python
# Router
@router.post("/jobs")
async def create_job(
    job_data: JobCreate,
    current_user = Depends(get_current_user),
    job_service: JobService = Depends()
):
    return await job_service.create_job(job_data, current_user)

# Service
class JobService:
    async def create_job(self, job_data: JobCreate, user: dict):
        # 业务逻辑
        job = await self.job_repository.create(job_data)
        await self.rabbitmq_client.publish("job_created", job)
        return job

# Repository
class JobRepository:
    async def create(self, job_data: JobCreate):
        # 数据库操作
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                "INSERT INTO jobs (...) VALUES (...) RETURNING *",
                ...
            )
            return result
```

## 📊 数据模型

### Pydantic 模型

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class JobCreate(BaseModel):
    job_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    job_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

## 🔄 WebSocket 通信

### 连接管理

```python
from api_gateway.websocket import manager

# 客户端连接
ws = new WebSocket('ws://localhost:8000/ws/job-123?token=xxx');

# 服务端推送
await manager.send_message(
    job_id="job-123",
    message={
        "type": "progress_update",
        "progress": 50,
        "message": "处理中..."
    }
)
```

### 消息类型

- `job_status` - 任务状态更新
- `progress_update` - 进度更新
- `need_user_input` - 需要用户输入
- `ai_message` - AI响应消息
- `job_completed` - 任务完成
- `job_failed` - 任务失败

## 🗄️ 数据库操作

### 异步连接池

```python
from api_gateway.database import get_db_pool

async with get_db_pool() as pool:
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM jobs")
```

### 事务处理

```python
async with conn.transaction():
    await conn.execute("INSERT INTO jobs ...")
    await conn.execute("INSERT INTO job_files ...")
```

## 📝 配置管理

### 环境变量

```bash
# 服务配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mold_cost_db
DB_USER=root
DB_PASSWORD=password

# JWT配置
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120

# CORS配置
CORS_ORIGINS=["http://localhost:3000"]
```

### 配置类

```python
from api_gateway.config import settings

# 使用配置
db_url = settings.DATABASE_URL
jwt_secret = settings.JWT_SECRET_KEY
```

## 🧪 测试

### 单元测试

```bash
# 测试所有路由
pytest tests/api_gateway/

# 测试特定路由
pytest tests/api_gateway/test_auth.py

# 生成覆盖率报告
pytest --cov=api_gateway --cov-report=html
```

### 集成测试

```python
from fastapi.testclient import TestClient
from api_gateway.main import app

client = TestClient(app)

def test_login():
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    assert "token" in response.json()
```

## 📈 性能优化

### 异步处理

```python
# 并发处理多个请求
import asyncio

results = await asyncio.gather(
    fetch_user_data(user_id),
    fetch_job_data(job_id),
    fetch_file_data(file_id)
)
```

### 缓存策略

```python
from api_gateway.utils.redis_client import redis_client

# 缓存查询结果
cached = await redis_client.get(f"job:{job_id}")
if cached:
    return cached

data = await fetch_from_db(job_id)
await redis_client.set(f"job:{job_id}", data, expire=300)
```

### 连接池

```python
# 数据库连接池
pool = await asyncpg.create_pool(
    dsn=DATABASE_URL,
    min_size=10,
    max_size=20
)
```

## 🔍 日志和监控

### 日志配置

```python
from shared.logging_config import get_logger

logger = get_logger(__name__)

logger.info("API request received")
logger.error("Error processing request", exc_info=True)
```

### 请求日志

```python
from api_gateway.logging_middleware import LoggingMiddleware

app.add_middleware(LoggingMiddleware)
```

## 🚀 部署

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd 服务

```ini
[Unit]
Description=Mold Cost API Gateway
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/mold_cost
ExecStart=/opt/mold_cost/venv/bin/uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
```

## 📚 相关文档

- [Agents 文档](../agents/README.md)
- [Shared 模块文档](../shared/README.md)
- [主项目文档](../README.md)

## 🤝 贡献指南

1. 遵循 FastAPI 最佳实践
2. 使用 Pydantic 进行数据验证
3. 编写异步代码
4. 添加类型注解
5. 编写单元测试
6. 更新 API 文档

## 📞 联系方式

如有问题，请联系 API Gateway 团队或提交 Issue。
