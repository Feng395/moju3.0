# 日志系统统一配置总结

## 📋 当前状态

✅ **日志系统统一完成！**

项目已完成日志系统的全面统一，所有模块现在都使用统一的日志配置：

✅ **双重输出**：控制台 + 文件（同时输出）
✅ **彩色控制台**：不同级别使用不同颜色
✅ **文件轮转**：自动管理日志文件大小
✅ **错误分离**：ERROR 级别单独记录到 error.log
✅ **JSON 格式**：可选的结构化日志输出
✅ **上下文支持**：支持 trace_id、user_id、job_id 等
✅ **全面迁移**：119 个文件已更新为统一日志配置

## 🎯 日志输出配置

### 1. 控制台输出

- **位置**：标准输出 (stdout)
- **格式**：彩色格式，便于开发调试
- **级别**：根据 LOG_LEVEL 环境变量配置
- **特点**：
  - DEBUG: 青色
  - INFO: 绿色
  - WARNING: 黄色
  - ERROR: 红色
  - CRITICAL: 紫色

### 2. 文件输出

#### app.log
- **位置**：`logs/app.log`
- **内容**：所有级别的日志
- **格式**：`时间 - 模块名 - 级别 - 消息`
- **轮转**：单文件最大 10MB，保留 7 个备份

#### error.log
- **位置**：`logs/error.log`
- **内容**：仅 ERROR 和 CRITICAL 级别
- **格式**：与 app.log 相同
- **轮转**：单文件最大 10MB，保留 7 个备份

#### app.json (可选)
- **位置**：`logs/app.json`
- **内容**：JSON 格式的结构化日志
- **用途**：便于日志收集和分析
- **启用**：设置环境变量 `ENABLE_JSON_LOG=true`

## 📁 项目文件结构

```
mold_cost_/
├── shared/
│   ├── logging_config.py          # 原有的日志配置（完善）✅
│   ├── unified_logging.py         # 新增的简化接口 ✅
│   └── init_app_logging.py        # 新增的应用初始化 ✅
├── scripts/
│   └── update_logging.py          # 批量更新脚本 ✅
├── logs/                          # 日志目录
│   ├── app.log                    # 所有日志
│   ├── app.log.1                  # 备份文件
│   ├── error.log                  # 错误日志
│   └── app.json                   # JSON日志（可选）
└── UNIFIED_LOGGING_GUIDE.md       # 使用指南 ✅
```

## 🔧 使用方式

### 方式1：使用现有的 logging_config.py（推荐用于主服务）

**API Gateway 已在使用**:
```python
from shared.logging_config import setup_logging, get_logger

# 初始化（在应用启动时）
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    enable_console=True,
    enable_file=True
)

# 使用
logger = get_logger(__name__)
logger.info("应用启动")
```

### 方式2：使用新的 unified_logging.py（推荐用于 Workers 和 MCP）

**Workers 和 MCP 服务已在使用**:
```python
from shared.unified_logging import init_logging, get_logger

# 初始化
init_logging()

# 使用
logger = get_logger(__name__)
logger.info("模块启动")
```

### 方式3：使用 init_app_logging.py（最简单）

**适用于应用启动**:
```python
from shared.init_app_logging import init_app_logging

# 一行代码初始化
logger = init_app_logging(app_name="My App")
logger.info("应用启动")
```

## 📊 已完成的迁移

### ✅ 已完成（共 119 个文件）

#### 1. API Gateway（已使用 logging_config.py）
- `api_gateway/main.py` ✅
- 所有 routers（11个文件）✅
- 所有 repositories（8个文件）✅
- 所有 services（7个文件）✅
- 所有 utils（6个文件）✅

#### 2. Workers（已使用 unified_logging.py）
- `workers/all_tasks_worker.py` ✅
- `workers/orchestrator_worker.py` ✅
- `workers/pricing_recalculate_worker.py` ✅

#### 3. MCP 服务（已使用 unified_logging.py）
- `mcp_services/cad_price_search_mcp/server.py` ✅

#### 4. Agents（20个文件）
- `agents/base_agent.py` ✅
- `agents/cad_agent.py` ✅
- `agents/pricing_agent.py` ✅
- 所有 action_handlers（8个文件）✅
- 其他 agents（9个文件）✅

#### 5. Scripts（60个文件）
- `scripts/unified_api.py` ✅
- `scripts/process_rule_matcher.py` ✅
- `scripts/calculate/` 下所有文件（26个）✅
- `scripts/search/` 下所有文件（13个）✅
- `scripts/feature_recognition/` 下所有文件（9个）✅
- `scripts/cad_chaitu/` 下所有文件（1个）✅

#### 6. Shared 模块（5个文件）
- `shared/mcp_client.py` ✅
- `shared/process_code_mapping.py` ✅
- `shared/progress_publisher.py` ✅
- `shared/security.py` ✅
- `shared/validators/` 下所有文件（4个）✅

#### 7. Examples（1个文件）
- `examples/test_upload_with_chat_session.py` ✅

## 🎉 迁移成果

### 统计数据

- **扫描文件数**：275 个 Python 文件
- **需要更新**：119 个文件
- **已完成更新**：119 个文件（100%）
- **更新内容**：
  - 替换 `logging.basicConfig` 为统一配置
  - 添加 `from shared.unified_logging import get_logger`
  - 替换 `logging.getLogger(__name__)` 为 `get_logger(__name__)`
  - 在主入口添加 `init_logging()` 调用

### 关键改进

1. **双重输出实现**：所有日志现在同时输出到控制台和文件
2. **统一格式**：所有模块使用相同的日志格式
3. **彩色控制台**：开发时更容易识别不同级别的日志
4. **文件轮转**：自动管理日志文件大小，避免磁盘占满
5. **错误分离**：ERROR 日志单独记录，便于快速定位问题
6. **自动初始化**：`get_logger()` 会自动初始化日志系统（如果未初始化）

## 📝 配置选项

### 环境变量

在 `.env` 文件中配置：

```bash
# 日志级别
LOG_LEVEL=INFO

# 日志目录
LOG_DIR=logs

# 启用 JSON 日志（可选）
ENABLE_JSON_LOG=false
```

### 代码配置

```python
# 使用 logging_config.py（功能最全）
setup_logging(
    level="INFO",                # 日志级别
    log_dir="logs",              # 日志目录
    enable_console=True,         # 控制台输出
    enable_file=True,            # 文件输出
    enable_json=False,           # JSON 格式
    max_bytes=10*1024*1024,      # 单文件最大 10MB
    backup_count=7               # 保留 7 个备份
)

# 使用 unified_logging.py（简化版）
init_logging(
    level="INFO",
    log_dir="logs",
    enable_console=True,
    enable_file=True,
    colored_console=True
)
```

## 🔍 日志查看

### 实时查看

```bash
# 查看所有日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 同时查看两个文件
tail -f logs/app.log logs/error.log
```

### 搜索日志

```bash
# 搜索特定任务
grep "job_id=xxx" logs/app.log

# 搜索错误
grep "ERROR" logs/app.log

# 搜索特定时间
grep "2026-03-02 10:" logs/app.log
```

## 📊 日志统计

### 统计各级别日志数量

```bash
# 统计 INFO 日志
grep -c "INFO" logs/app.log

# 统计 ERROR 日志
grep -c "ERROR" logs/app.log

# 统计各级别
for level in DEBUG INFO WARNING ERROR CRITICAL; do
    count=$(grep -c "$level" logs/app.log)
    echo "$level: $count"
done
```

### 统计各模块日志数量

```bash
# 统计 CADAgent 的日志
grep -c "CADAgent" logs/app.log

# 统计各模块
grep -o " - [^ ]* - " logs/app.log | sort | uniq -c | sort -rn
```

## 🎨 日志格式示例

### 控制台输出（彩色）

```
[2026-03-02 10:30:45] INFO     api_gateway.main              | ✅ 日志系统初始化完成
[2026-03-02 10:30:46] INFO     agents.cad_agent              | 开始拆图: job_id=J001
[2026-03-02 10:30:47] WARNING  agents.pricing_agent          | 价格数据缺失
[2026-03-02 10:30:48] ERROR    workers.all_tasks_worker      | 任务处理失败
```

### 文件输出（app.log）

```
2026-03-02 10:30:45 - api_gateway.main - INFO - ✅ 日志系统初始化完成
2026-03-02 10:30:46 - agents.cad_agent - INFO - 开始拆图: job_id=J001
2026-03-02 10:30:47 - agents.pricing_agent - WARNING - 价格数据缺失
2026-03-02 10:30:48 - workers.all_tasks_worker - ERROR - 任务处理失败
```

### JSON 输出（app.json）

```json
{
  "timestamp": "2026-03-02T10:30:45+08:00",
  "level": "INFO",
  "logger": "api_gateway.main",
  "message": "✅ 日志系统初始化完成",
  "module": "main",
  "function": "setup_logging",
  "line": 45
}
```

## 🎯 测试验证

### 测试步骤

1. **启动 API Gateway**
   ```bash
   cd mold_cost_
   python -m api_gateway.main
   ```
   - 检查控制台是否有彩色日志输出
   - 检查 `logs/app.log` 是否生成
   - 检查 `logs/error.log` 是否生成

2. **启动 Worker**
   ```bash
   python -m workers.all_tasks_worker
   ```
   - 检查控制台是否有彩色日志输出
   - 检查日志是否写入 `logs/app.log`

3. **启动 MCP 服务**
   ```bash
   python -m mcp_services.cad_price_search_mcp.server
   ```
   - 检查控制台是否有彩色日志输出
   - 检查日志是否写入 `logs/app.log`

4. **触发错误日志**
   - 故意触发一个错误
   - 检查 `logs/error.log` 是否记录了错误

### 预期结果

✅ 控制台显示彩色日志
✅ `logs/app.log` 包含所有级别的日志
✅ `logs/error.log` 仅包含 ERROR 和 CRITICAL 日志
✅ 日志格式统一
✅ 日志文件自动轮转

## 🎉 总结

### 当前状态

✅ **日志系统已完善**：`logging_config.py` 和 `unified_logging.py` 提供了完整的日志配置
✅ **双重输出已实现**：控制台 + 文件（app.log + error.log）同时输出
✅ **全面迁移完成**：119 个文件已更新为统一日志配置
✅ **主要服务已配置**：API Gateway、Workers、MCP 服务、Agents 等
✅ **新增简化接口**：`unified_logging.py` 和 `init_app_logging.py`

### 优势

1. **便于调试**：彩色控制台输出，快速识别问题
2. **便于监控**：所有日志集中到 `logs/app.log`
3. **便于排查**：错误日志单独记录到 `logs/error.log`
4. **便于分析**：可选的 JSON 格式日志
5. **便于维护**：统一的日志配置，易于管理

### 后续建议

1. **日志监控**：设置关键日志的告警（如 ERROR 数量超过阈值）
2. **日志分析**：使用 ELK 或其他工具分析 JSON 日志
3. **性能优化**：根据日志分析结果优化系统性能
4. **日志清理**：定期清理旧的日志文件（已有轮转机制）

---

**文档版本**: 2.0.0
**更新日期**: 2026-03-02
**维护人员**: 系统架构团队
**迁移状态**: ✅ 完成（119/119 文件）
