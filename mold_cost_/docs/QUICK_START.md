# 🚀 快速启动指南

> **合并信息**  
> 合并日期: 2026-02-10  
> 源文件: mold_cost-main/QUICK_START.md  
> 说明: 系统快速启动指南

## 端口配置（已更新）

| 服务 | 端口 | 说明 |
|------|------|------|
| **API Gateway** | **8300** | HTTP API 接口（已从 8000 改为 8300） |
| **MCP 服务** | **8200** | 统一的 CAD + 价格服务 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存和进度 |
| RabbitMQ | 5672 | 消息队列 |
| MinIO | 9000 | 对象存储 |

## 一键启动

### Windows

```bash
# 方式1: 使用批处理脚本
scripts\start_all_services.bat

# 方式2: 手动启动
# 终端1: MCP 服务
python mcp_services/cad_price_search_mcp/server.py

# 终端2: Worker
python workers/orchestrator_worker.py

# 终端3: API Gateway
python -m uvicorn api_gateway.main:app --host 0.0.0.0 --port 8300
```

### Linux/Mac

```bash
# 方式1: 使用 Shell 脚本
chmod +x scripts/start_all_services.sh
./scripts/start_all_services.sh

# 停止服务
chmod +x scripts/stop_all_services.sh
./scripts/stop_all_services.sh

# 方式2: 手动启动
# 终端1: MCP 服务
python mcp_services/cad_price_search_mcp/server.py

# 终端2: Worker
python workers/orchestrator_worker.py

# 终端3: API Gateway
python -m uvicorn api_gateway.main:app --host 0.0.0.0 --port 8300
```

## 验证服务

```bash
# 检查 API Gateway (端口 8300)
curl http://localhost:8300/health

# 检查 MCP 服务 (端口 8200)
curl http://localhost:8200/health

# 查看 API 文档
# 浏览器打开: http://localhost:8300/docs
```

## 环境变量

确保 `.env` 文件包含：

```bash
# MCP服务配置（统一服务）
CAD_PRICE_SEARCH_MCP_URL=http://localhost:8200
CAD_PRICE_SEARCH_MCP_HOST=0.0.0.0
CAD_PRICE_SEARCH_MCP_PORT=8200

# API Gateway配置
API_GATEWAY_HOST=0.0.0.0
API_GATEWAY_PORT=8300
```

## 常用命令

### 创建任务

```bash
curl -X POST http://localhost:8300/api/v1/jobs \
  -F "dwg_file=@test.dwg"
```

### 查询任务

```bash
curl http://localhost:8300/api/v1/jobs/{job_id}
```

### 查看进度

```bash
# 连接 Redis
redis-cli -h 192.168.0.41 -p 6379

# 查看进度
GET progress:{job_id}
```

## 故障排查

### 端口被占用

```bash
# Windows - 查看端口占用
netstat -ano | findstr :8300
netstat -ano | findstr :8200

# Linux/Mac - 查看端口占用
lsof -i :8300
lsof -i :8200

# 杀死进程
# Windows: taskkill /PID <PID> /F
# Linux/Mac: kill <PID>
```

### 服务无法连接

1. 确认服务启动顺序：MCP 服务 → Worker → API Gateway
2. 检查 `.env` 配置
3. 查看日志输出

## 架构图

```
用户/前端
    ↓
API Gateway (:8300)  ← 端口已改为 8300
    ↓
RabbitMQ (:5672)
    ↓
Orchestrator Worker
    ↓
MCP Client
    ↓
cad-price-search-mcp (:8200)
    ├── CAD 工具 (3个)
    ├── 搜索工具 (7个)
    └── 计算工具 (8个)
    ↓
Database + MinIO
```

## 重要提示

- ✅ **API Gateway 端口已从 8000 改为 8300**
- ✅ 避免与其他服务冲突
- ✅ 所有文档和脚本已更新
- ✅ 前端需要更新 API 地址为 `http://localhost:8300`

## 相关文档

- [完整启动指南](START_GUIDE_UPDATED.md)
- [清理和迁移完成](CLEANUP_AND_MIGRATION_COMPLETE.md)
- [CAD Agent MCP 迁移](docs/cad-agent-mcp-migration.md)
