# 日志系统文档索引

## 📚 文档列表

### 快速开始
- **[LOGGING_QUICK_START.md](LOGGING_QUICK_START.md)** - 5分钟快速上手指南

### 核心文档
- **[LOG_FILE_STRUCTURE.md](LOG_FILE_STRUCTURE.md)** - 日志文件结构详解
- **[MODULE_LOGGING_SUMMARY.md](MODULE_LOGGING_SUMMARY.md)** - 模块分类日志功能总结
- **[LOGGING_SYSTEM_SUMMARY.md](LOGGING_SYSTEM_SUMMARY.md)** - 日志系统完整总结
- **[UNIFIED_LOGGING_COMPLETE.md](UNIFIED_LOGGING_COMPLETE.md)** - 统一日志迁移报告

### 参考文档
- **[UNIFIED_LOGGING_GUIDE.md](UNIFIED_LOGGING_GUIDE.md)** - 统一日志详细指南
- **[LOG_QUICK_REFERENCE.md](LOG_QUICK_REFERENCE.md)** - 日志快速参考

---

## 🎯 日志系统特性

### 1. 双重输出
✅ 控制台输出（彩色）  
✅ 文件输出（持久化）

### 2. 模块分类
✅ 按功能模块自动分类  
✅ 8个日志文件，便于维护  
✅ 保留总日志，便于全局查看

### 3. 错误分离
✅ 错误日志单独记录  
✅ 快速定位问题

### 4. 自动轮转
✅ 单文件最大 10MB  
✅ 保留 7 个备份  
✅ 自动管理磁盘空间

---

## 📁 日志文件结构

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

---

## 🚀 快速开始

### 1. 配置环境变量

```bash
# .env
LOG_LEVEL=INFO
LOG_DIR=logs
ENABLE_MODULE_LOGS=true
```

### 2. 初始化日志系统

```python
from shared.unified_logging import init_logging, get_logger

# 初始化
init_logging(enable_module_logs=True)

# 使用
logger = get_logger(__name__)
logger.info("应用启动")
```

### 3. 查看日志

```bash
# 查看特定模块
tail -f logs/api_gateway.log

# 查看所有日志
tail -f logs/app.log

# 查看错误
tail -f logs/error.log
```

---

## 🔍 常用命令

### 实时查看

```bash
# 查看 API Gateway 日志
tail -f logs/api_gateway.log

# 查看 Workers 日志
tail -f logs/workers.log

# 查看错误日志
tail -f logs/error.log
```

### 搜索日志

```bash
# 搜索特定任务
grep "job_id=J001" logs/app.log

# 搜索错误
grep "ERROR" logs/error.log

# 搜索特定时间
grep "2026-03-02 10:" logs/app.log
```

### 统计分析

```bash
# 统计各文件行数
wc -l logs/*.log

# 统计错误数量
grep -c "ERROR" logs/error.log

# 统计各模块错误
grep "ERROR" logs/app.log | cut -d'-' -f2 | sort | uniq -c
```

---

## 📊 优势对比

### 之前（单一日志文件）
❌ 所有日志混在一起  
❌ 文件过大，打开缓慢  
❌ 难以定位问题  
❌ 噪音太多

### 现在（模块分类日志）
✅ 日志按模块分类  
✅ 文件较小，快速打开  
✅ 快速定位问题  
✅ 减少噪音  
✅ 保留总日志

---

## 🎨 日志格式

### 控制台输出（彩色）
```
[2026-03-02 10:30:45] INFO     api_gateway.main              | ✅ 服务启动
[2026-03-02 10:30:46] WARNING  agents.pricing_agent          | ⚠️  价格数据缺失
[2026-03-02 10:30:47] ERROR    workers.all_tasks_worker      | ❌ 任务处理失败
```

### 文件输出
```
2026-03-02 10:30:45 - api_gateway.main - INFO - ✅ 服务启动
2026-03-02 10:30:46 - agents.pricing_agent - WARNING - ⚠️  价格数据缺失
2026-03-02 10:30:47 - workers.all_tasks_worker - ERROR - ❌ 任务处理失败
```

---

## 🔧 配置选项

### 完整配置

```python
from shared.logging_config import setup_logging

setup_logging(
    level="INFO",                # 日志级别
    log_dir="logs",              # 日志目录
    enable_console=True,         # 控制台输出
    enable_file=True,            # 文件输出
    enable_module_logs=True,     # 模块分类日志
    enable_json=False,           # JSON 格式
    max_bytes=10*1024*1024,      # 单文件最大 10MB
    backup_count=7               # 保留 7 个备份
)
```

### 环境变量

```bash
LOG_LEVEL=INFO              # 日志级别
LOG_DIR=logs                # 日志目录
ENABLE_JSON_LOG=false       # JSON 格式
ENABLE_MODULE_LOGS=true     # 模块分类
```

---

## 📝 最佳实践

### 1. 命名规范

```python
# ✅ 使用模块前缀
logger = get_logger("api_gateway.routers.jobs")
logger = get_logger("workers.all_tasks_worker")
logger = get_logger("agents.cad_agent")
```

### 2. 日志内容

```python
# ✅ 包含关键信息
logger.info(f"开始处理任务: job_id={job_id}, user_id={user_id}")
logger.info(f"任务处理完成: job_id={job_id}, 耗时={elapsed:.2f}s")
```

### 3. 错误处理

```python
# ✅ 记录完整错误信息
try:
    result = process_job(job_id)
except Exception as e:
    logger.error(
        f"任务处理失败: job_id={job_id}, 原因={str(e)}",
        exc_info=True  # 包含堆栈信息
    )
```

---

## 🧪 测试验证

运行测试脚本：

```bash
cd mold_cost_
python test_module_logging.py
```

检查生成的日志文件：

```bash
# 查看文件列表
ls -lh logs/

# 查看各文件内容
cat logs/api_gateway.log
cat logs/workers.log
cat logs/error.log
```

---

## 📈 性能指标

- **写入性能**：无明显影响
- **查询速度**：显著提升（文件更小）
- **磁盘空间**：略有增加（多个文件）
- **内存占用**：无明显增加

---

## 🎉 总结

### 主要特性

1. ✅ 双重输出（控制台 + 文件）
2. ✅ 模块分类（8个日志文件）
3. ✅ 错误分离（error.log）
4. ✅ 自动轮转（10MB，7个备份）
5. ✅ 彩色控制台（便于调试）

### 适用场景

- 开发调试
- 问题排查
- 性能分析
- 监控告警
- 日志分析

---

**文档版本**: 1.0.0  
**更新日期**: 2026-03-02  
**维护人员**: 系统架构团队
