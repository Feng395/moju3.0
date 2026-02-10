# 模具成本核算系统

基于AI Agent的模具成本核算系统，实现从CAD文件上传到成本报表生成的全自动化流程。

## 📚 文档导航

### 🎯 新人必读
- **[团队协作完整指南](TEAM_GUIDE.md)** ⭐ 新人第一份文档，找到你的角色和职责
- **[快速参考卡片](docs/quick-reference.md)** - 常用命令和联系方式

### 📋 协作指南
- **[团队协作指南](docs/team-collaboration.md)** - 详细的Git工作流、接口约定、沟通机制
- **[协作工作流程](docs/collaboration-workflow.md)** - 可视化协作流程图
- **[协作总结](docs/COLLABORATION_SUMMARY.md)** - 协作原则和最佳实践

### 🏗️ 技术文档
- **[项目结构说明](docs/project-structure.md)** - 详细的目录结构和人员分工
- **[项目搭建总结](PROJECT_SETUP_SUMMARY.md)** - 项目架构搭建说明
- **[第二期功能说明](docs/phase2-features.md)** - 预留功能接口

### 🔌 前端对接
- **[前端对接总览](docs/README_FRONTEND.md)** ⭐ 前端开发者必读
- **[快速开始指南](docs/FRONTEND_QUICKSTART.md)** - 5分钟快速集成
- **[完整集成指南](docs/FRONTEND_INTEGRATION.md)** - React/TypeScript详细示例
- **[Vue集成示例](docs/FRONTEND_VUE_EXAMPLE.md)** - Vue 3 + Composition API
- **[对接检查清单](docs/FRONTEND_CHECKLIST.md)** - 分步骤对接指南
- **[API调用流程](docs/API_CALL_FLOW.md)** - 系统架构和调用链路
- **[Postman测试集合](docs/API_POSTMAN_COLLECTION.json)** - API测试工具

## 项目结构

```
mold-cost-system/
├── api-gateway/              # API网关服务（人员B2）
├── agents/                   # Agent层（人员B1, E, F）
├── mcp-services/            # MCP服务层（人员D）
├── frontend/                # 前端应用（人员C）
├── shared/                  # 共享代码和工具
├── infrastructure/          # 基础设施配置（人员A, B1, B2）
├── docs/                    # 文档
├── tests/                   # 测试
└── scripts/                 # 脚本工具
```

## 技术栈

- **后端**: Python 3.11+, FastAPI
- **AI框架**: LangChain, LangGraph
- **数据库**: PostgreSQL 14+
- **缓存**: Redis
- **消息队列**: RabbitMQ
- **对象存储**: MinIO
- **认证**: JWT Token + bcrypt
- **权限**: 简化版RBAC（3个角色）
- **前端**: React, TypeScript, Ant Design
- **容器化**: Docker, Docker Compose

## 权限角色

系统采用简化版RBAC，支持3个角色：

| 角色 | 说明 | 权限 |
|------|------|------|
| **Admin** | 管理员 | 所有权限，包括用户管理、价格配置 |
| **Operator** | 操作员 | 上传文件、查看自己的任务、重算 |
| **Viewer** | 查看者 | 查看所有任务和报表（只读） |

详见 [认证与权限管理方案](docs/auth-and-permission.md)

## 团队分工（7人）

- **人员A**: 架构师/技术负责人
- **人员B1**: Agent编排与流程工程师
- **人员B2**: API网关与交互工程师
- **人员C**: 前端开发工程师
- **人员D**: MCP服务开发工程师
- **人员E**: 价格计算与RAG工程师
- **人员F**: CAD处理与Agent工程师

## 快速开始

```bash
# 安装依赖
cd mold-cost-system
pip install -r requirements.txt

# 启动基础设施
docker-compose up -d

# 启动开发服务器
./scripts/dev-start.sh

# 默认管理员账号
# 用户名：admin
# 密码：admin123
```

## 开发指南

详见以下文档：
- [项目结构说明](docs/project-structure.md) - 详细的目录结构
- [团队协作指南](docs/team-collaboration.md) - 7人团队协同开发指南
- [协作工作流程](docs/collaboration-workflow.md) - 可视化协作流程
- [快速参考卡片](docs/quick-reference.md) - 常用命令和联系方式
- [第二期功能说明](docs/phase2-features.md) - 预留功能接口

## 部署指南

详见 [docs/deployment.md](docs/deployment.md)
