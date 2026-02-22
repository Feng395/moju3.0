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

## 📚 相关文档

- [Workers 文档](../workers/README.md)
- [Shared 模块文档](../shared/README.md)
- [主项目文档](../README.md)
