# Consumers 消费者模块

## 📋 概述

Consumers 模块包含 RabbitMQ 消息队列的消费者，负责处理特定类型的异步任务。

## 📁 文件结构

```
consumers/
├── review_consumer.py    # 审核消费者
└── __init__.py
```

## 🔄 消费者说明

### ReviewConsumer (审核消费者)

**功能**: 处理审核相关的异步任务

**监听队列**: `review_queue`

**处理任务**:
- 审核提交通知
- 审核结果处理
- 审核状态更新
- 审核消息推送

**启动方式**:
```bash
python consumers/review_consumer.py
```

**工作流程**:
```
1. 监听审核队列
   ↓
2. 接收审核消息
   ↓
3. 处理审核逻辑
   ↓
4. 更新数据库
   ↓
5. 发送通知
   ↓
6. 确认消息
```

## 🚀 使用方法

### 启动消费者

```bash
# 启动审核消费者
python consumers/review_consumer.py
```

### 发送消息到队列

```python
from shared.message_queue import MessageQueue

mq = MessageQueue()

# 发送审核消息
await mq.publish(
    queue="review_queue",
    message={
        "job_id": "job-123",
        "action": "submit_review",
        "reviewer_id": "user-456"
    }
)
```

## 📝 配置

### 环境变量

```bash
# RabbitMQ 配置
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=Admin@123

# 消费者配置
CONSUMER_PREFETCH_COUNT=1
CONSUMER_TIMEOUT=300
```

## 项目中 RabbitMQ 消息队列的使用

### 1. 核心组件

**RabbitMQ 客户端封装**

- `mold_cost_/api_gateway/utils/rabbitmq_client.py` - API Gateway 专用客户端
- `mold_cost_/shared/message_queue.py` - 通用消息队列封装

### 2. 队列定义

项目中使用了以下队列：

| 队列名称              | 用途                                   | 消费者                     |
| --------------------- | -------------------------------------- | -------------------------- |
| `job_processing`      | 新任务处理（拆图、特征识别、价格计算） | orchestrator_worker        |
| `pricing_recalculate` | 价格重算（用户修改参数后）             | pricing_recalculate_worker |
| `review_queue`        | 审核系统消息                           | review_consumer            |
| `job_processing_dlx`  | 死信队列（处理失败的消息）             | -                          |

### 3. 消息生产者（发布消息）

**任务创建**

- `api_gateway/services/job_service.py` - 创建新任务时发布到 `job_processing` 队列

**价格重算**

- `api_gateway/routers/pricing.py` - 用户修改参数后发布到 `pricing_recalculate` 队列
- `api_gateway/routers/recalculations.py` - 批量重算时发布消息

**审核系统**

- 发布到 `review_queue` 队列触发审核流程

### 4. 消息消费者（处理消息）

**Worker 进程**

- `workers/orchestrator_worker.py` - 消费 `job_processing` 队列，处理新任务
- `workers/pricing_recalculate_worker.py` - 消费 `pricing_recalculate` 队列，处理价格重算
- `workers/all_tasks_worker.py` - 统一 Worker，同时处理多个队列
- `consumers/review_consumer.py` - 消费 `review_queue` 队列，处理审核消息

### 5. 关键特性

**连接管理**

- 使用 `aio_pika.connect_robust()` 实现自动重连
- 心跳机制（60秒）保持连接活跃
- QoS 设置（prefetch_count）控制并发

**消息持久化**

- 队列持久化（`durable=True`）
- 消息持久化（`DeliveryMode.PERSISTENT`）
- 消息 TTL 配置（24小时或1小时）

**死信队列机制**

- 配置死信交换机和死信队列
- 处理失败的消息自动转移到死信队列
- 支持消息重试策略

**并发控制**

- 支持串行和并发处理模式
- 可配置最大并发数（环境变量）
- 信号量控制并发任务数

**消息确认策略**

- `early_ack=False`（标准模式）：处理完成后 ACK，保证消息不丢失
- `early_ack=True`（尽早 ACK 模式）：拉取后立即 ACK，避免 Consumer Timeout

### 6. 配置项

在 `.env` 文件中配置：

```bash
# RabbitMQ配置
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=Admin@123
RABBITMQ_QUEUE_JOB_PROCESSING=job_processing
RABBITMQ_QUEUE_DLX=job_processing_dlx

# 队列并发配置
JOB_PROCESSING_CONCURRENCY=1
PRICING_RECALCULATE_CONCURRENCY=3
```

### 7. 典型使用流程

**发布消息示例**：

```python
await rabbitmq_client.publish_job_message(
    job_id=job_id,
    user_id=user_id
)
```

**消费消息示例**：

```python
await mq.consume(
    queue_name=QUEUE_JOB_PROCESSING,
    callback=self.handle_message,
    early_ack=True,
    max_concurrent=1
)
```

项目使用 RabbitMQ 实现了完整的异步任务处理架构，支持任务编排、价格计算、审核流程等多种业务场景。

## 📚 相关文档

- [Workers 文档](../workers/README.md)
- [Shared 模块文档](../shared/README.md)
- [主项目文档](../README.md)
