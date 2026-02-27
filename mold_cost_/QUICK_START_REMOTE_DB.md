# 快速开始 - 使用远程数据库

## 一键切换到远程数据库

### Windows
```bash
switch_env.bat
# 选择选项 2
```

### Linux/Mac
```bash
chmod +x switch_env.sh
./switch_env.sh
# 选择选项 2
```

## 手动切换步骤

### 1. 切换配置文件
```bash
# Windows
copy .env.remote_db .env

# Linux/Mac
cp .env.remote_db .env
```

### 2. 验证配置
```bash
python scripts/validate_config.py
```

预期输出：
```
✅ 数据库配置正确 - 使用远程数据库 (192.168.1.54:5432/mold_cost_db)
✅ Redis配置正确 - 使用本地Redis
✅ RabbitMQ配置正确 - 使用本地RabbitMQ
✅ MinIO配置正确 - 使用本地MinIO
```

### 3. 启动本地服务
```bash
cd infrastructure
docker-compose up -d redis rabbitmq minio
```

### 4. 启动应用
```bash
cd ..
python main.py
```

## 配置说明

使用远程数据库环境时：

| 服务 | 地址 | 说明 |
|------|------|------|
| 数据库 | 192.168.1.54:5432 | 远程PostgreSQL |
| Redis | localhost:6379 | 本地Docker |
| RabbitMQ | localhost:5672 | 本地Docker |
| MinIO | localhost:9000 | 本地Docker |

## 优势

1. ✅ 使用生产数据库数据
2. ✅ 本地服务便于调试
3. ✅ 无需维护本地数据库
4. ✅ 快速切换环境

## 切换回本地环境

```bash
# Windows
switch_env.bat
# 选择选项 1

# Linux/Mac
./switch_env.sh
# 选择选项 1
```

## 故障排查

### 无法连接远程数据库

1. 检查网络连接
```bash
ping 192.168.1.54
```

2. 检查数据库端口
```bash
telnet 192.168.1.54 5432
```

3. 检查防火墙设置

### 本地服务未启动

```bash
cd infrastructure
docker-compose ps
docker-compose up -d redis rabbitmq minio
```

## 相关文档

- `ENV_SWITCH_GUIDE.md` - 完整的环境切换指南
- `CONFIG_UNIFIED_GUIDE.md` - 统一配置管理指南
- `QUICK_CONFIG_REFERENCE.md` - 配置快速参考
