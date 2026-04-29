# mold3.0 — 模具成本核算系统

基于 AI Agent 的智能模具成本核算平台，实现从 CAD 图纸上传到成本报表生成的全自动化流程。系统采用 FastAPI 异步架构 + React 前端，集成 LLM 驱动的特征识别、工艺规则匹配、价格计算、实时通信与审核工作流。

## 项目结构

```
mold3.0/
├── mold_cost_/                  # 后端 (Python/FastAPI)
│   ├── src/                     # 【新】Clean Architecture 重构代码
│   │   ├── domain/              #   领域层: 业务实体、服务、端口
│   │   ├── application/         #   应用层: 用例、LangGraph 工作流
│   │   ├── infrastructure/      #   基础设施: 数据库、CAD、LLM、消息队列
│   │   └── interfaces/          #   接口层: REST API、WebSocket、MCP、Worker
│   ├── api_gateway/             # 【旧】API 网关 (逐步下沉到 src)
│   ├── agents/                  # AI Agent 业务逻辑
│   ├── shared/                  # 共享模块 (数据库、模型、工具)
│   ├── workers/                 # 后台任务 Worker
│   ├── scripts/                 # CAD 拆图、特征识别、价格计算脚本
│   ├── mcp_services/            # MCP 微服务
│   ├── speech_services/         # 语音识别服务
│   └── infrastructure/          # Docker、SQL 初始化脚本
├── mold_cost_account_react/     # 前端 (React/TypeScript/Ant Design)
└── logs/                        # 运行日志
```

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Python 3.11+, FastAPI, Uvicorn |
| **AI/Agent** | LangChain, LangGraph, OpenAI |
| **数据库** | PostgreSQL 14+ (asyncpg), SQLAlchemy 2.0 |
| **缓存** | Redis 7+ |
| **消息队列** | RabbitMQ (aio-pika) |
| **对象存储** | MinIO |
| **微服务协议** | MCP (Model Context Protocol) |
| **前端** | React 18, TypeScript 5, Vite 5, Ant Design 5 |
| **CAD 处理** | ezdxf, ODA Converter, NX Adapter |
| **报表** | openpyxl, xlsxwriter, reportlab |
| **语音** | FFmpeg, Web Speech API |
| **测试** | pytest, pytest-asyncio |

## 核心功能

**CAD 文件处理与特征识别**
- 支持 .dwg、.prt 格式上传 (最大 100MB)
- AI Agent 自动识别加工特征 (钻孔、线割、水磨、NC 等)
- 按面编码 (Z/B/C/C_B/Z_VIEW/B_VIEW) 组织 NC 时间数据

**智能成本计算**
- 材料成本、NC 加工成本、线割成本、水磨成本
- 热处理、齿孔、重量价格等专项计算
- 支持 20+ 种价格计算器，按工艺规则自动匹配

**实时交互与审核**
- WebSocket 实时进度推送，SSE 流式消息
- 聊天式 AI 交互: 意图识别、代词推断、上下文记忆
- 完整审核流程: 提交→审核→通过/驳回→修改追踪

**企业级基础设施**
- JWT + bcrypt 认证，登录失败锁定
- 工艺规则与价格项版本管理
- Excel/PDF 报表导出
- Prometheus 监控指标

## 快速开始

### 前置条件

- Python 3.11+, Node.js 18+, PostgreSQL 14+, Redis, RabbitMQ
- FFmpeg (语音识别需要)

### 后端启动

```bash
cd mold_cost_

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env   # 编辑数据库、Redis、RabbitMQ 等配置

# 一键启动所有服务 (API + Worker, 端口 8000)
python main.py

# 或仅启动 API
python main.py --api-only
```

访问 http://localhost:8000/docs 查看 Swagger API 文档。

### 前端启动

```bash
cd mold_cost_account_react

npm install
npm run dev      # 默认 http://localhost:3000
```

### Docker 启动基础设施

```bash
cd mold_cost_/infrastructure
docker-compose up -d   # 启动 PostgreSQL, Redis, RabbitMQ, MinIO
```

## 架构演进

项目正在进行 **Clean Architecture 重构** (见 `src/` 目录)，将原有扁平化模块逐步下沉为清晰的分层架构:

```
interfaces → application → domain ← infrastructure
```

- `domain/` — 纯业务逻辑，不依赖任何框架
- `application/` — 用例编排，LangGraph 状态机工作流
- `infrastructure/` — 数据库仓储、CAD 运行时、消息队列适配器
- `interfaces/` — REST API、WebSocket、MCP Server、CLI

重构通过 Port/Adapter 模式将旧代码 (agents/, scripts/) 以 `legacy_*_gateway` 和 `*_runtime` 适配器形态接入新架构，确保平滑过渡。

## 环境变量

主要配置项 (详见 `.env.example`):

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_HOST` / `DB_PORT` / `DB_NAME` | PostgreSQL 连接 | localhost:5432 |
| `REDIS_URL` | Redis 连接 | redis://localhost:6379 |
| `RABBITMQ_HOST` | RabbitMQ 连接 | localhost |
| `MINIO_ENDPOINT` | MinIO 对象存储 | localhost:9000 |
| `JWT_SECRET_KEY` | JWT 签名密钥 | (需自行设置) |
| `API_TIMEOUT` | 外部 API 超时 (秒) | 60 |
| `NC_AGENT_ENABLED` | 启用 NC Agent | true |
| `MAX_HISTORY_MESSAGES` | 聊天上下文消息数 | 5 |

## 文档索引

- [后端 README](mold_cost_/README.md) — 详细架构、完整 API、部署指南
- [前端 README](mold_cost_account_react/README.md) — 前端架构、组件说明
- [快速启动清单](CXH.md) — 从零搭建完整环境
- [文档总索引](README_INDEX.md) — 全部模块文档导航
- [WebSocket 通信](WEBSOCKET_INTRO.md) — 实时通信设计
- [版本合并报告](VERSION_MERGE_FINAL_REPORT.md) — moldCost/mold_cost-main 合并记录

## License

MIT
