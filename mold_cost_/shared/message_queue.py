"""
=== 文件合并信息 ===
合并日期: 2026-02-10
源文件: mold_cost-main/shared/message_queue.py (使用 mold_cost-main 版本)
合并策略: 使用 mold_cost-main 版本（功能更完整）
主要改动:
  1. 保留 mold_cost-main 的灵活配置方式
  2. 保留完整的队列配置（TTL、死信队列）
  3. 保留复杂的消息确认策略（early_ack、错误处理）
  4. 保留并发控制功能（max_concurrent）
  5. 保留心跳和 prefetch_count 配置
说明: RabbitMQ 消息队列封装，支持异步消息发布和消费
=====================

消息队列模块
负责人：人员B1
"""
import aio_pika
import json
from typing import Dict, Any, Callable
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 支持两种配置方式
# 方式1: 直接使用 RABBITMQ_URL
# 方式2: 使用分开的配置项
RABBITMQ_URL = os.getenv("RABBITMQ_URL")

if not RABBITMQ_URL:
    # 从分开的配置项构建 URL
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = os.getenv("RABBITMQ_PORT", "5672")
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_URL = f"amqp://{user}:{password}@{host}:{port}/"

print(f"[MessageQueue] 连接地址: amqp://{user}:***@{host}:{port}/")

class MessageQueue:
    """RabbitMQ消息队列封装"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """建立连接"""
        self.connection = await aio_pika.connect_robust(
            RABBITMQ_URL,
            heartbeat=60  # 每60秒发送心跳，保持连接活跃
        )
        self.channel = await self.connection.channel()
        # prefetch_count 设置为 10，支持多个队列的并发消费
        # 实际并发数由 consume() 方法的 max_concurrent 参数控制
        await self.channel.set_qos(prefetch_count=10)
    
    async def publish(self, queue_name: str, message: Dict[str, Any]):
        """发布消息"""
        # 如果未连接，先连接
        if self.channel is None:
            await self.connect()
        
        # 声明队列，匹配现有队列的完整配置
        queue = await self.channel.declare_queue(
            queue_name, 
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24小时 TTL
                "x-dead-letter-exchange": "job_processing_dlx_exchange",  # 死信交换机
                "x-dead-letter-routing-key": "job_processing_dlx"  # 死信路由键
            }
        )
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue_name
        )
    
    async def consume(
        self,
        queue_name: str,
        callback: Callable,
        early_ack: bool = False,
        max_concurrent: int = 1
    ):
        """
        消费消息（支持并发处理）
        
        Args:
            queue_name: 队列名称
            callback: 回调函数
            early_ack: 是否尽早 ACK（默认 False）
                - True: 拉取消息后立即 ACK，避免 Consumer Timeout
                - False: 处理完成后再 ACK，保证消息不丢失
            max_concurrent: 最大并发处理数（默认 1，即串行）
        
        消息确认策略（early_ack=False）：
        1. callback 返回 True 或无返回值 -> ACK（消息成功处理）
        2. callback 返回 False -> NACK + requeue=False（业务失败，不重试，移到死信队列）
        3. callback 抛出异常 -> NACK + requeue=True（系统异常，重新入队重试）
        
        消息确认策略（early_ack=True）：
        1. 拉取消息后立即 ACK
        2. 然后调用 callback 处理
        3. 处理失败不会重新入队（需要在 callback 中自行处理错误）
        """
        import asyncio
        
        # 声明队列，匹配现有队列的完整配置
        queue = await self.channel.declare_queue(
            queue_name, 
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24小时 TTL
                "x-dead-letter-exchange": "job_processing_dlx_exchange",  # 死信交换机
                "x-dead-letter-routing-key": "job_processing_dlx"  # 死信路由键
            }
        )
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 存储正在执行的任务
        tasks = set()
        
        async def process_message(message):
            """处理单条消息（带信号量控制）"""
            async with semaphore:
                if early_ack:
                    # 尽早 ACK 模式：先确认消息，再处理
                    try:
                        data = json.loads(message.body.decode())
                        
                        # 立即 ACK，避免 Consumer Timeout
                        await message.ack()
                        print(f"[MessageQueue] ✅ 消息已确认（尽早 ACK 模式）")
                        
                        # 然后处理消息（即使失败也不会重新入队）
                        try:
                            await callback(data)
                        except Exception as e:
                            # 处理失败，但消息已经 ACK 了，不会重新入队
                            print(f"[MessageQueue] ⚠️ 消息处理失败（已 ACK，不会重试）: {e}")
                            
                    except json.JSONDecodeError as e:
                        # JSON 解析失败，直接 ACK 并丢弃
                        print(f"[MessageQueue] JSON解析失败，消息已丢弃: {e}")
                        await message.ack()
                        
                    except Exception as e:
                        # 其他异常，尝试 ACK
                        print(f"[MessageQueue] 处理消息时发生异常: {e}")
                        try:
                            await message.ack()
                        except:
                            pass
                else:
                    # 标准模式：处理完成后再 ACK
                    try:
                        data = json.loads(message.body.decode())
                        
                        # 调用回调函数
                        result = await callback(data)
                        
                        # 根据返回值决定是否确认消息
                        if result is False:
                            # 业务逻辑失败，不重试，移到死信队列
                            await message.reject(requeue=False)
                        else:
                            # 成功处理，确认消息
                            await message.ack()
                            
                    except json.JSONDecodeError as e:
                        # JSON 解析失败，不重试
                        print(f"[MessageQueue] JSON解析失败，消息将被丢弃: {e}")
                        await message.reject(requeue=False)
                        
                    except Exception as e:
                        # 系统异常，重新入队重试
                        print(f"[MessageQueue] 处理消息时发生异常，消息将重新入队: {e}")
                        await message.reject(requeue=True)
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                # 创建任务并添加到任务集合
                task = asyncio.create_task(process_message(message))
                tasks.add(task)
                
                # 任务完成后从集合中移除
                task.add_done_callback(tasks.discard)
                
                # 如果达到最大并发数，等待至少一个任务完成
                if len(tasks) >= max_concurrent:
                    # 等待任意一个任务完成
                    done, pending = await asyncio.wait(
                        tasks, 
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    # 更新任务集合
                    tasks = pending
    
    async def close(self):
        """关闭连接"""
        if self.connection:
            await self.connection.close()

# 队列名称常量
QUEUE_JOB_PROCESSING = "job_processing"  # 任务处理队列（orchestrator_worker使用）
QUEUE_PRICING_RECALCULATE = "pricing_recalculate"  # 价格重算队列（pricing_recalculate_worker使用）
QUEUE_RECALCULATION = "recalculation_queue"  # 重算队列（保留兼容性）
QUEUE_DEAD_LETTER = "dead_letter_queue"
