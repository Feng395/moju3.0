# 项目目录结构说明

## 整体架构

```
mold-cost-system/
├── api-gateway/              # API网关服务（人员B2）
│   ├── main.py              # FastAPI主入口
│   ├── auth.py              # 认证鉴权（JWT Token）
│   ├── websocket.py         # WebSocket实时通信
│   ├── dependencies.py      # 依赖注入（权限检查）
│   └── routers/             # API路由
│       ├── auth.py          # 认证相关API（登录、登出、刷新Token）
│       ├── users.py         # 用户管理API（仅管理员）
│       ├── jobs.py          # 任务相关API
│       ├── recalculations.py # 重算相关API
│       └── phase2.py        # 第二期功能API（预留）
│
├── agents/                   # Agent层
│   ├── base_agent.py        # BaseAgent基类（人员A）
│   ├── orchestrator_agent.py # 编排Agent（人员B1）
│   ├── nc_time_agent.py     # NC时间Agent（人员B1）
│   ├── interaction_agent.py # 交互Agent（人员B2）
│   ├── cad_agent.py         # CAD Agent（人员F）
│   ├── pricing_agent.py     # 价格Agent（人员E）
│   ├── decision_agent.py    # 决策Agent（人员E）
│   └── phase2/              # 第二期Agent（预留）
│       └── sheet_line_agent.py # 板料线Agent
│
├── mcp-services/            # MCP服务层（人员D）
│   ├── cad-parser-mcp/      # CAD解析服务（端口8101）
│   │   └── server.py
│   ├── feature-recognition-mcp/ # 特征识别服务（端口8102）
│   ├── nc-connector-mcp/    # NC连接器服务（端口8103）
│   ├── pricing-server-mcp/  # 价格服务（端口8105）
│   │   └── server.py
│   └── report-generator-mcp/ # 报表生成服务（端口8107）
│
├── frontend/                # 前端应用（人员C）
│   ├── src/
│   │   ├── components/      # React组件
│   │   ├── pages/           # 页面
│   │   ├── services/        # API服务
│   │   └── utils/           # 工具函数
│   └── package.json
│
├── shared/                  # 共享代码
│   ├── database.py          # 数据库连接（人员A）
│   ├── models.py            # 数据库模型（人员A）
│   ├── schemas.py           # Pydantic模型（人员A）
│   ├── security.py          # 安全工具（密码加密、Token生成）
│   ├── permissions.py       # 权限检查工具
│   ├── message_queue.py     # 消息队列（人员B1）
│   └── utils.py             # 工具函数
│
├── infrastructure/          # 基础设施配置
│   ├── docker-compose.yml   # Docker编排（人员B1）
│   ├── init-db.sql          # 数据库初始化（人员A）
│   ├── prometheus.yml       # 监控配置（人员B2）
│   └── nginx.conf           # Nginx配置
│
├── docs/                    # 文档
│   ├── project-structure.md # 项目结构说明
│   ├── development.md       # 开发指南
│   ├── deployment.md        # 部署指南
│   └── api-reference.md     # API文档
│
├── tests/                   # 测试
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── e2e/                 # 端到端测试
│
├── scripts/                 # 脚本工具
│   ├── dev-start.sh         # 开发启动脚本
│   ├── deploy.sh            # 部署脚本
│   └── migrate-db.sh        # 数据库迁移脚本
│
├── .env.example             # 环境变量示例
├── requirements.txt         # Python依赖
├── README.md                # 项目说明
└── .gitignore               # Git忽略文件
```

## 人员分工对应

### 人员A - 架构师/技术负责人
- `shared/database.py` - 数据库连接
- `shared/models.py` - 数据库模型
- `agents/base_agent.py` - BaseAgent基类
- `infrastructure/init-db.sql` - 数据库初始化

### 人员B1 - Agent编排与流程工程师
- `agents/orchestrator_agent.py` - 编排Agent
- `agents/nc_time_agent.py` - NC时间Agent
- `shared/message_queue.py` - 消息队列
- `infrastructure/docker-compose.yml` - Docker编排

### 人员B2 - API网关与交互工程师
- `api-gateway/main.py` - API主入口
- `api-gateway/auth.py` - 认证鉴权
- `api-gateway/websocket.py` - WebSocket
- `api-gateway/routers/` - 所有API路由
- `agents/interaction_agent.py` - 交互Agent

### 人员C - 前端开发工程师
- `frontend/` - 整个前端目录

### 人员D - MCP服务开发工程师
- `mcp-services/` - 所有MCP服务

### 人员E - 价格计算与RAG工程师
- `agents/pricing_agent.py` - 价格Agent
- `agents/decision_agent.py` - 决策Agent
- `mcp-services/pricing-server-mcp/` - 价格服务

### 人员F - CAD处理与Agent工程师
- `agents/cad_agent.py` - CAD Agent
- 其他CAD相关Agent

## 第二期功能预留

### API接口预留
- `api-gateway/routers/phase2.py` - 第二期功能API
  - 线割改精铣接口
  - 单个子图3D传入NC接口
  - 板料线生成接口
  - 多工艺并行处理接口

### Agent预留
- `agents/phase2/` - 第二期Agent目录
  - `sheet_line_agent.py` - 板料线生成Agent
  - `wire_to_milling_agent.py` - 线割改精铣Agent（待创建）
  - `multi_process_agent.py` - 多工艺Agent（待创建）

### MCP服务预留
- `mcp-services/cad-parser-mcp/server.py` 中的 `extrude_2d` 工具
- 其他第二期MCP工具

## 开发流程

1. **第1周**：搭建基础设施，创建数据库表
2. **第2-4周**：开发核心功能（文件上传、CAD解析、特征识别、价格计算、报表生成）
3. **第5周**：开发重算功能，系统测试
4. **第6周**：集成测试、部署、文档

## 技术栈

- **后端**: Python 3.11+, FastAPI, LangChain, LangGraph
- **数据库**: PostgreSQL 14+, Redis
- **消息队列**: RabbitMQ
- **对象存储**: MinIO
- **前端**: React, TypeScript, Ant Design
- **容器化**: Docker, Docker Compose
- **监控**: Prometheus, Grafana
- **日志**: ELK Stack
