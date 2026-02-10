# 进度发布功能使用指南

## 概述

进度发布功能允许编排器将任务执行进度实时发布到Redis Pub/Sub，供WebSocket服务订阅并推送给前端。

## 架构

```
RabbitMQ (job_id) 
    ↓
OrchestratorWorker
    ↓
OrchestratorAgent (发布进度)
    ↓
Redis Pub/Sub (job:{job_id}:progress)
    ↓
WebSocket → 前端
```

## 核心组件

### 1. ProgressPublisher (`shared/progress_publisher.py`)

进度发布器，负责将进度消息发布到Redis。

```python
from shared.progress_publisher import ProgressPublisher

# 创建发布器
publisher = ProgressPublisher()

# 发布进度
publisher.publish_progress(
    job_id="test_job_123",
    stage="cad_split_completed",
    progress=20,
    message="拆图完成，生成5个子图",
    details={"subgraph_count": 5}
)

# 关闭连接
publisher.close()
```

### 2. ProgressStage & ProgressPercent (`shared/progress_stages.py`)

进度阶段和百分比常量，避免硬编码字符串。

```python
from shared.progress_stages import ProgressStage, ProgressPercent

# 使用常量
stage = ProgressStage.CAD_SPLIT_COMPLETED
progress = ProgressPercent.CAD_SPLIT_COMPLETED
```

### 3. OrchestratorAgent (`agents/orchestrator_agent.py`)

编排器在每个阶段的开始和结束时发布进度。

```python
# 初始化时注入进度发布器
orchestrator = OrchestratorAgent(progress_publisher=publisher)

# 内部自动发布进度
await orchestrator.start(job_id)
```

## 进度阶段定义

| 阶段 | 常量 | 进度 | 说明 |
|------|------|------|------|
| 初始化 | `INITIALIZING` | 0% | 任务开始 |
| 拆图开始 | `CAD_SPLIT_STARTED` | 5% | 开始拆图 |
| 拆图完成 | `CAD_SPLIT_COMPLETED` | 20% | 拆图成功 |
| 拆图失败 | `CAD_SPLIT_FAILED` | 5% | 拆图失败 |
| 特征识别开始 | `FEATURE_RECOGNITION_STARTED` | 25% | 开始识别 |
| 特征识别完成 | `FEATURE_RECOGNITION_COMPLETED` | 50% | 识别成功 |
| 特征识别失败 | `FEATURE_RECOGNITION_FAILED` | 25% | 识别失败 |
| NC计算开始 | `NC_CALCULATION_STARTED` | 55% | 开始计算 |
| NC计算完成 | `NC_CALCULATION_COMPLETED` | 70% | 计算成功 |
| 价格计算开始 | `PRICING_STARTED` | 75% | 开始计算 |
| 价格计算完成 | `PRICING_COMPLETED` | 90% | 计算成功 |
| 任务完成 | `COMPLETED` | 100% | 全部完成 |
| 任务失败 | `FAILED` | 0% | 任务失败 |

## 消息格式

Redis频道：`job:{job_id}:progress`

消息体（JSON）：
```json
{
    "stage": "cad_split_completed",
    "progress": 20,
    "message": "拆图完成，生成5个子图",
    "timestamp": "2026-01-14T13:52:03.730523",
    "details": {
        "subgraph_count": 5
    }
}
```

### details 字段说明

不同阶段的 `details` 包含不同信息：

- **拆图完成**: `{"subgraph_count": 5}`
- **特征识别完成**: `{"success_count": 5, "failed_count": 0}`
- **价格计算完成**: `{"total_cost": 12345.67, "currency": "CNY"}`
- **任务完成**: `{"duration_ms": 15000}`
- **失败**: `{"error": "错误信息", "error_code": "ERROR_CODE"}`

## 使用流程

### 1. 配置环境变量

在 `.env` 文件中配置Redis连接：

```bash
REDIS_URL=redis://192.168.0.41:6379/0
```

### 2. 启动编排器Worker

```bash
python workers/orchestrator_worker.py
```

Worker会自动：
- 初始化 `ProgressPublisher`
- 将其注入到 `OrchestratorAgent`
- 在任务执行过程中自动发布进度

### 3. 监听进度（测试）

#### 方式1：使用测试脚本

```bash
# 订阅进度消息
python test_redis_subscribe.py test_job_123

# 发布测试消息
python test_progress_publisher.py
```

#### 方式2：使用WebSocket

在浏览器中打开WebSocket测试页面，输入job_id即可实时接收进度。

## 测试

### 测试1：完整流程

```bash
# 终端1：订阅进度
python test_redis_subscribe.py test_job_progress_123

# 终端2：发布测试消息
python test_progress_publisher.py
# 选择: 1 (完整流程)
```

### 测试2：错误流程

```bash
# 终端1：订阅进度
python test_redis_subscribe.py test_job_error_456

# 终端2：发布测试消息
python test_progress_publisher.py
# 选择: 2 (错误流程)
```

### 测试3：实际任务

```bash
# 终端1：订阅进度
python test_redis_subscribe.py <实际的job_id>

# 终端2：启动Worker并发送任务
python workers/orchestrator_worker.py
```

## 代码示例

### 在编排器中发布进度

```python
from shared.progress_publisher import ProgressPublisher
from shared.progress_stages import ProgressStage, ProgressPercent

class OrchestratorAgent:
    def __init__(self, progress_publisher=None):
        self.progress_publisher = progress_publisher or ProgressPublisher()
    
    async def start(self, job_id):
        # 初始化
        self._publish_progress(
            job_id,
            ProgressStage.INITIALIZING,
            ProgressPercent.INITIALIZING,
            "任务初始化..."
        )
        
        # 拆图开始
        self._publish_progress(
            job_id,
            ProgressStage.CAD_SPLIT_STARTED,
            ProgressPercent.CAD_SPLIT_STARTED,
            "正在拆图..."
        )
        
        # 调用CADAgent
        result = await self.cad_agent.split({"job_id": job_id})
        
        if result["status"] == "ok":
            # 拆图完成
            self._publish_progress(
                job_id,
                ProgressStage.CAD_SPLIT_COMPLETED,
                ProgressPercent.CAD_SPLIT_COMPLETED,
                f"拆图完成，生成{result['summary']['subgraph_count']}个子图",
                details=result['summary']
            )
        else:
            # 拆图失败
            self._publish_progress(
                job_id,
                ProgressStage.CAD_SPLIT_FAILED,
                ProgressPercent.CAD_SPLIT_STARTED,
                f"拆图失败: {result['message']}",
                details={"error": result['message']}
            )
    
    def _publish_progress(self, job_id, stage, progress, message, details=None):
        if self.progress_publisher:
            self.progress_publisher.publish_progress(
                job_id, stage, progress, message, details
            )
```

### 在其他Agent中使用（可选）

如果其他Agent也需要发布进度，可以注入 `ProgressPublisher`：

```python
class CADAgent:
    def __init__(self, progress_publisher=None):
        self.progress_publisher = progress_publisher
    
    async def split(self, context):
        job_id = context["job_id"]
        
        # 发布子阶段进度（可选）
        if self.progress_publisher:
            self.progress_publisher.publish_progress(
                job_id,
                "cad_split_processing",
                15,
                "拆图进行中，已处理50%"
            )
        
        # ... 执行拆图逻辑
```

## MCP集成（预留）

当前使用HTTP模式调用CAD服务，未来切换到MCP时：

1. **CADAgent保持不变** - 只需修改内部调用方式
2. **进度发布逻辑不变** - 编排器继续在调用前后发布进度
3. **MCP调用示例**:

```python
# 未来的MCP模式
async def split(self, context):
    job_id = context["job_id"]
    
    # 通过MCP调用拆图服务
    result = await self.mcp_client.call_tool(
        server_name="chaitu-mcp",
        tool_name="split_dwg",
        arguments={"job_id": job_id}
    )
    
    return result
```

## 故障排查

### 问题1：Redis连接失败

```
❌ Redis连接失败: Error 111 connecting to 192.168.0.41:6379. Connection refused.
```

**解决方案**:
1. 检查Redis服务是否启动
2. 检查 `.env` 中的 `REDIS_URL` 是否正确
3. 检查防火墙是否阻止6379端口
4. 测试网络: `ping 192.168.0.41`

### 问题2：没有收到进度消息

**检查清单**:
1. Redis连接是否成功
2. 订阅的频道名称是否正确（`job:{job_id}:progress`）
3. 编排器是否正确初始化了 `ProgressPublisher`
4. 查看编排器日志，确认是否调用了 `_publish_progress()`

### 问题3：进度消息格式错误

**检查**:
- 确保使用 `ProgressStage` 和 `ProgressPercent` 常量
- 检查 `details` 字段是否为有效的字典
- 查看Redis日志确认消息内容

## 性能考虑

- **Redis连接**: 使用连接池，避免频繁创建连接
- **消息频率**: 避免过于频繁发布（如每秒多次），建议关键节点发布
- **消息大小**: `details` 字段不要包含过大的数据（如完整文件内容）
- **订阅者数量**: Redis Pub/Sub支持多个订阅者，性能良好

## 扩展

### 添加新的进度阶段

1. 在 `shared/progress_stages.py` 中添加常量：

```python
class ProgressStage:
    # ... 现有常量
    NEW_STAGE_STARTED = "new_stage_started"
    NEW_STAGE_COMPLETED = "new_stage_completed"

class ProgressPercent:
    # ... 现有常量
    NEW_STAGE_STARTED = 80
    NEW_STAGE_COMPLETED = 85
```

2. 在编排器中使用：

```python
self._publish_progress(
    job_id,
    ProgressStage.NEW_STAGE_STARTED,
    ProgressPercent.NEW_STAGE_STARTED,
    "新阶段开始..."
)
```

### 添加更多details信息

根据需要在 `details` 中添加更多信息：

```python
details = {
    "subgraph_count": 5,
    "file_size_mb": 12.5,
    "processing_time_ms": 3000,
    "server_name": "cad-server-01"
}
```

## 总结

进度发布功能提供了：
- ✅ 实时进度更新
- ✅ 统一的消息格式
- ✅ 易于扩展的架构
- ✅ 完善的错误处理
- ✅ MCP集成预留

通过Redis Pub/Sub，前端可以实时接收任务进度，提升用户体验。
