# 信号量控制的并发任务池模式详解

## 什么是信号量（Semaphore）？

### 生活中的类比

想象一个停车场：
- 停车场有 **3个车位**（信号量值 = 3）
- 当车位满了，新来的车必须**等待**
- 有车离开后，等待的车才能**进入**

```
停车场（Semaphore(3)）
┌─────────────────────────┐
│ 🚗 车位1（占用）         │
│ 🚗 车位2（占用）         │
│ 🚗 车位3（占用）         │
└─────────────────────────┘
    ↓ 等待区
  🚗 🚗 🚗 （排队等待）
```

### 编程中的信号量

```python
import asyncio

# 创建信号量：最多允许3个任务同时执行
semaphore = asyncio.Semaphore(3)

async def task(task_id):
    # 尝试获取信号量（进入停车场）
    async with semaphore:
        print(f"任务 {task_id} 开始执行")
        await asyncio.sleep(2)  # 模拟工作
        print(f"任务 {task_id} 完成")
    # 自动释放信号量（离开停车场）

# 创建10个任务
tasks = [task(i) for i in range(10)]
await asyncio.gather(*tasks)
```

**执行过程：**
```
时间 0s:  任务0、1、2 开始（获得信号量）
时间 0s:  任务3-9 等待（信号量已满）
时间 2s:  任务0、1、2 完成（释放信号量）
时间 2s:  任务3、4、5 开始（获得信号量）
时间 2s:  任务6-9 继续等待
时间 4s:  任务3、4、5 完成
时间 4s:  任务6、7、8 开始
...
```

## 我们的实现原理

### 核心代码解析

```python
async def consume(
    self,
    queue_name: str,
    callback: Callable,
    max_concurrent: int = 1
):
    # 1. 创建信号量（控制并发数）
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 2. 创建任务集合（追踪正在执行的任务）
    tasks = set()
    
    # 3. 定义消息处理函数
    async def process_message(message):
        async with semaphore:  # 获取信号量
            # 处理消息
            data = json.loads(message.body.decode())
            await message.ack()
            await callback(data)
        # 自动释放信号量
    
    # 4. 消费消息循环
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            # 创建异步任务（不等待完成）
            task = asyncio.create_task(process_message(message))
            tasks.add(task)
            
            # 任务完成后自动从集合中移除
            task.add_done_callback(tasks.discard)
            
            # 如果达到最大并发数，等待至少一个任务完成
            if len(tasks) >= max_concurrent:
                done, pending = await asyncio.wait(
                    tasks, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                tasks = pending
```

### 详细执行流程

假设 `max_concurrent=3`，有10条消息：

```
步骤1: 收到消息1
  - 创建 task1
  - tasks = {task1}
  - len(tasks) = 1 < 3，继续

步骤2: 收到消息2
  - 创建 task2
  - tasks = {task1, task2}
  - len(tasks) = 2 < 3，继续

步骤3: 收到消息3
  - 创建 task3
  - tasks = {task1, task2, task3}
  - len(tasks) = 3 >= 3，等待！

步骤4: task1 完成
  - task1.add_done_callback 触发
  - tasks = {task2, task3}
  - 等待结束，继续

步骤5: 收到消息4
  - 创建 task4
  - tasks = {task2, task3, task4}
  - len(tasks) = 3 >= 3，等待！

步骤6: task2 完成
  - tasks = {task3, task4}
  - 等待结束，继续

...以此类推
```

### 可视化时间线

```
时间轴 →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

消息1: ████████████ (task1 执行)
消息2:   ████████████████ (task2 执行)
消息3:     ████████████ (task3 执行)
消息4:               ████████████ (task4 执行，等task1完成后开始)
消息5:                   ████████████████ (task5 执行，等task2完成后开始)
消息6:                       ████████████ (task6 执行，等task3完成后开始)
...

并发数始终 ≤ 3
```

## 关键技术点

### 1. asyncio.Semaphore

```python
semaphore = asyncio.Semaphore(3)

# 方式1: 使用 async with（推荐）
async with semaphore:
    # 自动获取和释放
    await do_work()

# 方式2: 手动控制
await semaphore.acquire()  # 获取
try:
    await do_work()
finally:
    semaphore.release()  # 释放
```

**内部实现原理：**
```python
class Semaphore:
    def __init__(self, value):
        self._value = value  # 可用资源数
        self._waiters = []   # 等待队列
    
    async def acquire(self):
        while self._value <= 0:
            # 没有可用资源，加入等待队列
            await self._wait()
        self._value -= 1  # 获取资源
    
    def release(self):
        self._value += 1  # 释放资源
        # 唤醒一个等待的协程
        if self._waiters:
            self._waiters.pop(0).set_result(None)
```

### 2. asyncio.create_task

```python
# 创建任务（立即返回，不等待完成）
task = asyncio.create_task(process_message(message))

# 等价于
task = asyncio.ensure_future(process_message(message))
```

**作用：**
- 将协程包装成 Task 对象
- 立即开始执行（在事件循环中调度）
- 不阻塞当前代码继续执行

### 3. Task 集合管理

```python
tasks = set()

# 添加任务
task = asyncio.create_task(work())
tasks.add(task)

# 任务完成后自动移除
task.add_done_callback(tasks.discard)

# 等价于
def remove_task(t):
    tasks.discard(t)
task.add_done_callback(remove_task)
```

### 4. asyncio.wait

```python
done, pending = await asyncio.wait(
    tasks,
    return_when=asyncio.FIRST_COMPLETED
)
```

**参数说明：**
- `tasks`: 任务集合
- `return_when`: 返回条件
  - `FIRST_COMPLETED`: 任意一个完成就返回
  - `FIRST_EXCEPTION`: 任意一个异常就返回
  - `ALL_COMPLETED`: 全部完成才返回

**返回值：**
- `done`: 已完成的任务集合
- `pending`: 未完成的任务集合

## 与其他并发模式对比

### 1. 串行处理（无并发）

```python
for message in messages:
    await process(message)  # 一个接一个
```

**特点：**
- ✅ 简单
- ✅ 资源占用少
- ❌ 效率低

### 2. 无限制并发

```python
tasks = [asyncio.create_task(process(msg)) for msg in messages]
await asyncio.gather(*tasks)
```

**特点：**
- ✅ 效率高
- ❌ 可能耗尽资源（内存、连接池）
- ❌ 难以控制

### 3. 信号量控制（我们的方案）

```python
semaphore = asyncio.Semaphore(3)
async def process_with_limit(msg):
    async with semaphore:
        await process(msg)

tasks = [asyncio.create_task(process_with_limit(msg)) for msg in messages]
await asyncio.gather(*tasks)
```

**特点：**
- ✅ 效率高（充分利用资源）
- ✅ 资源可控（不会耗尽）
- ✅ 灵活（可调整并发数）

### 4. 线程池/进程池

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(process, msg) for msg in messages]
    results = [f.result() for f in futures]
```

**特点：**
- ✅ 适合 CPU 密集型任务
- ❌ 线程/进程开销大
- ❌ 不适合 IO 密集型任务

## 性能分析

### 场景：处理10个任务，每个耗时10秒

#### 串行处理（max_concurrent=1）
```
总耗时 = 10 × 10秒 = 100秒
吞吐量 = 10任务 / 100秒 = 0.1任务/秒
```

#### 并发3（max_concurrent=3）
```
批次1: 任务1-3（0-10秒）
批次2: 任务4-6（10-20秒）
批次3: 任务7-9（20-30秒）
批次4: 任务10（30-40秒）

总耗时 = 40秒
吞吐量 = 10任务 / 40秒 = 0.25任务/秒
提升 = 2.5倍
```

#### 并发10（max_concurrent=10）
```
所有任务同时执行（0-10秒）

总耗时 = 10秒
吞吐量 = 10任务 / 10秒 = 1任务/秒
提升 = 10倍

但是：可能耗尽资源！
```

## 实际应用建议

### 1. 如何选择并发数？

**IO 密集型任务（网络请求、数据库查询）：**
```python
max_concurrent = CPU核心数 × 2
# 例如：4核CPU → 并发8
```

**CPU 密集型任务（计算、图像处理）：**
```python
max_concurrent = CPU核心数
# 例如：4核CPU → 并发4
```

**混合型任务：**
```python
max_concurrent = CPU核心数 × 1.5
# 例如：4核CPU → 并发6
```

**资源受限（数据库连接池）：**
```python
max_concurrent = 连接池大小 × 0.8
# 例如：连接池20 → 并发16（留余量）
```

### 2. 监控和调优

```python
import time

start_time = time.time()
completed_count = 0

async def process_with_metrics(message):
    global completed_count
    async with semaphore:
        await process(message)
        completed_count += 1
        
        # 计算吞吐量
        elapsed = time.time() - start_time
        throughput = completed_count / elapsed
        print(f"吞吐量: {throughput:.2f} 任务/秒")
```

### 3. 动态调整并发数

```python
class AdaptiveSemaphore:
    def __init__(self, initial_value, min_value, max_value):
        self.semaphore = asyncio.Semaphore(initial_value)
        self.current_value = initial_value
        self.min_value = min_value
        self.max_value = max_value
    
    def increase(self):
        if self.current_value < self.max_value:
            self.current_value += 1
            self.semaphore.release()
    
    def decrease(self):
        if self.current_value > self.min_value:
            self.current_value -= 1
            # 注意：减少需要等待一个任务完成
```

## 常见问题

### Q1: 为什么不用线程池？

**A:** 
- 你的任务是 IO 密集型（数据库、网络请求）
- asyncio 更轻量（协程 vs 线程）
- 避免 GIL 限制
- 更好的资源利用率

### Q2: 信号量会阻塞事件循环吗？

**A:** 
- 不会！`await semaphore.acquire()` 是异步等待
- 释放事件循环给其他协程
- 不会阻塞整个程序

### Q3: 如何处理任务失败？

**A:**
```python
async def process_message(message):
    async with semaphore:
        try:
            await callback(data)
            await message.ack()
        except Exception as e:
            logger.error(f"任务失败: {e}")
            await message.reject(requeue=True)
```

### Q4: 可以动态改变并发数吗？

**A:** 
- 可以，但需要小心
- 增加：调用 `semaphore.release()`
- 减少：需要等待任务完成
- 建议：重启 worker 更安全

## 总结

**信号量控制的并发任务池模式 = 停车场管理**

1. **信号量** = 停车位数量（控制并发）
2. **任务集合** = 停车场内的车（追踪状态）
3. **等待机制** = 排队等待（资源不足时）
4. **自动清理** = 车离开后释放车位（任务完成后释放资源）

**优势：**
- 🚀 提高吞吐量（充分利用资源）
- 🛡️ 保护系统（避免资源耗尽）
- 🎛️ 灵活可控（可调整并发数）
- 📊 易于监控（任务数量可见）

**适用场景：**
- ✅ IO 密集型任务
- ✅ 需要控制资源使用
- ✅ 任务之间相对独立
- ✅ 需要高吞吐量

你们的项目完美符合这个模式！
