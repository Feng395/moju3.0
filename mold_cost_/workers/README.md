# Workers 模块

## 📋 概述

Workers 模块包含系统的后台任务处理器，负责从消息队列中消费任务并异步处理。Workers 与 API Gateway 解耦，可以独立部署和扩展。

## 📁 目录结构

```
workers/
├── orchestrator_worker.py          # 编排Worker（主要）
├── pricing_recalculate_worker.py   # 价格重算Worker
├── all_tasks_worker.py             # 全任务Worker
└── __init__.py
```

## 🤖 核心 Workers

### 1. OrchestratorWorker (编排Worker)

**职责**: 处理主要的任务编排和流程控制

**功能**:
- 监听任务队列
- 调用 OrchestratorAgent 处理任务
- 发布任务进度
- 处理任务异常

**队列监听**:
- `job_processing` - 任务处理队列
- `cad_parsing` - CAD解析队列
- `feature_recognition` - 特征识别队列

**启动方式**:
```bash
# 直接启动
python workers/orchestrator_worker.py

# 使用统一启动脚本
python main.py  # 默认包含 Worker
```

**工作流程**:
```
1. 从 RabbitMQ 接收任务消息
   ↓
2. 解析任务参数
   ↓
3. 调用 OrchestratorAgent
   ↓
4. 发布进度到 WebSocket/Redis
   ↓
5. 处理结果或异常
   ↓
6. 确认消息消费
```

**代码示例**:
```python
from workers.orchestrator_worker import OrchestratorWorker

worker = OrchestratorWorker()
await worker.start()
```

### 2. PricingRecalculateWorker (价格重算Worker)

**职责**: 处理价格重新计算任务

**功能**:
- 监听价格重算队列
- 批量重算价格
- 更新数据库
- 发送通知

**队列监听**:
- `price_recalculation` - 价格重算队列

**触发场景**:
- 价格规则更新
- 材料价格变动
- 工艺参数调整
- 手动触发重算

**启动方式**:
```bash
python workers/pricing_recalculate_worker.py
```

**工作流程**:
```
1. 接收重算任务
   ↓
2. 获取相关任务列表
   ↓
3. 批量重新计算价格
   ↓
4. 更新数据库
   ↓
5. 发送完成通知
```

**代码示例**:
```python
from workers.pricing_recalculate_worker import PricingRecalculateWorker

worker = PricingRecalculateWorker()
await worker.start()
```

### 3. AllTasksWorker (全任务Worker)

**职责**: 处理所有类型的后台任务

**功能**:
- 监听多个队列
- 路由到对应的处理器
- 统一的错误处理
- 任务重试机制

**队列监听**:
- `job_processing` - 任务处理
- `cad_parsing` - CAD解析
- `feature_recognition` - 特征识别
- `price_calculation` - 价格计算
- `report_generation` - 报表生成
- `notification` - 通知发送

**启动方式**:
```bash
python workers/all_tasks_worker.py
```

**工作流程**:
```
1. 监听多个队列
   ↓
2. 识别任务类型
   ↓
3. 路由到对应处理器
   ↓
4. 执行任务
   ↓
5. 处理结果
   ↓
6. 重试或确认
```

## 🔄 消息队列集成

### RabbitMQ 配置

```python
# 连接配置
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "admin"
RABBITMQ_PASSWORD = "Admin@123"

# 队列配置
QUEUES = {
    "job_processing": {
        "durable": True,
        "auto_delete": False,
        "prefetch_count": 1
    },
    "price_recalculation": {
        "durable": True,
        "auto_delete": False,
        "prefetch_count": 5
    }
}
```

### 消息格式

```python
# 任务处理消息
{
    "job_id": "uuid",
    "action": "process",
    "parameters": {
        "file_path": "path/to/file.dwg",
        "user_id": "uuid"
    },
    "priority": 1,
    "timestamp": "2026-02-22T10:00:00Z"
}

# 价格重算消息
{
    "recalculation_id": "uuid",
    "job_ids": ["uuid1", "uuid2"],
    "reason": "price_rule_updated",
    "timestamp": "2026-02-22T10:00:00Z"
}
```

## 📊 进度发布

### WebSocket 推送

```python
from shared.progress_publisher import ProgressPublisher

publisher = ProgressPublisher()

# 发布进度
await publisher.publish_progress(
    job_id="job-123",
    stage="cad_parsing",
    progress=50,
    message="正在解析CAD文件..."
)
```

### Redis 缓存

```python
from api_gateway.utils.redis_client import redis_client

# 缓存任务状态
await redis_client.set(
    f"job_status:{job_id}",
    json.dumps({
        "status": "processing",
        "progress": 50,
        "stage": "cad_parsing"
    }),
    expire=3600
)
```

## 🔧 错误处理

### 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def process_task(task_data):
    # 处理任务
    pass
```

### 死信队列

```python
# 配置死信队列
DEAD_LETTER_QUEUE = "failed_tasks"

# 任务失败后发送到死信队列
await rabbitmq_client.publish(
    queue=DEAD_LETTER_QUEUE,
    message={
        "original_queue": "job_processing",
        "task_data": task_data,
        "error": str(error),
        "timestamp": datetime.now().isoformat()
    }
)
```

### 异常通知

```python
from shared.logging_config import get_logger

logger = get_logger(__name__)

try:
    await process_task(task_data)
except Exception as e:
    logger.error(f"Task processing failed: {e}", exc_info=True)
    # 发送通知
    await send_error_notification(task_data, error=e)
```

## 🚀 部署

### 单机部署

```bash
# 启动 Orchestrator Worker
python workers/orchestrator_worker.py &

# 启动 Pricing Worker
python workers/pricing_recalculate_worker.py &

# 启动 All Tasks Worker
python workers/all_tasks_worker.py &
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "workers/orchestrator_worker.py"]
```

```yaml
# docker-compose.yml
services:
  orchestrator_worker:
    build: .
    command: python workers/orchestrator_worker.py
    environment:
      - RABBITMQ_HOST=rabbitmq
      - DB_HOST=postgres
    depends_on:
      - rabbitmq
      - postgres
    restart: always
```

### Systemd 服务

```ini
# /etc/systemd/system/mold-cost-worker.service
[Unit]
Description=Mold Cost Orchestrator Worker
After=network.target rabbitmq.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mold_cost
Environment="PATH=/opt/mold_cost/venv/bin"
ExecStart=/opt/mold_cost/venv/bin/python workers/orchestrator_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 多实例部署

```bash
# 启动多个 Worker 实例
for i in {1..4}; do
    python workers/orchestrator_worker.py --instance $i &
done
```

## 📈 性能优化

### 并发处理

```python
import asyncio

# 并发处理多个任务
async def process_multiple_tasks(tasks):
    results = await asyncio.gather(
        *[process_task(task) for task in tasks],
        return_exceptions=True
    )
    return results
```

### 批量处理

```python
# 批量处理价格重算
async def batch_recalculate(job_ids, batch_size=10):
    for i in range(0, len(job_ids), batch_size):
        batch = job_ids[i:i+batch_size]
        await process_batch(batch)
```

### 资源限制

```python
# 限制并发数
semaphore = asyncio.Semaphore(10)

async def process_with_limit(task):
    async with semaphore:
        return await process_task(task)
```

## 📊 监控

### 健康检查

```python
async def health_check():
    return {
        "status": "healthy",
        "queue_size": await get_queue_size(),
        "processing_tasks": len(active_tasks),
        "uptime": get_uptime()
    }
```

### 指标收集

```python
from prometheus_client import Counter, Histogram

# 任务计数器
tasks_processed = Counter('tasks_processed_total', 'Total tasks processed')
tasks_failed = Counter('tasks_failed_total', 'Total tasks failed')

# 处理时间
processing_time = Histogram('task_processing_seconds', 'Task processing time')

# 使用
tasks_processed.inc()
with processing_time.time():
    await process_task(task)
```

### 日志记录

```python
from shared.logging_config import get_logger

logger = get_logger(__name__)

logger.info(f"Processing task: {task_id}")
logger.error(f"Task failed: {task_id}", exc_info=True)
```

## 🧪 测试

### 单元测试

```bash
# 测试 Workers
pytest tests/workers/

# 测试特定 Worker
pytest tests/workers/test_orchestrator_worker.py
```

### 集成测试

```python
import pytest
from workers.orchestrator_worker import OrchestratorWorker

@pytest.mark.asyncio
async def test_worker_processing():
    worker = OrchestratorWorker()
    result = await worker.process_task({
        "job_id": "test-123",
        "action": "process"
    })
    assert result["success"] is True
```

## 📝 配置

### 环境变量

```bash
# RabbitMQ 配置
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=Admin@123

# Worker 配置
WORKER_CONCURRENCY=4
WORKER_PREFETCH_COUNT=1
WORKER_TIMEOUT=300

# 重试配置
MAX_RETRIES=3
RETRY_DELAY=5
```

### Worker 配置文件

```python
# worker_config.py
WORKER_CONFIG = {
    "orchestrator": {
        "queues": ["job_processing", "cad_parsing"],
        "concurrency": 4,
        "timeout": 300
    },
    "pricing": {
        "queues": ["price_recalculation"],
        "concurrency": 10,
        "timeout": 60
    }
}
```

## 📚 相关文档

- [Agents 文档](../agents/README.md)
- [API Gateway 文档](../api_gateway/README.md)
- [Shared 模块文档](../shared/README.md)
- [主项目文档](../README.md)

## 🤝 贡献指南

1. 遵循异步编程最佳实践
2. 实现完善的错误处理
3. 添加详细的日志记录
4. 编写单元测试
5. 更新相关文档

## 📞 联系方式

如有问题，请联系 Workers 团队或提交 Issue。
