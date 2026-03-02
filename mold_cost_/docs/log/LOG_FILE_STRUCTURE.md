# 日志文件结构说明

## 📁 日志文件分类

为了便于维护和问题排查，日志系统按功能模块划分为多个文件：

```
logs/
├── app.log              # 总日志（所有模块的日志）
├── error.log            # 错误日志（所有ERROR及以上级别）
├── api_gateway.log      # API Gateway 日志
├── workers.log          # Workers 日志
├── agents.log           # Agents 日志
├── mcp_services.log     # MCP 服务日志
├── scripts.log          # Scripts 日志
└── shared.log           # Shared 模块日志
```

---

## 📋 各日志文件说明

### 1. app.log - 总日志
**用途**：记录所有模块的日志，用于全局查看

**包含内容**：
- 所有模块的 INFO、WARNING、ERROR、CRITICAL 日志
- 系统启动、关闭信息
- 所有业务操作日志

**适用场景**：
- 查看系统整体运行情况
- 追踪跨模块的业务流程
- 全局搜索特定关键词

**示例**：
```
2026-03-02 10:30:45 - api_gateway.main - INFO - ✅ API Gateway 启动
2026-03-02 10:30:46 - workers.all_tasks_worker - INFO - ✅ Worker 启动
2026-03-02 10:30:47 - agents.cad_agent - INFO - 开始拆图: job_id=J001
```

---

### 2. error.log - 错误日志
**用途**：记录所有模块的错误和严重问题

**包含内容**：
- ERROR 级别日志
- CRITICAL 级别日志
- 异常堆栈信息

**适用场景**：
- 快速定位系统错误
- 监控系统健康状态
- 错误统计和分析

**示例**：
```
2026-03-02 10:35:20 - workers.all_tasks_worker - ERROR - 任务处理失败: job_id=J001
Traceback (most recent call last):
  File "workers/all_tasks_worker.py", line 120, in handle_message
    result = await self.process_job(job_data)
  ...
```

---

### 3. api_gateway.log - API Gateway 日志
**用途**：记录 API Gateway 相关的所有操作

**包含内容**：
- HTTP 请求和响应
- WebSocket 连接
- 路由处理
- 认证授权
- 文件上传下载
- 数据库操作

**适用场景**：
- 调试 API 接口问题
- 分析请求性能
- 追踪用户操作
- 排查认证问题

**示例**：
```
2026-03-02 10:30:50 - api_gateway.routers.jobs - INFO - 收到上传请求: user_id=U001
2026-03-02 10:30:51 - api_gateway.services.file_service - INFO - 文件上传成功: file_id=F001
2026-03-02 10:30:52 - api_gateway.routers.jobs - INFO - 任务创建成功: job_id=J001
```

**关键日志点**：
- 请求接收：`收到XXX请求`
- 参数验证：`参数验证通过/失败`
- 业务处理：`开始处理XXX`、`处理完成`
- 数据库操作：`查询XXX`、`更新XXX`
- 错误处理：`XXX失败`、异常信息

---

### 4. workers.log - Workers 日志
**用途**：记录后台任务处理的所有操作

**包含内容**：
- 任务队列消费
- 任务处理流程
- 任务状态变更
- 重试机制
- 性能指标

**适用场景**：
- 调试任务处理问题
- 监控任务队列状态
- 分析任务处理性能
- 排查任务失败原因

**示例**：
```
2026-03-02 10:31:00 - workers.all_tasks_worker - INFO - 开始处理任务: job_id=J001
2026-03-02 10:31:01 - workers.all_tasks_worker - INFO - 调用 OrchestratorAgent
2026-03-02 10:31:05 - workers.all_tasks_worker - INFO - 任务处理完成: job_id=J001, 耗时=5.2s
```

**关键日志点**：
- 队列监听：`开始监听队列`
- 消息接收：`收到消息: job_id=XXX`
- 任务处理：`开始处理`、`处理完成`、`处理失败`
- 性能指标：`耗时=XXs`
- 重试机制：`任务重试: 第X次`

---

### 5. agents.log - Agents 日志
**用途**：记录所有 Agent 的业务逻辑处理

**包含内容**：
- CADAgent：拆图、特征识别
- PricingAgent：价格计算
- InteractionAgent：用户交互
- OrchestratorAgent：任务编排
- 其他 Agents 的业务逻辑

**适用场景**：
- 调试业务逻辑问题
- 追踪数据处理流程
- 分析算法性能
- 排查计算错误

**示例**：
```
2026-03-02 10:31:10 - agents.cad_agent - INFO - 开始拆图: job_id=J001
2026-03-02 10:31:15 - agents.cad_agent - INFO - 拆图完成: 零件数=5
2026-03-02 10:31:16 - agents.pricing_agent - INFO - 开始价格计算: part_id=P001
2026-03-02 10:31:20 - agents.pricing_agent - INFO - 价格计算完成: total=1250.50
```

**关键日志点**：
- 任务开始：`开始XXX: job_id=XXX`
- 数据处理：`处理XXX数据`
- 算法执行：`执行XXX算法`
- 结果输出：`XXX完成: 结果=XXX`
- LLM 调用：`调用 LLM`、`LLM 响应`

---

### 6. mcp_services.log - MCP 服务日志
**用途**：记录 MCP 服务的所有操作

**包含内容**：
- MCP 服务启动
- 工具调用
- CAD 处理
- 价格搜索
- 数据库查询

**适用场景**：
- 调试 MCP 工具问题
- 监控服务健康状态
- 分析工具调用性能
- 排查数据查询问题

**示例**：
```
2026-03-02 10:32:00 - mcp_services.cad_price_search_mcp.server - INFO - MCP 服务启动: port=8200
2026-03-02 10:32:10 - mcp_services.cad_price_search_mcp.server - INFO - 调用工具: parse_dwg
2026-03-02 10:32:15 - mcp_services.cad_price_search_mcp.server - INFO - 工具执行完成: 耗时=5.1s
```

**关键日志点**：
- 服务启动：`MCP 服务启动`
- 工具调用：`调用工具: XXX`
- 参数解析：`解析参数`
- 执行过程：`执行XXX`
- 结果返回：`工具执行完成`

---

### 7. scripts.log - Scripts 日志
**用途**：记录各种脚本的执行情况

**包含内容**：
- 计算脚本（价格计算、NC时间等）
- 搜索脚本（材料搜索、工艺搜索等）
- 特征识别脚本
- 工具脚本

**适用场景**：
- 调试脚本执行问题
- 分析计算逻辑
- 排查数据查询问题
- 验证算法正确性

**示例**：
```
2026-03-02 10:33:00 - scripts.calculate.price_material - INFO - 开始材料价格计算
2026-03-02 10:33:01 - scripts.search.material_search - INFO - 查询材料: material_code=SKD11
2026-03-02 10:33:02 - scripts.calculate.price_material - INFO - 材料价格计算完成: price=125.50
```

**关键日志点**：
- 脚本启动：`开始XXX计算/搜索`
- 数据查询：`查询XXX`
- 计算过程：`计算XXX`
- 结果输出：`XXX完成: 结果=XXX`

---

### 8. shared.log - Shared 模块日志
**用途**：记录共享模块的操作

**包含内容**：
- 数据库连接池
- Redis 操作
- RabbitMQ 消息
- 工具函数
- 验证器

**适用场景**：
- 调试基础设施问题
- 监控资源使用
- 排查连接问题
- 分析性能瓶颈

**示例**：
```
2026-03-02 10:34:00 - shared.database - INFO - 数据库连接池初始化: size=10
2026-03-02 10:34:01 - shared.message_queue - INFO - RabbitMQ 连接成功
2026-03-02 10:34:02 - shared.validators.field_validator - INFO - 字段验证通过
```

---

## 🔍 日志查看技巧

### 1. 查看特定模块日志

```bash
# 查看 API Gateway 日志
tail -f logs/api_gateway.log

# 查看 Workers 日志
tail -f logs/workers.log

# 查看 Agents 日志
tail -f logs/agents.log
```

### 2. 查看错误日志

```bash
# 实时查看错误
tail -f logs/error.log

# 统计错误数量
grep -c "ERROR" logs/error.log

# 查看最近的错误
tail -n 50 logs/error.log
```

### 3. 搜索特定任务

```bash
# 在总日志中搜索
grep "job_id=J001" logs/app.log

# 在特定模块中搜索
grep "job_id=J001" logs/workers.log
grep "job_id=J001" logs/agents.log
```

### 4. 按时间查看

```bash
# 查看特定时间段
grep "2026-03-02 10:" logs/app.log

# 查看今天的日志
grep "$(date +%Y-%m-%d)" logs/app.log
```

### 5. 同时查看多个日志

```bash
# 同时查看 Workers 和 Agents
tail -f logs/workers.log logs/agents.log

# 同时查看所有错误
tail -f logs/error.log logs/api_gateway.log | grep ERROR
```

---

## 📊 日志分析

### 1. 统计各模块日志数量

```bash
# 统计各日志文件的行数
wc -l logs/*.log

# 统计各级别日志数量
for level in DEBUG INFO WARNING ERROR CRITICAL; do
    echo "$level: $(grep -c "$level" logs/app.log)"
done
```

### 2. 分析错误分布

```bash
# 统计各模块的错误数量
grep "ERROR" logs/app.log | cut -d'-' -f2 | sort | uniq -c | sort -rn

# 查看最常见的错误
grep "ERROR" logs/app.log | cut -d'-' -f4- | sort | uniq -c | sort -rn | head -10
```

### 3. 性能分析

```bash
# 查找耗时较长的操作
grep "耗时" logs/app.log | awk -F'耗时=' '{print $2}' | sort -rn | head -20

# 统计平均耗时
grep "耗时" logs/app.log | awk -F'耗时=' '{sum+=$2; count++} END {print sum/count}'
```

---

## ⚙️ 日志配置

### 环境变量

```bash
# 日志级别
LOG_LEVEL=INFO

# 日志目录
LOG_DIR=logs

# 启用模块分类日志
ENABLE_MODULE_LOGS=true
```

### 代码配置

```python
# API Gateway（使用 logging_config.py）
setup_logging(
    level="INFO",
    enable_console=True,
    enable_file=True,
    enable_module_logs=True  # 启用模块分类
)

# Workers（使用 unified_logging.py）
init_logging(
    level="INFO",
    enable_module_logs=True  # 启用模块分类
)
```

---

## 🎯 最佳实践

### 1. 日志级别使用

- **DEBUG**：详细的调试信息（开发环境）
- **INFO**：正常的业务流程（生产环境默认）
- **WARNING**：警告信息，不影响功能
- **ERROR**：错误信息，影响功能
- **CRITICAL**：严重错误，系统无法继续

### 2. 日志内容规范

```python
# ✅ 好的日志
logger.info(f"开始处理任务: job_id={job_id}, user_id={user_id}")
logger.info(f"任务处理完成: job_id={job_id}, 耗时={elapsed:.2f}s")
logger.error(f"任务处理失败: job_id={job_id}, 原因={error}", exc_info=True)

# ❌ 不好的日志
logger.info("开始处理")  # 缺少关键信息
logger.info(f"job_id: {job_id}")  # 格式不统一
logger.error("失败")  # 缺少错误详情
```

### 3. 关键业务节点必须记录

- 任务开始和结束
- 重要的状态变更
- 外部服务调用
- 数据库操作
- 错误和异常

### 4. 性能敏感操作记录耗时

```python
import time

start_time = time.time()
# 执行操作
elapsed = time.time() - start_time
logger.info(f"操作完成: 耗时={elapsed:.2f}s")
```

---

## 📝 日志轮转

所有日志文件都启用了自动轮转：

- **单文件最大**：10MB
- **保留备份**：7 个
- **命名规则**：`app.log.1`, `app.log.2`, ...

当日志文件达到 10MB 时，会自动创建新文件，旧文件重命名为 `.1`, `.2` 等。

---

## 🎉 总结

### 优势

1. **模块隔离**：每个模块的日志独立，互不干扰
2. **快速定位**：直接查看对应模块的日志文件
3. **便于监控**：可以针对不同模块设置不同的监控策略
4. **减少噪音**：不需要在海量日志中搜索
5. **保留总览**：app.log 仍然保留所有日志，用于全局查看

### 适用场景

- **开发调试**：查看特定模块的日志
- **问题排查**：快速定位问题所在模块
- **性能分析**：分析特定模块的性能
- **监控告警**：针对不同模块设置告警规则

---

**文档版本**: 1.0.0  
**更新日期**: 2026-03-02  
**维护人员**: 系统架构团队
