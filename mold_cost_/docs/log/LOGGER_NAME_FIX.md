# Logger 名称修复说明

## 🐛 问题描述

在模块分类日志功能中，发现 MCP 服务和 Workers 的日志没有正确输出到对应的日志文件中。

### 问题表现

- `logs/mcp_services.log` - 只有测试日志，没有实际运行日志
- `logs/workers.log` - 只有测试日志，没有实际运行日志
- 实际日志都输出到了 `logs/app.log`

## 🔍 问题原因

### 根本原因

当 Python 脚本作为主程序运行时，`__name__` 的值是 `__main__`，而不是模块的完整路径。

### 示例说明

```python
# 在 mcp_services/cad_price_search_mcp/server.py 中
logger = get_logger(__name__)

# 当作为主程序运行时：
# python -m mcp_services.cad_price_search_mcp.server
# __name__ = "__main__"  ❌ 不是 "mcp_services.xxx"

# 当作为模块导入时：
# from mcp_services.cad_price_search_mcp import server
# __name__ = "mcp_services.cad_price_search_mcp.server"  ✅ 正确
```

### ModuleFilter 的工作原理

```python
class ModuleFilter(logging.Filter):
    def __init__(self, module_prefix: str):
        self.module_prefix = module_prefix  # 例如 "mcp_services"
    
    def filter(self, record: logging.LogRecord) -> bool:
        # 检查 logger 名称是否以指定前缀开头
        return record.name.startswith(self.module_prefix)
        # "__main__".startswith("mcp_services") = False ❌
```

## ✅ 解决方案

### 使用固定的模块名称

不使用 `__name__`，而是使用固定的模块路径字符串。

### 修复前

```python
# ❌ 问题代码
from shared.unified_logging import init_logging, get_logger

init_logging()
logger = get_logger(__name__)  # __name__ = "__main__"
```

### 修复后

```python
# ✅ 修复后
from shared.unified_logging import init_logging, get_logger

init_logging()
# 使用固定的模块名称，确保日志正确分类
logger = get_logger("mcp_services.cad_price_search_mcp.server")
```

## 📝 修复的文件

### 1. MCP 服务

**文件**: `mcp_services/cad_price_search_mcp/server.py`

```python
# 修复前
logger = get_logger(__name__)

# 修复后
logger = get_logger("mcp_services.cad_price_search_mcp.server")
```

### 2. Workers

**文件**: `workers/all_tasks_worker.py`

```python
# 修复前
logger = get_logger(__name__)

# 修复后
logger = get_logger("workers.all_tasks_worker")
```

**文件**: `workers/orchestrator_worker.py`

```python
# 修复前
logger = get_logger(__name__)

# 修复后
logger = get_logger("workers.orchestrator_worker")
```

**文件**: `workers/pricing_recalculate_worker.py`

```python
# 修复前
logger = get_logger(__name__)

# 修复后
logger = get_logger("workers.pricing_recalculate_worker")
```

## 🧪 验证方法

### 1. 启动服务

```bash
# 启动 MCP 服务
cd mold_cost_
python -m mcp_services.cad_price_search_mcp.server

# 启动 Workers
python -m workers.all_tasks_worker
```

### 2. 检查日志文件

```bash
# 查看 MCP 服务日志
tail -f logs/mcp_services.log

# 查看 Workers 日志
tail -f logs/workers.log

# 应该能看到实际的运行日志，而不仅仅是测试日志
```

### 3. 预期结果

**logs/mcp_services.log**:
```
2026-03-02 10:00:00 - mcp_services.cad_price_search_mcp.server - INFO - [OK] CAD 处理模块导入成功
2026-03-02 10:00:01 - mcp_services.cad_price_search_mcp.server - INFO - MCP 服务启动: port=8200
```

**logs/workers.log**:
```
2026-03-02 10:00:00 - workers.all_tasks_worker - INFO - AllTasksWorker 初始化
2026-03-02 10:00:01 - workers.all_tasks_worker - INFO - 开始监听队列
```

## 📊 影响范围

### 受影响的服务

1. ✅ **MCP 服务** - 已修复
2. ✅ **Workers** - 已修复（3个文件）

### 不受影响的服务

1. ✅ **API Gateway** - 使用 `logging_config.py`，logger 名称来自导入路径
2. ✅ **Agents** - 作为模块导入，`__name__` 是正确的
3. ✅ **Scripts** - 作为模块导入，`__name__` 是正确的

## 🎯 最佳实践

### 对于主程序（可以直接运行的脚本）

```python
# ✅ 推荐：使用固定的模块名称
logger = get_logger("workers.my_worker")
logger = get_logger("mcp_services.my_service")
```

### 对于模块（被导入使用的代码）

```python
# ✅ 推荐：使用 __name__
logger = get_logger(__name__)
```

### 判断标准

**使用固定名称的情况**：
- 文件包含 `if __name__ == "__main__":`
- 文件可以直接运行（如 `python xxx.py`）
- 文件是服务的入口点

**使用 __name__ 的情况**：
- 文件只作为模块被导入
- 文件不包含主程序入口
- 文件是库代码或工具函数

## 🔧 通用解决方案

如果不确定使用哪种方式，可以使用以下模式：

```python
import os
from pathlib import Path

# 自动计算模块名称
def get_module_name():
    """自动计算当前文件的模块名称"""
    current_file = Path(__file__).resolve()
    project_root = Path(__file__).parent.parent  # 根据实际情况调整
    
    # 计算相对路径
    relative_path = current_file.relative_to(project_root)
    
    # 转换为模块名称
    module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')
    
    return module_name

# 使用
logger = get_logger(get_module_name())
```

## 📝 总结

### 问题

- 主程序使用 `__name__` 导致 logger 名称为 `__main__`
- ModuleFilter 无法识别，日志未分类

### 解决

- 主程序使用固定的模块名称字符串
- 确保 logger 名称以正确的模块前缀开头

### 效果

- ✅ MCP 服务日志正确输出到 `logs/mcp_services.log`
- ✅ Workers 日志正确输出到 `logs/workers.log`
- ✅ 日志分类功能完全正常

---

**文档版本**: 1.0.0  
**修复日期**: 2026-03-02  
**修复人员**: 系统架构团队  
**状态**: ✅ 已完成
