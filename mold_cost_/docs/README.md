# 文档中心

## 📋 概述

本目录包含模具成本核算系统的完整文档，包括 API 参考、开发指南、部署说明等。

## 📚 文档导航

### 🚀 快速开始

- **[快速开始指南](../QUICK_START.md)** - 5分钟快速上手
- **[启动清单](启动清单.md)** - 系统启动检查清单

### 📡 API 文档

- **[API 参考手册](NC_3D_Workflow_API_Reference.md)** - 完整的 API 接口说明
- **[Postman 集合](API_POSTMAN_COLLECTION.json)** - 可导入的 API 测试集合
- **[预签名 URL 测试](PRESIGNED_URL_POSTMAN.json)** - 文件上传测试集合

### 🔀 账户系统合并

- **[账户合并文档](merge/account/)** - 账户系统合并相关文档

## 📖 主要文档

### NC_3D_Workflow_API_Reference.md

完整的 API 接口参考文档，包括：

- 认证接口
- 任务管理接口
- 文件管理接口
- 工艺规则接口
- 价格项接口
- 聊天会话接口
- WebSocket 接口

**使用方式**:
```bash
# 在线查看
http://localhost:8000/docs  # Swagger UI
http://localhost:8000/redoc # ReDoc

# 离线查看
markdown-viewer NC_3D_Workflow_API_Reference.md
```

### API_POSTMAN_COLLECTION.json

Postman API 测试集合，包含所有接口的示例请求。

**导入方式**:
1. 打开 Postman
2. 点击 Import
3. 选择 `API_POSTMAN_COLLECTION.json`
4. 配置环境变量
5. 开始测试

**环境变量**:
```json
{
  "base_url": "http://localhost:8000",
  "token": "your-jwt-token"
}
```

### PRESIGNED_URL_POSTMAN.json

MinIO 预签名 URL 测试集合。

**功能**:
- 获取上传 URL
- 上传文件
- 获取下载 URL
- 下载文件

### 启动清单.md

系统启动前的检查清单，确保所有依赖服务正常运行。

**检查项**:
- [ ] PostgreSQL 已启动
- [ ] Redis 已启动
- [ ] RabbitMQ 已启动
- [ ] MinIO 已启动
- [ ] 环境变量已配置
- [ ] 数据库已初始化

## 🔧 开发文档

### 架构设计

系统采用微服务架构，主要组件：

```
┌─────────────┐
│   前端应用   │
└──────┬──────┘
       │
┌──────▼──────────────────┐
│    API Gateway          │
│  (FastAPI)              │
└──────┬──────────────────┘
       │
┌──────▼──────┬──────────┬──────────┐
│  Agents     │ Workers  │ Scripts  │
└─────────────┴──────────┴──────────┘
       │
┌──────▼──────────────────────────────┐
│  Infrastructure                      │
│  (PostgreSQL, Redis, RabbitMQ, MinIO)│
└──────────────────────────────────────┘
```

### 数据流

```
1. 用户上传 CAD 文件
   ↓
2. API Gateway 接收请求
   ↓
3. 发送任务到 RabbitMQ
   ↓
4. Worker 消费任务
   ↓
5. Agent 处理业务逻辑
   ↓
6. Script 执行计算
   ↓
7. 结果存储到数据库
   ↓
8. WebSocket 推送进度
   ↓
9. 返回结果给用户
```

## 📝 API 使用示例

### 1. 用户登录

```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**响应**:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_info": {
    "user_id": "uuid",
    "username": "admin",
    "role": "admin"
  }
}
```

### 2. 创建任务

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "模具001",
    "description": "测试任务"
  }'
```

### 3. 上传文件

```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/file.dwg" \
  -F "job_id=<job_id>"
```

### 4. WebSocket 连接

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/job-123?token=<token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('进度更新:', data);
};
```

## 🧪 测试文档

### 单元测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/api_gateway/
pytest tests/agents/
pytest tests/scripts/

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

### 集成测试

```bash
# 端到端测试
pytest tests/integration/

# API 测试
pytest tests/api/
```

### 性能测试

```bash
# 使用 locust 进行压力测试
locust -f tests/performance/locustfile.py
```

## 📊 监控文档

### 日志查看

```bash
# 应用日志
tail -f logs/app.log

# API Gateway 日志
tail -f logs/api_gateway.log

# Worker 日志
tail -f logs/worker.log
```

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# 数据库连接检查
psql -h localhost -U root -d mold_cost_db -c "SELECT 1"

# Redis 检查
redis-cli ping

# RabbitMQ 检查
rabbitmqctl status
```

## 🚀 部署文档

### Docker 部署

```bash
# 构建镜像
docker build -t mold-cost-api:latest .

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 生产部署

参考 [主 README](../README.md) 的部署说明章节。

## 🔐 安全文档

### 认证流程

1. 用户登录获取 JWT Token
2. 在请求头中携带 Token
3. API Gateway 验证 Token
4. 检查用户权限
5. 执行业务逻辑

### 权限控制

- **admin** - 所有权限
- **user** - 基本操作权限
- **viewer** - 只读权限

## 📞 获取帮助

### 在线文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 问题反馈

- GitHub Issues: <repository-url>/issues
- 邮箱: support@example.com

### 技术支持

- 开发者群组
- 技术论坛

## 🤝 贡献文档

### 文档规范

1. 使用 Markdown 格式
2. 添加目录和导航
3. 包含代码示例
4. 保持更新

### 提交流程

1. Fork 项目
2. 创建文档分支
3. 编写/更新文档
4. 提交 Pull Request

## 📝 更新日志

### 2026-02-22
- ✅ 创建文档中心
- ✅ 整理 API 文档
- ✅ 添加使用示例

### 2026-02-10
- ✅ 完成账户系统合并文档
- ✅ 更新 API 参考手册

## 📚 相关资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [RabbitMQ 文档](https://www.rabbitmq.com/documentation.html)
- [MinIO 文档](https://min.io/docs/)

---

**最后更新**: 2026-02-22  
**维护者**: 文档团队
