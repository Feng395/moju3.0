# mold_cost-main 与 mold_cost_ 合并执行计划

## 📋 执行概览

**目标：** 将 `mold_cost-main` 合并到 `mold_cost_`，保留 `mold_cost_` 作为主项目  
**原因：** `mold_cost_` 功能更完整，是生产级版本  
**风险等级：** 🟢 低风险（结构相似，主要是配置和文档合并）

---

## 📊 差异分析总结

### 1. 依赖包差异

| 包名 | mold_cost-main | mold_cost_ | 建议 |
|------|----------------|------------|------|
| fastapi | 0.128.0 | 0.109.0 | ⬆️ 升级到 0.128.0 |
| uvicorn | 0.40.0 | 0.27.0 | ⬆️ 升级到 0.40.0 |
| sqlalchemy | 2.0.45 | 2.0.25 | ⬆️ 升级到 2.0.45 |
| asyncpg | 0.30.0 | 0.29.0 | ⬆️ 升级到 0.30.0 |
| redis | 7.1.0 | 5.3.1 | ⬆️ 升级到 7.1.0 |
| aio-pika | 9.5.7 | 9.3.1 | ⬆️ 升级到 9.5.7 |
| minio | 7.2.20 | 7.2.3 | ⬆️ 升级到 7.2.20 |
| httpx | 0.28.1 | 0.26.0 | ⬆️ 升级到 0.28.1 |
| pydantic | 2.12.5 | 2.5.3 | ⬆️ 升级到 2.12.5 |
| python-jose | ✅ 有 | ❌ 无 | ➕ 添加（JWT 支持） |
| PyJWT | ❌ 无 | ✅ 有 | ✅ 保留 |
| websocket-client | ✅ 有 | ❌ 无 | ➕ 添加 |
| websockets | ✅ 有 | ❌ 无 | ➕ 添加 |
| ezdxf | ✅ 有 | ❌ 无 | ➕ 添加（CAD 处理） |
| loguru | ✅ 有 | ❌ 无 | ➕ 添加（日志） |
| openpyxl | ✅ 有 | ❌ 无 | ➕ 添加（Excel） |
| xlsxwriter | ✅ 有 | ❌ 无 | ➕ 添加（Excel） |
| reportlab | ✅ 有 | ❌ 无 | ➕ 添加（PDF） |
| prometheus-client | ✅ 有 | ❌ 无 | ➕ 添加（监控） |
| mcp | ✅ 有 | ❌ 无 | ➕ 添加（MCP 协议） |

### 2. 配置差异

| 配置项 | mold_cost-main | mold_cost_ | 建议 |
|--------|----------------|------------|------|
| REDIS_URL | redis://192.168.0.41:6379/0 | redis://localhost:6379 | 🔄 使用 mold_cost-main 的值 |
| RABBITMQ_HOST | 192.168.0.41 | localhost | 🔄 使用 mold_cost-main 的值 |
| 并发配置 | ✅ 详细 | ❌ 无 | ➕ 添加并发配置 |
| 特征识别配置 | ✅ 详细 | ❌ 无 | ➕ 添加特征识别配置 |
| CAD 拆图配置 | ✅ 有 | ❌ 无 | ➕ 添加 CAD 配置 |
| MCP 服务配置 | ✅ 统一 | ✅ 分散 | 🔄 合并配置 |
| MINIO_EXTERNAL_ENDPOINT | ❌ 无 | ✅ 有 | ✅ 保留 |
| LOG 配置 | ✅ 简单 | ✅ 详细 | ✅ 保留 mold_cost_ 的详细配置 |

### 3. 独有模块

#### mold_cost-main 独有：
- ✅ `workers/` 目录（需要迁移）
- ✅ 文档：`启动清单.md`、`NC_3D_Workflow_API_Reference.md`、`QUICK_START.md`

#### mold_cost_ 独有：
- ✅ `consumers/` - 消息消费者
- ✅ `scripts/` - 完整的脚本工具集
- ✅ `mcp_services/` - MCP 服务
- ✅ `examples/` - 测试示例
- ✅ `tests/` - 测试文件
- ✅ `infrastructure/` - 基础设施配置

---

## 🎯 合并步骤

### 步骤 1：备份当前状态 ✅

```bash
# 创建备份分支
git checkout -b backup-before-merge
git push origin backup-before-merge

# 返回主分支
git checkout main
```

### 步骤 2：迁移 workers 目录

#### 2.1 检查 workers 功能
```bash
# 对比两个项目的 workers 实现
# mold_cost-main 有 workers，mold_cost_ 没有
```

#### 2.2 复制 workers 到 mold_cost_
```bash
# 复制整个 workers 目录
cp -r mold_cost-main/workers mold_cost_/

# 检查是否需要修改导入路径
```

#### 2.3 更新 workers 的导入路径
需要检查 workers 中的导入语句，确保与 mold_cost_ 的结构一致。

**可能需要修改的导入：**
```python
# 旧的导入（mold_cost-main）
from shared.database import get_db
from shared.message_queue import MessageQueue
from agents.orchestrator_agent import OrchestratorAgent

# 新的导入（mold_cost_）
from shared.database import get_db
from shared.message_queue import MessageQueue
from agents.orchestrator_agent import OrchestratorAgent
# 应该是一样的，但需要验证
```

### 步骤 3：合并 requirements.txt

创建新的 `requirements.txt`：

```txt
# ============================================
# Web 框架
# ============================================
fastapi==0.128.0
uvicorn[standard]==0.40.0
python-multipart==0.0.21
websocket-client==1.9.0
websockets==16.0

# ============================================
# 数据库
# ============================================
sqlalchemy[asyncio]==2.0.45
asyncpg==0.30.0
alembic==1.18.0
psycopg2-binary==2.9.11

# ============================================
# 消息队列
# ============================================
aio-pika==9.5.7

# ============================================
# 缓存
# ============================================
redis[hiredis]==7.1.0

# ============================================
# 对象存储
# ============================================
minio==7.2.20

# ============================================
# 认证和安全
# ============================================
PyJWT==2.8.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==42.0.0

# ============================================
# HTTP 客户端
# ============================================
httpx==0.28.1
aiohttp==3.13.3
requests>=2.31.0

# ============================================
# 配置管理
# ============================================
python-dotenv==1.2.1
pydantic==2.12.5
pydantic-settings==2.12.0

# ============================================
# 日志
# ============================================
python-json-logger==4.0.0
loguru>=0.7.0

# ============================================
# AI 框架
# ============================================
langchain>=1.0,<2.0
langgraph>=1.0,<2.0
langchain-openai>=0.1.0,<1.0
openai>=1.0,<2.0

# ============================================
# MCP 协议
# ============================================
mcp>=1.25,<2

# ============================================
# 工具库
# ============================================
tenacity==9.1.2
python-dateutil==2.8.2

# ============================================
# CAD 文件处理
# ============================================
ezdxf>=1.0.0

# ============================================
# Excel & PDF
# ============================================
openpyxl==3.1.5
xlsxwriter==3.2.0
reportlab==4.4.7

# ============================================
# 监控
# ============================================
prometheus-client==0.23.1

# ============================================
# 测试
# ============================================
pytest==9.0.2
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# ============================================
# 代码质量
# ============================================
black==25.12.0
flake8==6.1.0
mypy==1.19.1
```

### 步骤 4：合并 .env 配置

创建新的 `.env` 文件（合并两者的配置）：

```bash
# ============================================
# 数据库配置
# ============================================
DB_HOST=192.168.1.54
DB_PORT=5432
DB_NAME=mold_cost_db
DB_USER=root
DB_PASSWORD=yunzai123

# ============================================
# Redis 配置
# ============================================
REDIS_URL=redis://192.168.0.41:6379/0

# ============================================
# RabbitMQ 配置
# ============================================
RABBITMQ_HOST=192.168.0.41
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=Admin@123
RABBITMQ_QUEUE_JOB_PROCESSING=job_processing
RABBITMQ_QUEUE_DLX=job_processing_dlx

# ============================================
# 队列并发配置
# ============================================
# job_processing 队列并发数（任务编排）
JOB_PROCESSING_CONCURRENCY=3

# pricing_recalculate 队列并发数（价格重算）
PRICING_RECALCULATE_CONCURRENCY=4

# ============================================
# MinIO 配置
# ============================================
MINIO_ENDPOINT=192.168.0.41:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_USE_HTTPS=false
MINIO_BUCKET_FILES=files
MINIO_REGION=us-east-1

# MinIO 外部访问地址（用于生成预签名URL）
MINIO_EXTERNAL_ENDPOINT=192.168.0.41:9000

# MinIO 并行下载配置
MINIO_DOWNLOAD_WORKERS=5
MINIO_UPLOAD_PART_SIZE=10485760
MINIO_UPLOAD_WORKERS=8

# ============================================
# 子图导出并发数配置
# ============================================
EXPORT_WORKERS=5
PRICING_BATCH_SIZE=50

# ============================================
# 特征识别并发控制配置
# ============================================
FEATURE_RECOGNITION_MAX_CONCURRENT=25
MCP_CLIENT_POOL_SIZE=30
MCP_CLIENT_MAX_RETRIES=3
MCP_CLIENT_TIMEOUT=600

# 自适应并发控制（实验性功能）
FEATURE_RECOGNITION_ADAPTIVE_CONCURRENCY=false
FEATURE_RECOGNITION_MIN_CONCURRENT=10
FEATURE_RECOGNITION_MAX_CONCURRENT_LIMIT=50

# 性能监控配置
FEATURE_RECOGNITION_SLOW_THRESHOLD=30000
FEATURE_RECOGNITION_LOG_PERFORMANCE=true

# ============================================
# CAD 拆图服务配置
# ============================================
ODA_FILE_CONVERTER_PATH=C:\\anzhuang\\ODAFileConverter\\ODAFileConverter.exe
SERVER_HOST=localhost
SERVER_PORT=6009
SERVER_RELOAD=false
SERVER_WORKERS=1

# ============================================
# JWT 配置
# ============================================
JWT_SECRET_KEY=your-secret-key-change-in-production-2024
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120

# ============================================
# 文件上传配置
# ============================================
MAX_FILE_SIZE_MB=1000
ALLOWED_FILE_EXTENSIONS=.dwg,.prt

# ============================================
# 外部 NC Agent 配置
# ============================================
NC_AGENT_URL=http://192.168.0.111:8001
NC_AGENT_TIMEOUT=86400

# ============================================
# MCP 服务配置（统一服务）
# ============================================
CAD_PRICE_SEARCH_MCP_URL=http://localhost:8200
CAD_PRICE_SEARCH_MCP_HOST=0.0.0.0
CAD_PRICE_SEARCH_MCP_PORT=8200

CAD_PARSER_MCP_URL=http://localhost:8101
FEATURE_RECOGNITION_MCP_URL=http://localhost:8102
NC_CONNECTOR_MCP_URL=http://localhost:8103
PRICING_SERVER_MCP_URL=http://localhost:8105
REPORT_GENERATOR_MCP_URL=http://localhost:8107

# ============================================
# API Gateway 配置
# ============================================
API_GATEWAY_HOST=0.0.0.0
API_GATEWAY_PORT=8300

# ============================================
# 日志配置
# ============================================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=logs
ENABLE_JSON_LOG=false
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# ============================================
# 监控配置
# ============================================
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# ============================================
# 开发模式
# ============================================
DEBUG=true
RELOAD=true

# ============================================
# 消息重试配置
# ============================================
ENABLE_MESSAGE_RETRY=false

# ============================================
# LLM 配置（InteractionAgent V2）
# ============================================
OPENAI_API_KEY=sk-dummy
OPENAI_MODEL=Qwen3-30B-A3B-Instruct
OPENAI_BASE_URL=http://192.168.0.22:8000/v1

# Agent 配置
USE_LLM=true
USE_LLM_FOR_QUERY_DETAILS=true
USE_CHAT_HISTORY=true
MAX_HISTORY_MESSAGES=10

# 性能配置
LLM_TIMEOUT=300
API_TIMEOUT=60
LLM_TEMPERATURE=0
MAX_RETRIES=3

# 参数验证配置
SUPPORTED_MATERIALS=P20,718,NAK80,S136,H13,2738
MIN_THICKNESS=1
MAX_THICKNESS=500
MIN_WIRE_LENGTH=0
MAX_WIRE_LENGTH=10000
```

### 步骤 5：迁移文档

```bash
# 复制文档到 mold_cost_/docs/
cp mold_cost-main/启动清单.md mold_cost_/docs/
cp mold_cost-main/NC_3D_Workflow_API_Reference.md mold_cost_/docs/
cp mold_cost-main/QUICK_START.md mold_cost_/docs/
```

### 步骤 6：更新 .gitignore

确保 `.gitignore` 包含所有必要的忽略规则：

```gitignore
# 敏感配置文件
mold_cost_account_react/src/services/speechRecognitionService.ts
mold_cost_account_react/src/services/speechSynthesisService.ts
mold_cost_/.env.interaction_agent

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Environment
.env
.env.local
.env.*.local

# Database
*.db
*.sqlite

# Temporary files
*.tmp
*.temp
*.bak

# 备份目录
mold_cost-main/
```

### 步骤 7：删除 mold_cost-main 目录

```bash
# 确认所有内容已迁移后，删除 mold_cost-main
rm -rf mold_cost-main
```

### 步骤 8：测试验证

#### 8.1 安装依赖
```bash
cd mold_cost_
pip install -r requirements.txt
```

#### 8.2 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_interaction_agent.py
```

#### 8.3 启动服务
```bash
# 启动 API Gateway
python -m uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8300

# 启动 Workers（如果需要）
python workers/orchestrator_worker.py
python workers/all_tasks_worker.py
python workers/pricing_recalculate_worker.py
```

#### 8.4 验证功能
- ✅ API 接口正常
- ✅ WebSocket 连接正常
- ✅ 数据库连接正常
- ✅ Redis 连接正常
- ✅ RabbitMQ 连接正常
- ✅ MinIO 连接正常
- ✅ Workers 正常运行

### 步骤 9：提交到 Git

```bash
# 添加所有更改
git add -A

# 提交
git commit -m "合并 mold_cost-main 到 mold_cost_

- 迁移 workers 目录
- 合并 requirements.txt（升级依赖包）
- 合并 .env 配置（添加并发和性能配置）
- 迁移文档到 docs 目录
- 删除 mold_cost-main 目录
- 更新 .gitignore"

# 推送到远程
git push origin main
```

---

## ⚠️ 注意事项

### 1. 依赖包升级风险
- 升级 fastapi、sqlalchemy 等核心包可能导致 API 不兼容
- **建议：** 先在测试环境验证

### 2. Workers 模块迁移
- workers 模块可能依赖特定的配置
- **建议：** 仔细检查导入路径和配置

### 3. 配置文件合并
- 确保所有服务的地址和端口正确
- **建议：** 逐项检查配置

### 4. 数据库兼容性
- 两个项目的数据库模型可能有差异
- **建议：** 运行数据库迁移脚本

---

## 📝 检查清单

### 合并前检查
- [ ] 已创建备份分支
- [ ] 已阅读 MERGE_ANALYSIS.md
- [ ] 已了解两个项目的差异

### 合并中检查
- [ ] workers 目录已复制
- [ ] requirements.txt 已合并
- [ ] .env 配置已合并
- [ ] 文档已迁移
- [ ] .gitignore 已更新

### 合并后检查
- [ ] 依赖包已安装
- [ ] 测试已通过
- [ ] API 服务正常启动
- [ ] Workers 正常运行
- [ ] 所有配置项正确
- [ ] 已提交到 Git

---

## 🎉 完成标志

当以下所有条件满足时，合并完成：

1. ✅ mold_cost-main 目录已删除
2. ✅ mold_cost_ 包含所有功能
3. ✅ 所有测试通过
4. ✅ 服务正常运行
5. ✅ 代码已提交到 Git

---

**文档版本：** v1.0  
**创建时间：** 2026-02-10  
**预计执行时间：** 2-3 小时
