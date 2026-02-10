# agents 目录合并计划

## 📋 合并头信息标准格式

所有合并后的文件都应在文件头部添加以下信息：

```python
"""
[文件名] - [功能描述]
负责人：[负责人]
版本：[版本号]

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/[文件名] + mold_cost_/agents/[文件名]
- 合并策略：[具体策略]
- 主要改动：
  1. [改动1]
  2. [改动2]
  ...

[原有的文档字符串内容]
"""
```

## 📊 文件对比和合并策略

### 1. `__init__.py`

**对比结果：**
- mold_cost-main: ✅ 完整的单例管理，支持 MCP 客户端
- mold_cost_: ❌ 文件不存在

**合并策略：** 使用 mold_cost-main 版本

**合并后头信息：**
```python
"""
Agent 模块
提供统一的 Agent 实例获取接口

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/__init__.py
- 合并策略：直接使用 mold_cost-main 版本（mold_cost_ 无此文件）
- 主要功能：
  1. 全局单例管理
  2. MCP 客户端统一获取
  3. 各 Agent 实例获取接口
"""
```

---

### 2. `base_agent.py` ⭐ 重点

**对比结果：**
- mold_cost-main: ✅ 增强版 OpResult（支持元数据、质量评分、错误详情、工件列表）
- mold_cost-main: ✅ 增强版 BaseAgent（版本管理、上下文验证、错误构造、操作日志）
- mold_cost_: ✅ 简化版，但使用上海时区

**合并策略：** 使用 mold_cost-main 的增强版，添加时区支持

**需要修改的地方：**
1. 导入时区工具：`from shared.timezone_utils import now_shanghai`
2. 修改 OpResult 的 timestamp：`self.timestamp = now_shanghai()`
3. 修改 BaseAgent 的时间相关方法使用上海时区

**合并后头信息：**
```python
"""
BaseAgent基类
负责人：人员A
版本：v1.2 - 增强 OpResult，标准化输入输出，支持上海时区

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/base_agent.py + mold_cost_/agents/base_agent.py
- 合并策略：使用 mold_cost-main 的增强版，添加 mold_cost_ 的时区支持
- 主要改动：
  1. 保留 mold_cost-main 的增强 OpResult 类（元数据、质量评分、错误详情）
  2. 保留 mold_cost-main 的增强 BaseAgent 类（版本管理、验证、日志）
  3. 添加上海时区支持（now_shanghai）
  4. 所有时间戳使用上海时区

OpResult 增强功能：
- 支持 agent_name, agent_version, execution_id
- 支持 confidence_score（质量评分）
- 支持 warnings（警告列表）
- 支持 error_code, error_details, is_retryable
- 支持 artifacts（工件列表）
- 支持 duration_ms（持续时间）
- 提供 to_dict() 方法

BaseAgent 增强功能：
- 版本号管理
- validate_context() - 上下文验证
- build_error_result() - 标准错误构造
- _log_operation() - 操作日志记录到数据库
"""
```

---

### 3. `cad_agent.py` ⭐ 重点

**对比结果：**
- mold_cost-main: ✅ 完整的 MCP 模式实现，支持并发、进度发布、工艺规则匹配
- mold_cost_: ❌ 简化版，功能不完整

**合并策略：** 使用 mold_cost-main 版本

**合并后头信息：**
```python
"""
CADAgent - CAD拆图与特征识别Agent (MCP模式)
负责人：人员F
版本：v2.0

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/cad_agent.py
- 合并策略：使用 mold_cost-main 版本（功能更完整）
- 主要功能：
  1. 通过 MCP 客户端调用 MCP 服务
  2. 支持并发处理多个子图
  3. 特征识别完成后自动匹配工艺规则
  4. 支持进度发布

职责：
1. 通过 MCP 客户端调用 MCP 服务
2. MCP 服务调用底层工具（拆图/特征识别脚本）
3. 支持并发处理多个子图（并发数可通过环境变量配置）
4. 特征识别完成后自动匹配工艺规则

调用链路：
CAD Agent → MCP Client → MCP Service (cad-price-search-mcp) → 底层工具

并发控制：
- 并发数：从环境变量 FEATURE_RECOGNITION_MAX_CONCURRENT 读取（默认25）
- 连接池：从环境变量 MCP_CLIENT_POOL_SIZE 读取（默认30）
- 自适应：从环境变量 FEATURE_RECOGNITION_ADAPTIVE_CONCURRENCY 控制
"""
```

---

### 4. `interaction_agent.py` ⭐ 重点

**对比结果：**
- mold_cost-main: ❌ 简单版，只处理参数缺失
- mold_cost_: ✅ 完整版，支持数据审核、自然语言处理、多轮对话

**合并策略：** 保留 mold_cost_ 版本

**合并后头信息：**
```python
"""
InteractionAgent - 数据审核和交互Agent (重构版)
负责人：人员B2
版本：v2.0

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost_/agents/interaction_agent.py
- 合并策略：保留 mold_cost_ 版本（功能更完整）
- 主要功能：
  1. 监听 RabbitMQ 消息队列
  2. 查询 3 个表（features, job_price_snapshots, subgraphs）
  3. 通过 WebSocket 推送数据给前端
  4. 接收用户自然语言修改指令
  5. 解析自然语言并推送确认
  6. 支持多轮修改循环
  7. 用户确认后更新数据库

职责：
1. 监听 RabbitMQ 消息队列
2. 查询 3 个表（features, job_price_snapshots, subgraphs）
3. 通过 WebSocket 推送数据给前端
4. 接收用户自然语言修改指令
5. 解析自然语言并推送确认
6. 支持多轮修改循环
7. 用户确认后更新数据库

架构：事件驱动（非阻塞）
"""
```

---

### 5. `nc_time_agent.py` ⭐ 重点

**对比结果：**
- mold_cost-main: ✅ 完整实现，支持 MinIO 文件下载、进度发布、详细日志
- mold_cost_: ❌ 简化版，功能不完整

**合并策略：** 使用 mold_cost-main 版本

**合并后头信息：**
```python
"""
NCTimeAgent - NC时间计算Agent
负责人：人员B1
版本：v2.0

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/nc_time_agent.py
- 合并策略：使用 mold_cost-main 版本（功能更完整）
- 主要功能：
  1. 调用外部 NC Agent 获取每个子图的 NC 时间数据
  2. 解析 NC 返回的 JSON 数据
  3. 将时间数据写入 subgraphs 表
  4. 将详细时间数据写入 features 表
  5. 支持 MinIO 文件自动下载
  6. 支持进度发布

职责：
1. 调用外部 NC Agent 获取每个子图的 NC 时间数据
2. 解析 NC 返回的 JSON 数据
3. 将时间数据写入 subgraphs 表（nc_roughing_time, nc_milling_time, drilling_time）
4. 将详细时间数据写入 features 表（nc_time_cost 字段）
"""
```

---

### 6. `orchestrator_agent.py` ⭐ 重点

**对比结果：**
- mold_cost-main: ✅ 完整的编排流程，支持并行执行、状态管理、进度发布
- mold_cost_: ✅ 使用 LangGraph 构建状态机，但功能较简单

**合并策略：** 使用 mold_cost-main 版本（更成熟）

**合并后头信息：**
```python
"""
OrchestratorAgent - 编排Agent 
负责人：人员B1
版本：v2.1 - 简化流程，支持并行执行

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/orchestrator_agent.py
- 合并策略：使用 mold_cost-main 版本（功能更完整）
- 主要功能：
  1. 调度：按顺序/并行调用各 Agent
  2. 状态管理：更新 jobs 表的状态和进度
  3. 审计：写入 operation_logs 表
  4. 汇总：更新 jobs 表的汇总数据
  5. 进度发布：发布任务进度到Redis，供WebSocket实时推送

职责：
1. 调度：按顺序/并行调用各 Agent
2. 状态管理：更新 jobs 表的状态和进度
3. 审计：写入 operation_logs 表
4. 汇总：更新 jobs 表的汇总数据
5. 进度发布：发布任务进度到Redis，供WebSocket实时推送

注意：
- 测试开发阶段使用 PricingAgentHTTP（直接调用 HTTP API）
- 生产环境使用 PricingAgent（MCP 模式）
"""
```

---

### 7. `pricing_agent.py` ⭐ 重点

**对比结果：**
- mold_cost-main: ✅ 完整的价格计算流程，支持并发、分批处理、进度发布
- mold_cost_: ❌ 简化版，功能不完整

**合并策略：** 使用 mold_cost-main 版本

**合并后头信息：**
```python
"""
PricingAgent - 价格计算Agent
负责人：人员E
版本：v2.0

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/pricing_agent.py
- 合并策略：使用 mold_cost-main 版本（功能更完整）
- 主要功能：
  1. 并发调用 price-search-mcp 检索所有数据
  2. 合并搜索结果
  3. 并发调用 price-search-mcp 计算所有费用
  4. 汇总总成本
  5. 支持分批处理（避免大量子图时连接池耗尽）

职责：
1. 并发调用 price-search-mcp 检索所有数据
2. 合并搜索结果
3. 并发调用 price-search-mcp 计算所有费用
4. 汇总总成本

设计原则：
- Agent 层面实现并发（asyncio.gather）
- 支持分批处理（避免大量子图时连接池耗尽）
- MCP 服务只负责单一工具执行
- 支持部分失败的优雅降级
"""
```

---

### mold_cost_ 独有文件（保留，添加头信息）

所有独有文件保持不变，但需要添加合并头信息：

```python
"""
[文件名] - [功能描述]
负责人：[负责人]
版本：[版本号]

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost_/agents/[文件名]
- 合并策略：保留原文件（mold_cost-main 无此文件）
- 说明：此文件为 mold_cost_ 独有功能

[原有的文档字符串内容]
"""
```

独有文件列表：
- ✅ `confirm_handler.py` - 确认处理器
- ✅ `data_view_builder.py` - 数据视图构建器
- ✅ `decision_agent.py` - 决策 Agent
- ✅ `intent_recognizer.py` - 意图识别器
- ✅ `intent_types.py` - 意图类型定义
- ✅ `message_persistence_manager.py` - 消息持久化管理器
- ✅ `nlp_parser.py` - 自然语言解析器
- ✅ `review_status.py` - 审核状态管理
- ✅ `action_handlers/` 目录 - 所有处理器


## 📝 合并执行清单

### 阶段 1：准备工作
- [x] 创建备份：`cp -r mold_cost_/agents mold_cost_/agents_backup` ✅ 2026-02-10 开始执行
- [x] 阅读本合并计划 ✅
- [x] 确认所有文件对比结果 ✅

### 阶段 2：复制和替换文件

#### 2.1 直接替换（mold_cost-main 版本更好）
```bash
# 1. __init__.py ✅ 已完成 2026-02-10
cp mold_cost-main/agents/__init__.py mold_cost_/agents/__init__.py

# 2. base_agent.py（需要手动修改添加时区支持） ✅ 已完成 2026-02-10
cp mold_cost-main/agents/base_agent.py mold_cost_/agents/base_agent.py

# 3. cad_agent.py ✅ 已完成 2026-02-10
cp mold_cost-main/agents/cad_agent.py mold_cost_/agents/cad_agent.py

# 4. nc_time_agent.py ✅ 已完成 2026-02-10
cp mold_cost-main/agents/nc_time_agent.py mold_cost_/agents/nc_time_agent.py

# 5. orchestrator_agent.py ✅ 已完成 2026-02-10
cp mold_cost-main/agents/orchestrator_agent.py mold_cost_/agents/orchestrator_agent.py

# 6. pricing_agent.py ✅ 已完成 2026-02-10
cp mold_cost-main/agents/pricing_agent.py mold_cost_/agents/pricing_agent.py
```

#### 2.2 保留不变（mold_cost_ 版本更好）
- ✅ `interaction_agent.py` - 保持不变
- ✅ 所有独有文件 - 保持不变

### 阶段 3：手动修改文件

#### 3.1 修改 `base_agent.py` 添加时区支持

**位置 1：导入部分**
```python
# 在文件顶部添加
from shared.timezone_utils import now_shanghai
```

**位置 2：OpResult.__init__ 方法**
```python
# 修改前（第 60 行左右）
self.timestamp = datetime.utcnow()

# 修改后
self.timestamp = now_shanghai()
```

**位置 3：OpResult.__init__ 方法（started_at 和 completed_at）**
```python
# 修改前（第 67-68 行左右）
self.started_at = started_at or datetime.utcnow()
self.completed_at = completed_at or datetime.utcnow()

# 修改后
self.started_at = started_at or now_shanghai()
self.completed_at = completed_at or now_shanghai()
```

**位置 4：BaseAgent.build_error_result 方法**
```python
# 修改前（第 180 行左右）
completed_at=datetime.utcnow(),

# 修改后
completed_at=now_shanghai(),
```

**位置 5：BaseAgent._log_operation 方法**
```python
# 修改前（第 240 行左右）
created_at=datetime.utcnow()

# 修改后
created_at=now_shanghai()
```

### 阶段 4：添加合并头信息

为每个文件添加合并头信息（参考上面的标准格式）：

#### 4.1 需要添加头信息的文件
- [ ] `__init__.py`
- [ ] `base_agent.py`
- [ ] `cad_agent.py`
- [ ] `interaction_agent.py`
- [ ] `nc_time_agent.py`
- [ ] `orchestrator_agent.py`
- [ ] `pricing_agent.py`
- [ ] `confirm_handler.py`
- [ ] `data_view_builder.py`
- [ ] `decision_agent.py`
- [ ] `intent_recognizer.py`
- [ ] `intent_types.py`
- [ ] `message_persistence_manager.py`
- [ ] `nlp_parser.py`
- [ ] `review_status.py`
- [ ] `action_handlers/` 目录下所有文件

### 阶段 5：测试验证
- [ ] 检查导入是否正常：`python -c "from agents import *"`
- [ ] 运行单元测试：`pytest tests/test_*_agent.py`
- [ ] 检查语法错误：`python -m py_compile agents/*.py`

### 阶段 6：提交到 Git
```bash
git add mold_cost_/agents/
git commit -m "合并 agents 目录

- 使用 mold_cost-main 的增强版 base_agent.py（添加时区支持）
- 使用 mold_cost-main 的完整版 cad_agent.py
- 使用 mold_cost-main 的完整版 nc_time_agent.py
- 使用 mold_cost-main 的完整版 orchestrator_agent.py
- 使用 mold_cost-main 的完整版 pricing_agent.py
- 保留 mold_cost_ 的完整版 interaction_agent.py
- 保留 mold_cost_ 的所有独有文件
- 为所有文件添加合并头信息"
```

---

## ⚠️ 注意事项

### 1. base_agent.py 时区修改
- 必须手动修改 5 处使用 `datetime.utcnow()` 的地方
- 改为使用 `now_shanghai()`
- 确保导入 `from shared.timezone_utils import now_shanghai`

### 2. 依赖检查
- 确保 `shared.timezone_utils` 模块存在
- 确保 `shared.mcp_client` 模块存在
- 确保 `shared.progress_publisher` 模块存在

### 3. 测试重点
- 测试 base_agent.py 的时区功能
- 测试各 Agent 的初始化
- 测试 MCP 客户端连接

---

## 📊 合并统计

### 文件数量
- 共同文件：7 个
- mold_cost_ 独有：8 个文件 + 1 个目录
- 总计：15+ 个文件

### 合并策略分布
- 使用 mold_cost-main：6 个（__init__.py, base_agent.py, cad_agent.py, nc_time_agent.py, orchestrator_agent.py, pricing_agent.py）
- 保留 mold_cost_：9+ 个（interaction_agent.py + 所有独有文件）

### 预计工作量
- 文件复制：10 分钟
- 手动修改：20 分钟
- 添加头信息：30 分钟
- 测试验证：20 分钟
- **总计：约 1.5 小时**

---

**文档版本：** v2.0  
**创建时间：** 2026-02-10  
**最后更新：** 2026-02-10
