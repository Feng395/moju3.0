# 消息队列重试策略

## 当前策略：尽早 ACK 模式

为了避免长时间任务处理导致 RabbitMQ Consumer Timeout（默认 30 分钟），系统采用**尽早 ACK 模式**。

## 工作原理

### 标准模式 vs 尽早 ACK 模式

#### 标准模式（已弃用）
```
1. Worker 拉取消息（消息进入 Unacked 状态）
2. Worker 处理消息（可能需要 30+ 分钟）
3. 处理完成后发送 ACK
4. 消息从队列删除

风险：如果处理时间 > 30 分钟，RabbitMQ 会超时，消息重新入队
```

#### 尽早 ACK 模式（当前使用）✅
```
1. Worker 拉取消息
2. 立即发送 ACK（消息从队列删除）✅
3. Worker 处理消息（可以处理任意长时间）
4. 处理完成或失败

优点：不会因为处理时间长而导致消息重新入队
风险：如果处理失败，消息不会自动重试
```

## 配置

### 启用尽早 ACK 模式

```python
# workers/orchestrator_worker.py
await self.mq.consume(
    QUEUE_JOB_PROCESSING, 
    self.handle_message, 
    early_ack=True  # ✅ 启用尽早 ACK
)
```

### 禁用尽早 ACK 模式（不推荐）

```python
await self.mq.consume(
    QUEUE_JOB_PROCESSING, 
    self.handle_message, 
    early_ack=False  # 标准模式
)
```

## 幂等性保护

为了防止消息重复处理（例如手动重新发送消息），系统实现了幂等性检查：

### 检查逻辑

```python
# 在处理前检查任务状态
if job_status == "processing":
    # 任务正在处理中，跳过
    return

if job_status in ["completed", "awaiting_confirm"]:
    # 任务已完成或等待确认，跳过
    return

if job_status == "failed":
    # 任务之前失败，可以重新处理
    继续执行
```

### 保护的场景

1. **消息重复投递**：即使消息被重复发送，也不会重复执行
2. **手动重试**：可以手动重新发送失败的任务
3. **并发处理**：多个 Worker 不会同时处理同一个任务

## 错误处理

### 处理失败时的行为

由于使用尽早 ACK 模式，消息已经被确认，不会自动重试。系统会：

1. **记录错误日志**：详细记录异常信息
2. **更新数据库状态**：将任务状态设置为 `failed`
3. **记录错误消息**：在 `jobs.error_message` 字段中保存错误详情

### 手动重试失败任务

如果需要重试失败的任务：

```python
# 方式 1：通过 API 重新提交
POST /api/v1/jobs/{job_id}/retry

# 方式 2：手动发送消息到队列
await mq.publish(QUEUE_JOB_PROCESSING, {
    "job_id": "xxx",
    "user_id": "xxx"
})
```

## 监控建议

### 1. 监控失败任务

```sql
-- 查询失败的任务
SELECT job_id, error_message, updated_at
FROM jobs
WHERE status = 'failed'
ORDER BY updated_at DESC;
```

### 2. 监控处理时间

```sql
-- 查询处理时间超过 30 分钟的任务
SELECT job_id, 
       EXTRACT(EPOCH FROM (completed_at - created_at))/60 as duration_minutes
FROM jobs
WHERE status = 'completed'
  AND completed_at - created_at > INTERVAL '30 minutes'
ORDER BY duration_minutes DESC;
```

### 3. 监控队列长度

在 RabbitMQ 管理界面监控：
- Ready 消息数量：等待处理的任务
- Unacked 消息数量：应该始终为 0（尽早 ACK 模式）

## 优缺点对比

### 尽早 ACK 模式

**优点**：
- ✅ 不会因为处理时间长而超时
- ✅ 避免消息重复投递
- ✅ 简化了消息确认逻辑

**缺点**：
- ❌ 处理失败不会自动重试
- ❌ Worker 崩溃时可能丢失正在处理的任务
- ❌ 需要额外的错误处理和监控

### 标准模式

**优点**：
- ✅ 处理失败会自动重试
- ✅ Worker 崩溃时消息不会丢失

**缺点**：
- ❌ 长时间处理会导致超时
- ❌ 可能导致消息重复处理
- ❌ 需要配置 Consumer Timeout

## 最佳实践

1. **使用尽早 ACK 模式**：适合长时间任务（> 30 分钟）
2. **实现幂等性检查**：防止重复处理
3. **记录详细日志**：便于排查问题
4. **监控失败任务**：及时发现和处理失败
5. **定期清理**：清理长期失败的任务

## 故障恢复

### Worker 崩溃

```
1. Worker 拉取消息并立即 ACK
2. Worker 开始处理
3. Worker 崩溃 ❌
4. 消息已经 ACK，不会重新入队
5. 任务状态可能停留在 "processing"

恢复方案：
- 定期扫描长时间处于 "processing" 状态的任务
- 手动重新提交或标记为失败
```

### 数据库故障

```
1. Worker 拉取消息并立即 ACK
2. Worker 尝试更新数据库
3. 数据库连接失败 ❌
4. 消息已经 ACK，不会重新入队

恢复方案：
- 实现数据库重试机制
- 记录到本地日志文件
- 恢复后从日志重新处理
```

## 环境变量

```bash
# .env 文件

# 是否启用消息重试（尽早 ACK 模式下此选项无效）
ENABLE_MESSAGE_RETRY=false

# RabbitMQ 连接配置
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
```

## 相关文件

- `shared/message_queue.py`：消息队列封装，实现尽早 ACK 逻辑
- `workers/orchestrator_worker.py`：Worker 实现，包含幂等性检查
- `agents/orchestrator_agent.py`：编排器，负责任务执行
