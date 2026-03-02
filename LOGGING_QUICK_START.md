# 日志系统快速开始

## 🚀 5分钟上手

### 1. 主服务（API Gateway）

```python
from shared.logging_config import setup_logging, get_logger

# 在 main.py 开头初始化
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    enable_console=True,
    enable_file=True
)

logger = get_logger(__name__)
logger.info("✅ 服务启动")
```

### 2. Workers 和 MCP 服务

```python
from shared.unified_logging import init_logging, get_logger

# 在文件开头初始化
init_logging()

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

- **logs/app.log** - 所有日志
- **logs/error.log** - 仅错误日志

## 🔍 查看日志

```bash
# 实时查看
tail -f logs/app.log

# 查看错误
tail -f logs/error.log

# 搜索
grep "ERROR" logs/app.log
```

## ⚙️ 配置（.env）

```bash
LOG_LEVEL=INFO
LOG_DIR=logs
```

## 📚 完整文档

- **UNIFIED_LOGGING_COMPLETE.md** - 完整迁移报告
- **LOGGING_SYSTEM_SUMMARY.md** - 系统总结
- **UNIFIED_LOGGING_GUIDE.md** - 详细指南
