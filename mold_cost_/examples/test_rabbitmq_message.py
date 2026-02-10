"""
RabbitMQ 消息发送测试脚本
负责人：人员B2

功能：
发送测试消息到 review_queue，测试 Consumer 是否正常工作

使用方法：
    python examples/test_rabbitmq_message.py
"""
import asyncio
import sys
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '.')

from api_gateway.utils.rabbitmq_client import rabbitmq_client


async def send_test_message(job_id: str = None):
    """
    发送测试消息到 review_queue
    
    Args:
        job_id: 任务ID（可选，默认自动生成）
    """
    if job_id is None:
        job_id = f"test-job-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print("=" * 60)
    print("RabbitMQ 消息发送测试")
    print("=" * 60)
    print(f"队列: review_queue")
    print(f"任务ID: {job_id}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 连接 RabbitMQ
        print("\n🔌 连接到 RabbitMQ...")
        await rabbitmq_client.connect()
        print("✅ 连接成功")
        
        # 构造消息
        message = {
            "action": "start_review",
            "job_id": job_id,
            "user_id": "test_user_001"
        }
        
        print(f"\n📨 发送消息:")
        print(f"  action: {message['action']}")
        print(f"  job_id: {message['job_id']}")
        print(f"  user_id: {message['user_id']}")
        
        # 发送消息
        await rabbitmq_client.publish_message(
            queue="review_queue",
            message=message
        )
        
        print("\n✅ 消息已发送到 review_queue")
        print("\n💡 提示:")
        print("  1. 确保 ReviewConsumer 正在运行")
        print("  2. 查看 Consumer 日志确认消息已被处理")
        print("  3. 检查 Redis 中的审核状态")
        
        print("\n🔍 验证命令:")
        print(f"  redis-cli GET review:state:{job_id}")
        print(f"  redis-cli GET review:lock:{job_id}")
        
    except Exception as e:
        print(f"\n❌ 发送失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭连接
        await rabbitmq_client.close()
        print("\n✅ 连接已关闭")


async def send_multiple_messages(count: int = 5):
    """
    发送多条测试消息
    
    Args:
        count: 消息数量
    """
    print("=" * 60)
    print(f"批量发送 {count} 条消息")
    print("=" * 60)
    
    try:
        await rabbitmq_client.connect()
        
        for i in range(count):
            job_id = f"test-job-batch-{i+1:03d}"
            message = {
                "action": "start_review",
                "job_id": job_id,
                "user_id": "test_user_001"
            }
            
            await rabbitmq_client.publish_message(
                queue="review_queue",
                message=message
            )
            
            print(f"✅ [{i+1}/{count}] 消息已发送: {job_id}")
            
            # 延迟一下，避免过快
            await asyncio.sleep(0.5)
        
        print(f"\n✅ 所有 {count} 条消息已发送")
    
    except Exception as e:
        print(f"\n❌ 发送失败: {e}")
    
    finally:
        await rabbitmq_client.close()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RabbitMQ 消息发送测试")
    parser.add_argument(
        "--job-id",
        type=str,
        help="任务ID（可选）"
    )
    parser.add_argument(
        "--batch",
        type=int,
        help="批量发送消息数量"
    )
    
    args = parser.parse_args()
    
    if args.batch:
        # 批量发送
        await send_multiple_messages(args.batch)
    else:
        # 单条发送
        await send_test_message(args.job_id)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 已取消")
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
