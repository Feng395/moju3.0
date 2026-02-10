# 快速启动指南

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置环境变量

```bash
# 复制配置文件
cp config/.env.example config/.env

# 编辑配置文件
# 修改数据库连接信息和JWT密钥
```

## 3. 检查配置

```bash
python scripts/check_config.py
```

## 4. 启动服务

```bash
# 方式1：使用run.py（推荐）
python run.py

# 方式2：直接运行main.py
python main.py
```

## 5. 测试接口

```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试登录
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'

# 测试工艺规则列表
curl http://localhost:8000/api/process-rules

# 测试价格项列表
curl http://localhost:8000/api/price-items
```

## 6. 查看文档

- 项目结构: `PROJECT_STRUCTURE.md`
- JWT指南: `docs/JWT_GUIDE.md`
- 工艺接口: `docs/工艺接口文档.md`
- 价格接口: `docs/价格接口文档-简洁版.md`

## 常见问题

### 1. 数据库连接失败
- 检查数据库服务是否运行
- 检查 `config/.env` 中的数据库配置
- 运行 `python scripts/check_config.py` 查看配置

### 2. 端口被占用
- 修改 `config/config.py` 中的 `PORT` 配置
- 或在 `config/.env` 中设置 `PORT=8001`

### 3. JWT过期时间
- 修改 `config/.env` 中的 `JWT_EXPIRE_MINUTES`
- 重启服务生效

## 目录结构

```
├── app/              # 应用代码
│   ├── api/         # API路由
│   ├── models/      # 数据模型
│   ├── services/    # 业务服务
│   └── utils/       # 工具函数
├── config/          # 配置文件
├── docs/            # 文档
├── tests/           # 测试
├── scripts/         # 脚本工具
├── main.py          # 主应用
└── run.py           # 启动入口
```

## 下一步

1. 阅读 `PROJECT_STRUCTURE.md` 了解项目结构
2. 查看 `docs/` 目录下的API文档
3. 运行 `tests/` 目录下的测试脚本
4. 开始开发你的功能！
