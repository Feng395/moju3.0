# 快速开始 - 模具成本核算系统

## ⚡ 一键启动

### Windows
```bash
start.bat
```

### Linux/macOS
```bash
./start.sh
```

## 📍 访问地址

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **ReDoc**: http://localhost:8000/redoc

## 🎯 启动模式

```bash
# 完整模式（API + Worker）
python main.py

# 仅 API（适合前端开发）
python main.py --api-only

# 仅 Worker（后台任务）
python main.py --worker-only

# 指定端口
python main.py --port 8211
```

## ✅ 前置检查

- [ ] PostgreSQL 已启动 (端口 5432)
- [ ] Redis 已启动 (端口 6379)
- [ ] RabbitMQ 已启动 (端口 5672)
- [ ] MinIO 已启动 (端口 9000)
- [ ] `.env` 文件已配置

## 🔧 环境配置

最小配置 `.env`:

```bash
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mold_cost
DB_USER=postgres
DB_PASSWORD=root

# Redis
REDIS_URL=redis://localhost:6379

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET=mold-cost
MINIO_BUCKET_FILES=mold-cost

# ODA Converter
ODA_FILE_CONVERTER_PATH=D:\\workspace\\ODA\\ODAFileConverter.exe
```

## 🚨 常见问题

### 端口被占用
```bash
# 更换端口
python main.py --port 8001
```

### 服务连接失败
```bash
# 检查基础设施服务
curl http://localhost:8000/health
```

### 环境变量未加载
```bash
# 验证 .env 文件
cat .env
```

## 📚 详细文档

- [统一启动文档](docs/UNIFIED_STARTUP.md)
- [启动流程说明](docs/STARTUP_GUIDE.md)
- [完整 README](README.md)

## 🎉 就这么简单！

一个命令，启动整个系统！
