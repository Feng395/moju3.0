# 快速参考卡片

## 🚀 快速启动

```bash
# 1. 克隆项目
git clone <repo-url>
cd mold-cost-system

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动基础设施
cd infrastructure && docker-compose up -d && cd ..

# 4. 启动开发服务器
./scripts/dev-start.sh
```

## 👥 人员分工速查

| 人员 | 主要模块 | 关键文件 |
|------|---------|---------|
| A | 架构/数据库 | `shared/`, `infrastructure/` |
| B1 | Agent编排 | `agents/orchestrator_agent.py`, `nc_time_agent.py` |
| B2 | API网关 | `api-gateway/`, `interaction_agent.py` |
| C | 前端 | `frontend/` |
| D | MCP服务 | `mcp-services/` |
| E | 价格计算 | `pricing_agent.py`, `decision_agent.py` |
| F | CAD处理 | `cad_agent.py`, `report_agent.py` |

## 📝 Git命令速查

```bash
# 创建功能分支
git checkout -b feature/B1-orchestrator

# 提交代码
git add .
git commit -m "feat(orchestrator): 实现状态机"

# 推送到远程
git push origin feature/B1-orchestrator

# 同步develop
git checkout develop && git pull
git checkout feature/B1-orchestrator
git rebase develop

# 删除分支
git branch -d feature/B1-orchestrator
```

## 🔧 常用命令

```bash
# 代码格式化
black .

# 代码检查
flake8 .

# 类型检查
mypy .

# 运行测试
pytest tests/

# 启动API网关
cd api-gateway && uvicorn main:app --reload

# 查看Docker日志
docker-compose logs -f postgres
```

## 📞 紧急联系

- **技术问题**: @人员A
- **API问题**: @人员B2
- **Agent问题**: @人员B1
- **前端问题**: @人员C
- **MCP问题**: @人员D
- **价格问题**: @人员E
- **CAD问题**: @人员F

## 🔗 重要链接

- API文档: http://localhost:8000/docs
- RabbitMQ管理: http://localhost:15672
- MinIO控制台: http://localhost:9001
- 前端: http://localhost:3000

## 📋 每日检查清单

- [ ] 参加站会（9:30）
- [ ] 拉取最新代码
- [ ] 提交今日代码
- [ ] 更新任务状态
- [ ] 回复PR评论

## 🆘 遇到问题？

1. 查看文档: `docs/`
2. 搜索Issue
3. 在频道提问
4. 找相关人员
