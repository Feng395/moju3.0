# Infrastructure 模块

## 📋 概述

Infrastructure 模块包含系统的基础设施配置文件，包括 Docker 容器编排、数据库初始化脚本和部署配置。

## 📁 目录结构

```
infrastructure/
├── docker-compose.yml    # Docker Compose 编排文件
├── Dockerfile           # 应用 Docker 镜像
├── init.sql            # 数据库初始化脚本
└── add.sql             # 数据库补充脚本
```

## 🐳 Docker Compose

### 服务列表

```yaml
services:
  - postgres      # PostgreSQL 数据库
  - redis         # Redis 缓存
  - rabbitmq      # RabbitMQ 消息队列
  - minio         # MinIO 对象存储
```

### 快速启动

```bash
# 启动所有服务
cd mold_cost_/infrastructure
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数据
docker-compose down -v
```

### 启动失败排查

如果启动时出现下面这类错误：

```text
failed to resolve reference "docker.io/library/rabbitmq:3.12-management-alpine"
net/http: TLS handshake timeout
```

这通常不是 `docker-compose.yml` 写错了，而是 Docker Desktop 到 Docker Hub 的网络链路异常，常见原因是代理、镜像源或 DNS 配置不通。

```bash
# 1. 先单独测试镜像拉取
docker pull rabbitmq:3.12-management-alpine
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull minio/minio:latest
docker pull minio/mc:latest

# 2. 如果仍然超时，检查 Docker 当前代理配置
docker info
```

重点看 `HTTP Proxy`、`HTTPS Proxy` 和 `No Proxy`。如果 `docker info` 显示了代理，但当前网络并不需要代理，或者代理地址已经失效，请在 Docker Desktop 的 `Settings -> Resources -> Proxies` 中关闭或修正代理后重试。

如果你所在网络访问 Docker Hub 较慢，可以在 Docker Desktop 中配置可用的 registry mirror，然后执行：

```bash
docker-compose down
docker-compose pull
docker-compose up -d
```

如果只是偶发超时，重试一次 `docker-compose pull` 往往就能恢复。

另外，`add.sql` 属于增量脚本，不应该在全新数据库首启时自动执行。当前 compose 已改为只在首启时加载 `sql/00_init.sql`。

### 服务配置

#### PostgreSQL
```yaml
postgres:
  image: postgres:15-alpine
  ports:
    - "5432:5432"
  environment:
    POSTGRES_DB: mold_cost_db
    POSTGRES_USER: root
    POSTGRES_PASSWORD: yunzai123
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./init.sql:/docker-entrypoint-initdb.d/init.sql
```

**访问方式**:
```bash
psql -h localhost -U root -d mold_cost_db
```

#### Redis
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

**访问方式**:
```bash
redis-cli -h localhost -p 6379
```

#### RabbitMQ
```yaml
rabbitmq:
  image: rabbitmq:3.12-management-alpine
  ports:
    - "5672:5672"    # AMQP 端口
    - "15672:15672"  # 管理界面
  environment:
    RABBITMQ_DEFAULT_USER: admin
    RABBITMQ_DEFAULT_PASS: Admin@123
```

**访问方式**:
- 管理界面: http://localhost:15672
- 用户名: admin
- 密码: Admin@123

#### MinIO
```yaml
minio:
  image: minio/minio:latest
  ports:
    - "9000:9000"    # API 端口
    - "9001:9001"    # 控制台
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  command: server /data --console-address ":9001"
```

**访问方式**:
- 控制台: http://localhost:9001
- 用户名: minioadmin
- 密码: minioadmin

## 🗄️ 数据库初始化

### init.sql

数据库初始化脚本，创建所有必要的表和索引。

**主要表结构**:

#### 用户表 (users)
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 任务表 (jobs)
```sql
CREATE TABLE jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES users(user_id),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 工艺规则表 (process_rules)
```sql
CREATE TABLE process_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(100) NOT NULL,
    feature_type VARCHAR(50),
    conditions JSONB,
    version_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 价格项表 (price_items)
```sql
CREATE TABLE price_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    unit_price DECIMAL(10, 2),
    version_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 执行初始化

```bash
# 方式1: Docker Compose 自动执行
docker-compose up -d

# 方式2: 手动执行
psql -h localhost -U root -d mold_cost_db -f init.sql

# 方式3: 在容器内执行
docker exec -i mold_cost_postgres psql -U root -d mold_cost_db < init.sql
```

### add.sql

补充脚本，添加额外的表、索引或数据。

```bash
# 执行补充脚本
psql -h localhost -U root -d mold_cost_db -f add.sql
```

## 🏗️ Dockerfile

### 应用镜像构建

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 构建镜像

```bash
# 构建镜像
docker build -t mold-cost-api:latest .

# 运行容器
docker run -d \
  --name mold-cost-api \
  -p 8000:8000 \
  --env-file .env \
  mold-cost-api:latest
```

## 🚀 部署方案

### 开发环境

```bash
# 启动基础设施
cd infrastructure
docker-compose up -d

# 启动应用（本地）
cd ..
python main.py
```

### 生产环境

#### 方案1: Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: mold-cost-api:latest
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=postgres
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
      - rabbitmq
      - minio
    restart: always

  worker:
    image: mold-cost-api:latest
    command: python workers/orchestrator_worker.py
    environment:
      - DB_HOST=postgres
      - RABBITMQ_HOST=rabbitmq
    depends_on:
      - postgres
      - rabbitmq
    restart: always
```

```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### 方案2: Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mold-cost-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mold-cost-api
  template:
    metadata:
      labels:
        app: mold-cost-api
    spec:
      containers:
      - name: api
        image: mold-cost-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          value: postgres-service
```

```bash
kubectl apply -f deployment.yaml
```

## 🔧 维护操作

### 数据库备份

```bash
# 备份数据库
docker exec mold_cost_postgres pg_dump -U root mold_cost_db > backup.sql

# 恢复数据库
docker exec -i mold_cost_postgres psql -U root mold_cost_db < backup.sql
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f rabbitmq
```

### 数据清理

```bash
# 清理未使用的容器
docker-compose down

# 清理数据卷
docker-compose down -v

# 清理镜像
docker image prune -a
```

### 服务重启

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart postgres
docker-compose restart redis
```

## 📊 监控

### 健康检查

```bash
# PostgreSQL
docker exec mold_cost_postgres pg_isready -U root

# Redis
docker exec mold_cost_redis redis-cli ping

# RabbitMQ
curl http://localhost:15672/api/healthchecks/node

# MinIO
curl http://localhost:9000/minio/health/live
```

### 资源使用

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
docker system df
```

## 🔐 安全配置

### 生产环境建议

1. **修改默认密码**
```yaml
environment:
  POSTGRES_PASSWORD: ${DB_PASSWORD}
  RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
  MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
```

2. **使用 Docker Secrets**
```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

3. **限制网络访问**
```yaml
networks:
  backend:
    internal: true
  frontend:
    internal: false
```

4. **启用 SSL/TLS**
```yaml
postgres:
  environment:
    POSTGRES_SSL_MODE: require
```

## 📚 相关文档

- [Docker Compose 文档](https://docs.docker.com/compose/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [Redis 文档](https://redis.io/documentation)
- [RabbitMQ 文档](https://www.rabbitmq.com/documentation.html)
- [MinIO 文档](https://min.io/docs/minio/linux/index.html)

## 🤝 贡献指南

1. 测试配置变更
2. 更新文档
3. 提交 Pull Request

## 📞 联系方式

如有问题，请联系基础设施团队或提交 Issue。
