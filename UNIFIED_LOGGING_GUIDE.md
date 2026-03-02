# 统一日志系统使用指南

## 📋 概述

项目已统一日志配置，所有日志将同时输出到：
1. **控制台**：彩色输出，便于开发调试
2. **文件**：
   - `logs/app.log` - 所有级别的日志
   - `logs/error.log` - 仅ERROR及以上级别的日志

## 🎯 核心特性

- ✅ 统一的日志格式
- ✅ 控制台彩色输出
- ✅ 文件自动轮转（单文件最大10MB，保留7个备份）
- ✅ 错误日志单独记录
- ✅ 支持日志级别配置
- ✅ 支持日志上下文（job_id、user_id等）

## 🚀 快速开始

### 1. 在应用启动时初始化（推荐）

**API Gateway (api_gateway/main.py)**:
```python
from shared.init_app_logging import init_app_logging, get_app_logger

# 在应用启动时初始化
init_app_logging(app_name="API Gateway")

# 在其他地方使用
logger = get_app_logger(__name__)
logger.info("API Gateway 启动成功")
```

**MCP 服务 (mcp_services/cad_price_search_mcp/server.py)**:
```python
from shared.init_app_logging import init_mcp_logging, get_app_logger

# 初始化
init_mcp_logging(service_name="CAD Price Search MCP")

# 使用
logger = get_app_logger(__name__)
logger.info("MCP 服务启动")
```

**Worker (workers/all_tasks_worker.py)**:
```python
from shared.init_app_logging import init_worker_logging, get_app_logger

# 初始化
init_worker_logging(worker_name="All Tasks Worker")

# 使用
logger = get_app_logger(__name__)
logger.info("Worker 启动")
```

**脚本 (scripts/xxx.py)**:
```python
from shared.unified_logging import quick_init_logging

# 一行代码初始化并获取 logger
logger = quick_init_logging(__name__)
logger.info("脚本开始执行")
```

### 2. 在模块中使用

**Agent (agents/cad_agent.py)**:
```python
from shared.unified_logging import get_logger

# 获取 logger（无需初始化，应用启动时已初始化）
logger = get_logger(__name__)

class CADAgent:
    def __init__(self):
        logger.info("CAD Agent 初始化")
    
    def process(self):
        logger.info("开始处理")
        try:
            # 业务逻辑
            logger.debug("详细调试信息")
        except Exception as e:
            logger.error("处理失败", exc_info=True)
```

## 📝 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 详细调试信息 | `logger.debug("变量值: x=10")` |
| INFO | 正常业务流程 | `logger.info("任务开始: job_id=xxx")` |
| WARNING | 警告信息 | `logger.warning("配置缺失，使用默认值")` |
| ERROR | 错误信息 | `logger.error("数据库连接失败", exc_info=True)` |
| CRITICAL | 严重错误 | `logger.critical("系统崩溃")` |

## 🎨 日志格式

### 控制台输出（彩色）

```
[2026-02-28 10:30:45] INFO     api_gateway.main              | API Gateway 启动成功
[2026-02-28 10:30:46] DEBUG    agents.cad_agent              | 开始拆图: job_id=J001
[2026-02-28 10:30:47] WARNING  agents.pricing_agent          | 价格数据缺失，使用默认值
[2026-02-28 10:30:48] ERROR    workers.all_tasks_worker      | 任务处理失败
```

### 文件输出（logs/app.log）

```
2026-02-28 10:30:45 - api_gateway.main - INFO - API Gateway 启动成功
2026-02-28 10:30:46 - agents.cad_agent - DEBUG - 开始拆图: job_id=J001
2026-02-28 10:30:47 - agents.pricing_agent - WARNING - 价格数据缺失，使用默认值
2026-02-28 10:30:48 - workers.all_tasks_worker - ERROR - 任务处理失败
```

## 🔧 配置选项

### 环境变量配置

在 `.env` 文件中配置：

```bash
# 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
LOG_LEVEL=INFO

# 日志目录
LOG_DIR=logs
```

### 代码配置

```python
from shared.unified_logging import init_logging

# 自定义配置
init_logging(
    level="DEBUG",              # 日志级别
    log_dir="custom_logs",      # 自定义日志目录
    enable_console=True,        # 启用控制台输出
    enable_file=True,           # 启用文件输出
    colored_console=True        # 启用彩色控制台
)
```

## 📊 高级用法

### 1. 日志上下文

为日志添加额外的上下文信息：

```python
from shared.unified_logging import LogContext, get_logger

logger = get_logger(__name__)

# 使用上下文
with LogContext(job_id="J001", user_id="U123"):
    logger.info("开始处理任务")  # 日志会包含 job_id 和 user_id
    # ... 业务逻辑
    logger.info("任务完成")
```

### 2. 异常日志

记录异常信息和堆栈：

```python
try:
    # 业务逻辑
    result = process_data()
except Exception as e:
    # 记录完整的异常信息和堆栈
    logger.error("处理失败", exc_info=True)
    # 或者
    logger.exception("处理失败")  # 自动包含 exc_info=True
```

### 3. 性能日志

记录代码块的执行时间：

```python
import time

start_time = time.time()
# 业务逻辑
result = expensive_operation()
elapsed = time.time() - start_time

logger.info(f"操作完成: 耗时={elapsed:.3f}s")
```

### 4. 结构化日志

使用字典记录结构化信息：

```python
logger.info(
    "任务完成",
    extra={
        "job_id": "J001",
        "subgraph_count": 100,
        "duration": 45.2,
        "status": "success"
    }
)
```

## 🔍 日志查看

### 实时查看

```bash
# 查看所有日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看最近100行
tail -n 100 logs/app.log
```

### 搜索日志

```bash
# 搜索特定任务
grep "job_id=J001" logs/app.log

# 搜索错误
grep "ERROR" logs/app.log

# 搜索特定模块
grep "CADAgent" logs/app.log

# 组合搜索
grep "job_id=J001" logs/app.log | grep "ERROR"
```

## 📦 迁移指南

### 从旧的日志配置迁移

**旧代码**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

**新代码**:
```python
from shared.unified_logging import get_logger

# 无需 basicConfig，应用启动时已初始化
logger = get_logger(__name__)
```

### 批量更新

使用提供的脚本批量更新所有文件：

```bash
cd mold_cost_
python scripts/update_logging.py
```

## 🎯 最佳实践

### 1. 日志级别选择

- **DEBUG**: 仅在开发环境使用，记录详细的调试信息
- **INFO**: 记录正常的业务流程节点
- **WARNING**: 记录可能的问题，但不影响主流程
- **ERROR**: 记录错误，需要关注和处理
- **CRITICAL**: 记录严重错误，系统无法继续运行

### 2. 日志内容

**好的日志**:
```python
logger.info(f"开始处理任务: job_id={job_id}, subgraph_count={count}")
logger.info(f"任务完成: job_id={job_id}, 耗时={duration:.2f}s, 成功={success}, 失败={failed}")
```

**不好的日志**:
```python
logger.info("开始处理")  # 缺少关键信息
logger.info(f"job_id: {job_id}")  # 信息分散
```

### 3. 异常处理

**好的做法**:
```python
try:
    result = process_data()
except ValueError as e:
    logger.error(f"数据验证失败: {e}", exc_info=True)
    raise
except Exception as e:
    logger.error(f"未知错误: {e}", exc_info=True)
    raise
```

**不好的做法**:
```python
try:
    result = process_data()
except:
    logger.error("出错了")  # 缺少异常信息
    pass  # 吞掉异常
```

### 4. 性能考虑

```python
# 避免在循环中记录过多日志
for i in range(10000):
    # ❌ 不好：产生10000条日志
    logger.debug(f"处理第 {i} 项")

# ✅ 好：批量记录
batch_size = 1000
for i in range(0, 10000, batch_size):
    logger.info(f"处理进度: {i}/{10000}")
```

## 🐛 故障排查

### 问题1：日志没有输出

**检查**:
1. 是否调用了 `init_logging()` 或 `init_app_logging()`
2. 日志级别是否正确（DEBUG < INFO < WARNING < ERROR < CRITICAL）
3. 是否有权限写入日志目录

**解决**:
```python
# 在应用启动时添加
from shared.init_app_logging import init_app_logging
init_app_logging(app_name="My App")
```

### 问题2：日志文件过大

**检查**:
- 日志文件是否正常轮转
- 是否有过多的DEBUG日志

**解决**:
```bash
# 调整日志级别为 INFO
export LOG_LEVEL=INFO

# 或在代码中设置
init_logging(level="INFO")
```

### 问题3：找不到日志文件

**检查**:
- 日志目录是否存在
- 是否有写入权限

**解决**:
```bash
# 创建日志目录
mkdir -p logs

# 检查权限
ls -la logs/
```

## 📚 相关文档

- [Y.md](Y.md) - 系统架构和日志关键点
- [LOG_QUICK_REFERENCE.md](LOG_QUICK_REFERENCE.md) - 日志快速参考
- [Y_LOG_ENHANCEMENT_SUMMARY.md](Y_LOG_ENHANCEMENT_SUMMARY.md) - 日志增强总结

## 🎉 总结

统一日志系统的优势：

✅ **简单易用**：一行代码初始化，无需重复配置
✅ **双重输出**：控制台 + 文件，开发和生产都方便
✅ **自动轮转**：日志文件自动管理，不会无限增长
✅ **彩色输出**：控制台彩色显示，提升可读性
✅ **错误分离**：错误日志单独记录，便于排查
✅ **统一格式**：所有模块使用相同格式，便于分析

---

**版本**: 1.0.0
**更新日期**: 2026-02-28
**维护人员**: 系统架构团队
