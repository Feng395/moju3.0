# 队列并发配置说明

## 概述
系统使用**信号量控制的并发任务池模式**来处理消息队列，可以针对不同队列设置不同的并发数。

## 并发策略

### 1. job_processing 队列（任务编排）
**并发数：1（串行处理）**

**原因：**
- 任务包含多个阶段（拆图 → 特征识别 → NC计算 → 价格计算）
- 阶段之间有依赖关系
- 避免同一任务的多个阶段冲突
- 每个任务耗时较长（几分钟到几十分钟）

**配置位置：**
```python
# workers/all_tasks_worker.py
async def _consume_job_processing_queue(self):
    await self.mq.consume(
        queue_name=QUEUE_JOB_PROCESSING,
        callback=self.handle_job_processing_message,
        early_ack=True,
        max_concurrent=1  # 串行处理
    )
```

### 2. pricing_recalculate 队列（价格重算）
**并发数：3（并发处理）**

**原因：**
- 任务之间完全独立
- 每个任务耗时中等（几秒到几分钟）
- 可以充分利用数据库连接池和CPU资源
- 提高价格重算的吞吐量

**配置位置：**
```python
# workers/all_tasks_worker.py
async def _consume_pricing_queue(self):
    await self.mq.consume(
        queue_name=QUEUE_PRICING_RECALCULATE,
        callback=self.handle_pricing_message,
        early_ack=True,
        max_concurrent=3  # 并发3个任务
    )
```

## 技术实现

### 信号量控制
使用 `asyncio.Semaphore` 控制并发数：
```python
semaphore = asyncio.Semaphore(max_concurrent)

async def process_message(message):
    async with semaphore:  # 获取信号量
        # 处理消息
        await callback(data)
    # 自动释放信号量
```

### 任务池管理
```python
tasks = set()  # 存储正在执行的任务

# 创建任务
task = asyncio.create_task(process_message(message))
tasks.add(task)

# 任务完成后自动移除
task.add_done_callback(tasks.discard)

# 达到最大并发数时等待
if len(tasks) >= max_concurrent:
    done, pending = await asyncio.wait(
        tasks, 
        return_when=asyncio.FIRST_COMPLETED
    )
    tasks = pending
```

## RabbitMQ 配置

### prefetch_count
```python
# shared/message_queue.py
await self.channel.set_qos(prefetch_count=10)
```

**说明：**
- 设置为 10，支持多个队列的并发消费
- 实际并发数由 `consume()` 方法的 `max_concurrent` 参数控制
- prefetch_count 应该 >= 所有队列的 max_concurrent 之和

**计算：**
- job_processing: max_concurrent=1
- pricing_recalculate: max_concurrent=3
- 总计：1 + 3 = 4
- 设置为 10 留有余量

## 调优建议

### 1. 根据资源调整并发数

**数据库连接池：**
```python
# 如果数据库连接池大小为 20
# 建议并发数不超过 15（留5个给API请求）
max_concurrent = min(15, cpu_count * 2)
```

**CPU密集型任务：**
```python
import os
max_concurrent = os.cpu_count()  # 等于CPU核心数
```

**IO密集型任务：**
```python
import os
max_concurrent = os.cpu_count() * 2  # 2倍CPU核心数
```

### 2. 监控指标

**关键指标：**
- 队列长度（积压消息数）
- 消息处理时间（平均、P95、P99）
- 任务成功率
- 数据库连接池使用率
- CPU和内存使用率

**调整策略：**
- 队列积压 → 增加并发数
- 数据库连接池耗尽 → 减少并发数
- CPU使用率过高 → 减少并发数
- 内存不足 → 减少并发数

### 3. 环境变量配置（可选）

可以将并发数配置到环境变量：
```python
# .env
JOB_PROCESSING_CONCURRENCY=1
PRICING_RECALCULATE_CONCURRENCY=3

# workers/all_tasks_worker.py
import os

job_concurrency = int(os.getenv("JOB_PROCESSING_CONCURRENCY", "1"))
pricing_concurrency = int(os.getenv("PRICING_RECALCULATE_CONCURRENCY", "3"))
```

## 注意事项

1. **early_ack=True**
   - 消息拉取后立即确认，避免 Consumer Timeout
   - 适合长时间任务
   - 需要在 callback 中自行处理错误和重试

2. **任务幂等性**
   - 确保任务可以安全重试
   - 使用数据库事务保证一致性
   - 记录任务状态避免重复执行

3. **资源限制**
   - 监控数据库连接池使用情况
   - 避免内存泄漏（及时释放大对象）
   - 控制外部API调用频率

4. **错误处理**
   - 捕获所有异常，避免任务池崩溃
   - 记录详细日志便于排查问题
   - 考虑使用死信队列处理失败消息

## 性能对比

### 串行处理（max_concurrent=1）
- 10个任务，每个耗时10秒
- 总耗时：100秒

### 并发处理（max_concurrent=3）
- 10个任务，每个耗时10秒
- 总耗时：约40秒（3个并发批次 + 1个任务）

### 提升比例
- 吞吐量提升：2.5倍
- 适合独立任务的批量处理
