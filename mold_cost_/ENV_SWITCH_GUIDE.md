# 环境配置切换指南

## 可用环境配置

项目提供了多个预配置的环境文件，方便快速切换：

### 1. 本地环境 (`.env` 或 `.env.local`)
**适用场景**: 本地开发和测试

**配置**:
- 数据库: `localhost:5432/mold_cost`
- Redis: `localhost:6379`
- RabbitMQ: `localhost:5672`
- MinIO: `localhost:9000`

**启动前提**: 需要先启动本地Docker服务
```bash
cd infrastructure
docker-compose up -d
```

### 2. 远程数据库环境 (`.env.remote_db`) ⭐ 新增
**适用场景**: 使用远程数据库，其他服务使用本地Docker

**配置**:
- 数据库: `192.168.1.54:5432/mold_cost_db` (远程)
- Redis: `localhost:6379` (本地)
- RabbitMQ: `localhost:5672` (本地)
- MinIO: `localhost:9000` (本地)

**优势**:
- 使用生产数据库进行测试
- 本地服务便于调试
- 无需维护本地数据库

**启动前提**: 需要启动本地Docker服务（除数据库外）
```bash
cd infrastructure
# 只启动 Redis, RabbitMQ, MinIO
docker-compose up -d redis rabbitmq minio
```

### 3. 远程环境 (`.env.remote`)
**适用场景**: 集成测试，所有服务使用远程

**配置**:
- 数据库: `192.168.1.54:5432/mold_cost_db`
- Redis: `192.168.0.41:6379`
- RabbitMQ: `192.168.0.41:5672`
- MinIO: `192.168.0.41:9000`

### 4. 生产环境 (`.env.main`)
**适用场景**: 生产部署

## 快速切换方法

### 方法1: 使用切换脚本（推荐）

#### Windows
```bash
switch_env.bat
```

#### Linux/Mac
```bash
chmod +x switch_env.sh
./switch_env.sh
```

脚本会显示菜单：
```
========================================
环境配置切换
========================================

请选择要切换的环境:
1. 本地环境 (本地数据库 + 本地服务)
2. 远程数据库 (远程数据库 + 本地服务)
3. 远程环境 (远程数据库 + 远程服务)
4. 生产环境
0. 退出

请输入选项 (0-4):
```

### 方法2: 手动复制

#### 切换到远程数据库环境
```bash
# Windows
copy .env.remote_db .env

# Linux/Mac
cp .env.remote_db .env
```

#### 切换到本地环境
```bash
# Windows
copy .env.local .env

# Linux/Mac
cp .env.local .env
```

#### 切换到远程环境
```bash
# Windows
copy .env.remote .env

# Linux/Mac
cp .env.remote .env
```

## 验证配置

切换后验证配置是否正确：

```bash
# 方法1: 使用验证脚本
python scripts/validate_config.py

# 方法2: 快速检查数据库配置
python -c "from shared.config import settings; print(f'数据库: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}')"
```

预期输出（远程数据库环境）：
```
数据库: 192.168.1.54:5432/mold_cost_db
```

## 启动应用

切换配置后，重启应用使配置生效：

```bash
# 停止当前运行的应用（如果有）
# Ctrl+C

# 重新启动
python main.py
```

## 配置对比

| 配置项 | 本地环境 | 远程数据库环境 | 远程环境 |
|--------|----------|----------------|----------|
| 数据库 | localhost | 192.168.1.54 | 192.168.1.54 |
| Redis | localhost | localhost | 192.168.0.41 |
| RabbitMQ | localhost | localhost | 192.168.0.41 |
| MinIO | localhost | localhost | 192.168.0.41 |
| 适用场景 | 本地开发 | 使用生产数据 | 集成测试 |

## 注意事项

### 1. 数据库连接
- 远程数据库需要网络连接
- 确保防火墙允许访问端口 5432
- 远程数据库名称为 `mold_cost_db`（不是 `mold_cost`）

### 2. 本地服务
使用远程数据库环境时，仍需启动本地Docker服务：
```bash
cd infrastructure
docker-compose up -d redis rabbitmq minio
```

### 3. 配置文件管理
- `.env` 文件不应提交到Git（已在 .gitignore 中）
- `.env.*` 模板文件可以提交
- 生产环境配置应使用环境变量或密钥管理服务

### 4. 重启应用
配置切换后必须重启应用才能生效

### 5. 数据一致性
- 本地数据库和远程数据库的数据可能不同
- 切换环境时注意数据差异

## 故障排查

### 问题1: 无法连接远程数据库

**检查**:
```bash
# 测试网络连接
ping 192.168.1.54

# 测试数据库端口
telnet 192.168.1.54 5432
# 或
nc -zv 192.168.1.54 5432
```

**解决**:
- 检查网络连接
- 检查防火墙设置
- 确认数据库服务运行中

### 问题2: 配置未生效

**检查**:
```bash
# 查看当前配置
python -c "from shared.config import settings; print(settings.DB_HOST)"
```

**解决**:
- 确认 `.env` 文件已更新
- 重启应用
- 清除Python缓存：`rm -rf **/__pycache__`

### 问题3: 本地服务未启动

**检查**:
```bash
cd infrastructure
docker-compose ps
```

**解决**:
```bash
# 启动所有服务
docker-compose up -d

# 或只启动需要的服务
docker-compose up -d redis rabbitmq minio
```

## 环境变量优先级

配置加载优先级（从高到低）：
1. 系统环境变量
2. `.env` 文件
3. `shared/config.py` 中的默认值

临时覆盖配置：
```bash
# Windows
set DB_HOST=192.168.1.54
python main.py

# Linux/Mac
DB_HOST=192.168.1.54 python main.py
```

## 相关文件

- `.env` - 当前使用的配置（不提交到Git）
- `.env.local` - 本地环境配置模板
- `.env.remote_db` - 远程数据库环境配置模板 ⭐ 新增
- `.env.remote` - 远程环境配置模板
- `.env.example` - 配置示例
- `switch_env.bat` - Windows切换脚本
- `switch_env.sh` - Linux/Mac切换脚本
- `shared/config.py` - 统一配置模块
- `scripts/validate_config.py` - 配置验证脚本

## 快速参考

```bash
# 切换到远程数据库环境
./switch_env.bat  # Windows
./switch_env.sh   # Linux/Mac
# 选择选项 2

# 验证配置
python scripts/validate_config.py

# 启动本地服务
cd infrastructure
docker-compose up -d redis rabbitmq minio

# 启动应用
python main.py
```

## 更新日志

### 2026-02-27
- ✅ 新增 `.env.remote_db` 远程数据库配置
- ✅ 创建环境切换脚本（Windows/Linux）
- ✅ 添加配置验证功能
- ✅ 完善文档说明
