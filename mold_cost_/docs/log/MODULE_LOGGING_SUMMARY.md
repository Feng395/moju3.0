# 模块分类日志功能总结

## 📋 功能概述

为了便于日志维护和问题排查，日志系统现在支持按功能模块自动分类保存日志。

## ✅ 已完成

### 1. 核心功能实现

- ✅ 在 `logging_config.py` 中添加模块分类支持
- ✅ 在 `unified_logging.py` 中添加模块分类支持
- ✅ 实现 `ModuleFilter` 过滤器类
- ✅ 更新 API Gateway 启用模块分类
- ✅ 创建测试脚本验证功能

### 2. 日志文件结构

```
logs/
├── app.log              # 总日志（所有模块）- 8.9MB
├── error.log            # 错误日志（ERROR及以上）- 122KB
├── api_gateway.log      # API Gateway 日志 - 285 bytes
├── workers.log          # Workers 日志 - 261 bytes
├── agents.log           # Agents 日志 - 255 bytes
├── mcp_services.log     # MCP 服务日志 - 291 bytes
├── scripts.log          # Scripts 日志 - 261 bytes
└── shared.log           # Shared 模块日志 - 255 bytes
```

### 3. 测试验证

运行测试脚本：
```bash
cd mold_cost_
python test_module_logging.py
```

测试结果：
- ✅ 所有模块日志文件正常生成
- ✅ 日志正确分类到对应文件
- ✅ app.log 包含所有日志
- ✅ error.log 仅包含错误日志
- ✅ 各模块日志文件仅包含对应模块的日志

## 🎯 使用方法

### 启用模块分类日志

#### 方式1：API Gateway（使用 logging_config.py）

```python
from shared.logging_config import setup_logging, get_logger

setup_logging(
    level="INFO",
    enable_console=True,
    enable_file=True,
    enable_module_logs=True  # 启用模块分类
)

logger = get_logger(__name__)
```

#### 方式2：Workers/MCP（使用 unified_logging.py）

```python
from shared.unified_logging import init_logging, get_logger

init_logging(
    enable_module_logs=True  # 启用模块分类
)

logger = get_logger(__name__)
```

### 环境变量配置

在 `.env` 文件中添加：

```bash
# 启用模块分类日志
ENABLE_MODULE_LOGS=true
```

## 📊 优势对比

### 之前（单一日志文件）

❌ 所有日志混在一起，难以查找  
❌ 日志文件过大，打开缓慢  
❌ 无法针对特定模块分析  
❌ 噪音太多，影响排查效率

### 现在（模块分类日志）

✅ 日志按模块分类，清晰明了  
✅ 单个文件较小，快速打开  
✅ 可以针对特定模块分析  
✅ 减少噪音，提高排查效率  
✅ 保留总日志，便于全局查看

## 🔍 实际应用场景

### 场景1：调试 API 接口问题

```bash
# 只查看 API Gateway 日志
tail -f logs/api_gateway.log

# 搜索特定请求
grep "user_id=U001" logs/api_gateway.log
```

### 场景2：排查 Worker 任务失败

```bash
# 只查看 Workers 日志
tail -f logs/workers.log

# 搜索特定任务
grep "job_id=J001" logs/workers.log
```

### 场景3：分析 Agent 业务逻辑

```bash
# 只查看 Agents 日志
tail -f logs/agents.log

# 搜索价格计算
grep "价格计算" logs/agents.log
```

### 场景4：监控系统错误

```bash
# 查看所有错误
tail -f logs/error.log

# 统计各模块错误数量
grep "ERROR" logs/error.log | cut -d'-' -f2 | sort | uniq -c
```

### 场景5：全局搜索

```bash
# 在总日志中搜索
grep "job_id=J001" logs/app.log

# 追踪完整流程
grep "job_id=J001" logs/app.log | less
```

## 📈 性能影响

### 测试数据

- **写入性能**：无明显影响（多个 handler 并行写入）
- **文件大小**：单个文件更小，便于管理
- **查询速度**：显著提升（文件更小，内容更集中）

### 资源占用

- **磁盘空间**：略有增加（每个模块一个文件）
- **文件句柄**：增加 6 个（每个模块一个）
- **内存占用**：无明显增加

## 🎨 日志格式

所有日志文件使用统一格式：

```
时间 - 模块名 - 级别 - 消息
```

示例：
```
2026-03-02 09:08:44 - api_gateway.routers.jobs - INFO - 收到上传请求: user_id=U001
2026-03-02 09:08:45 - workers.all_tasks_worker - INFO - 开始处理任务: job_id=J001
2026-03-02 09:08:46 - agents.cad_agent - INFO - 开始拆图: job_id=J001
```

## 🔧 配置选项

### 完整配置示例

```python
# logging_config.py
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

### 模块配置

当前支持的模块：

1. **api_gateway** - API Gateway 相关
2. **workers** - Workers 相关
3. **agents** - Agents 相关
4. **mcp_services** - MCP 服务相关
5. **scripts** - Scripts 相关
6. **shared** - Shared 模块相关

### 添加新模块

如需添加新模块，在 `logging_config.py` 或 `unified_logging.py` 中修改 `module_configs`：

```python
module_configs = [
    # ... 现有配置 ...
    {
        "name": "new_module",
        "filename": "new_module.log",
        "filter_prefix": "new_module",
        "description": "新模块日志"
    }
]
```

## 📝 最佳实践

### 1. 命名规范

使用模块前缀命名 logger：

```python
# ✅ 好的命名
logger = get_logger("api_gateway.routers.jobs")
logger = get_logger("workers.all_tasks_worker")
logger = get_logger("agents.cad_agent")

# ❌ 不好的命名
logger = get_logger("jobs")  # 无法识别模块
logger = get_logger("worker")  # 无法识别模块
```

### 2. 日志级别

- **开发环境**：DEBUG 或 INFO
- **测试环境**：INFO
- **生产环境**：INFO 或 WARNING

### 3. 日志内容

包含关键信息：

```python
# ✅ 好的日志
logger.info(f"开始处理任务: job_id={job_id}, user_id={user_id}")
logger.info(f"任务处理完成: job_id={job_id}, 耗时={elapsed:.2f}s")

# ❌ 不好的日志
logger.info("开始处理")  # 缺少关键信息
logger.info(f"job_id: {job_id}")  # 格式不统一
```

### 4. 错误处理

记录完整的错误信息：

```python
try:
    # 执行操作
    result = process_job(job_id)
except Exception as e:
    logger.error(
        f"任务处理失败: job_id={job_id}, 原因={str(e)}",
        exc_info=True  # 包含堆栈信息
    )
```

## 🎉 总结

### 主要改进

1. ✅ 日志按模块自动分类
2. ✅ 便于快速定位问题
3. ✅ 减少日志噪音
4. ✅ 提高排查效率
5. ✅ 保留总日志用于全局查看

### 下一步

- [ ] 添加日志监控告警
- [ ] 集成日志分析工具
- [ ] 添加日志统计报表
- [ ] 优化日志查询性能

---

**文档版本**: 1.0.0  
**更新日期**: 2026-03-02  
**维护人员**: 系统架构团队  
**测试状态**: ✅ 已验证
