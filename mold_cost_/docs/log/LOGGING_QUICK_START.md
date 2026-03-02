# 日志系统快速开始

## 🚀 5分钟上手

### 1. 主服务（API Gateway）

```python
from shared.logging_config import setup_logging, get_logger

# 在 main.py 开头初始化
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    enable_console=True,
    enable_file=True,
    enable_module_logs=True  # 启用模块分类日志
)

logger = get_logger(__name__)
logger.info("✅ 服务启动")
```

### 2. Workers 和 MCP 服务

```python
from shared.unified_logging import init_logging, get_logger

# 在文件开头初始化
init_logging(enable_module_logs=True)  # 启用模块分类日志

logger = get_logger(__name__)
logger.info("✅ Worker 启动")
```

### 3. 普通模块（无需初始化）

```python
from shared.unified_logging import get_logger

# 直接使用
logger = get_logger(__name__)
logger.info("模块加载")
```

## 📁 日志文件位置

### 模块分类日志（推荐）

```
logs/
├── app.log              # 总日志（所有模块）
├── error.log            # 错误日志（ERROR及以上）
├── api_gateway.log      # API Gateway 日志
├── workers.log          # Workers 日志
├── agents.log           # Agents 日志
├── mcp_services.log     # MCP 服务日志
├── scripts.log          # Scripts 日志
└── shared.log           # Shared 模块日志
```

### 优势

✅ **模块隔离**：每个模块的日志独立，便于查看  
✅ **快速定位**：直接查看对应模块的日志文件  
✅ **减少噪音**：不需要在海量日志中搜索  
✅ **保留总览**：app.log 仍然保留所有日志

## 🔍 查看日志

### 查看特定模块

```bash
# 查看 API Gateway 日志
tail -f logs/api_gateway.log

# 查看 Workers 日志
tail -f logs/workers.log

# 查看 Agents 日志
tail -f logs/agents.log
```

### 查看所有日志

```bash
# 实时查看总日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

### 搜索日志

```bash
# 在特定模块中搜索
grep "job_id=J001" logs/workers.log

# 在所有日志中搜索
grep "job_id=J001" logs/app.log
```

## ⚙️ 配置（.env）

```bash
# 日志级别
LOG_LEVEL=INFO

# 日志目录
LOG_DIR=logs

# 启用模块分类日志（推荐）
ENABLE_MODULE_LOGS=true
```

## 📚 完整文档

- **LOG_FILE_STRUCTURE.md** - 日志文件结构详解
- **UNIFIED_LOGGING_COMPLETE.md** - 完整迁移报告
- **LOGGING_SYSTEM_SUMMARY.md** - 系统总结
- **UNIFIED_LOGGING_GUIDE.md** - 详细指南
