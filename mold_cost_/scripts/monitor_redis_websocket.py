"""
Redis 和 WebSocket 消息监控脚本
实时显示：
1. Redis 接收到的消息
2. WebSocket 推送的消息
3. 连接状态变化
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis.asyncio as redis
from api_gateway.config import settings

# ANSI 颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text:^80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")


def print_redis_message(channel: str, data: Dict[str, Any]):
    """打印 Redis 消息"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    print(f"{Colors.CYAN}[{timestamp}] 📥 Redis 消息{Colors.ENDC}")
    print(f"{Colors.BLUE}  频道: {channel}{Colors.ENDC}")
    
    # 提取 job_id
    parts = channel.split(':')
    if len(parts) >= 2:
        job_id = parts[1]
        print(f"{Colors.BLUE}  任务ID: {job_id}{Colors.ENDC}")
    
    # 打印消息内容
    print(f"{Colors.GREEN}  内容:{Colors.ENDC}")
    for key, value in data.items():
        print(f"    {Colors.YELLOW}{key:20s}{Colors.ENDC}: {value}")
    
    print(f"{Colors.CYAN}{'─' * 80}{Colors.ENDC}")


def print_websocket_push(job_id: str, message: Dict[str, Any], connection_count: int):
    """打印 WebSocket 推送"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    print(f"{Colors.GREEN}[{timestamp}] 📤 WebSocket 推送{Colors.ENDC}")
    print(f"{Colors.BLUE}  任务ID: {job_id}{Colors.ENDC}")
    print(f"{Colors.BLUE}  接收者: {connection_count} 个连接{Colors.ENDC}")
    
    # 打印消息内容
    print(f"{Colors.GREEN}  消息:{Colors.ENDC}")
    print(f"    {Colors.YELLOW}{'type':20s}{Colors.ENDC}: {message.get('type')}")
    print(f"    {Colors.YELLOW}{'timestamp':20s}{Colors.ENDC}: {message.get('timestamp')}")
    
    if 'data' in message:
        print(f"    {Colors.YELLOW}{'data':20s}{Colors.ENDC}:")
        for key, value in message['data'].items():
            print(f"      {Colors.YELLOW}{key:18s}{Colors.ENDC}: {value}")
    
    print(f"{Colors.GREEN}{'─' * 80}{Colors.ENDC}")


def print_connection_change(event: str, job_id: str, count: int):
    """打印连接状态变化"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    if event == "connect":
        emoji = "✅"
        color = Colors.GREEN
        text = "连接建立"
    else:
        emoji = "❌"
        color = Colors.RED
        text = "连接断开"
    
    print(f"{color}[{timestamp}] {emoji} {text}{Colors.ENDC}")
    print(f"{Colors.BLUE}  任务ID: {job_id}{Colors.ENDC}")
    print(f"{Colors.BLUE}  当前连接数: {count}{Colors.ENDC}")
    print(f"{color}{'─' * 80}{Colors.ENDC}")


def print_error(error: str):
    """打印错误"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.RED}[{timestamp}] ❌ 错误: {error}{Colors.ENDC}")


def print_info(info: str):
    """打印信息"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.CYAN}[{timestamp}] ℹ️  {info}{Colors.ENDC}")


async def monitor_redis():
    """监控 Redis 消息"""
    print_header("Redis 消息监控")
    
    try:
        # 连接 Redis
        print_info(f"正在连接 Redis: {settings.REDIS_URL}")
        
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        # 测试连接
        await redis_client.ping()
        print_info("✅ Redis 连接成功")
        
        # 订阅频道
        pubsub = redis_client.pubsub()
        await pubsub.psubscribe("job:*:progress")
        print_info("✅ 已订阅频道: job:*:progress")
        
        print_info("开始监听 Redis 消息...")
        print(f"{Colors.YELLOW}{'─' * 80}{Colors.ENDC}\n")
        
        # 监听消息
        message_count = 0
        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                message_count += 1
                
                # 解析频道和数据
                channel = message['channel']
                if isinstance(channel, bytes):
                    channel = channel.decode('utf-8')
                
                data_str = message['data']
                if isinstance(data_str, bytes):
                    data_str = data_str.decode('utf-8')
                
                try:
                    data = json.loads(data_str)
                    
                    # 打印 Redis 消息
                    print_redis_message(channel, data)
                    
                    # 模拟 WebSocket 推送（显示会推送给多少个连接）
                    parts = channel.split(':')
                    if len(parts) >= 2:
                        job_id = parts[1]
                        
                        # 构造 WebSocket 消息
                        ws_message = {
                            "type": "progress",
                            "job_id": job_id,
                            "timestamp": datetime.now().isoformat(),
                            "data": data
                        }
                        
                        # 这里假设有连接（实际需要查询 ConnectionManager）
                        print_websocket_push(job_id, ws_message, 1)
                    
                    print(f"\n{Colors.BOLD}总消息数: {message_count}{Colors.ENDC}\n")
                
                except json.JSONDecodeError as e:
                    print_error(f"JSON 解析失败: {e}")
    
    except KeyboardInterrupt:
        print_info("\n用户中断监控")
    
    except Exception as e:
        print_error(f"监控失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'redis_client' in locals():
            await redis_client.close()
            print_info("Redis 连接已关闭")


async def monitor_websocket_connections():
    """监控 WebSocket 连接状态（需要访问 ConnectionManager）"""
    print_header("WebSocket 连接监控")
    
    try:
        from api_gateway.websocket import manager
        
        print_info("开始监控 WebSocket 连接...")
        
        last_connections = {}
        
        while True:
            current_connections = {}
            
            # 获取所有活跃连接
            for job_id in manager.get_all_job_ids():
                count = manager.get_connection_count(job_id)
                current_connections[job_id] = count
            
            # 检测变化
            for job_id, count in current_connections.items():
                if job_id not in last_connections:
                    print_connection_change("connect", job_id, count)
                elif last_connections[job_id] != count:
                    if count > last_connections[job_id]:
                        print_connection_change("connect", job_id, count)
                    else:
                        print_connection_change("disconnect", job_id, count)
            
            # 检测断开的连接
            for job_id in last_connections:
                if job_id not in current_connections:
                    print_connection_change("disconnect", job_id, 0)
            
            last_connections = current_connections
            
            # 每秒检查一次
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print_info("\n用户中断监控")
    
    except Exception as e:
        print_error(f"监控失败: {e}")


async def test_publish_message():
    """测试发布消息（用于测试）"""
    print_header("测试消息发布")
    
    try:
        # 连接 Redis
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        print_info("✅ Redis 连接成功")
        
        # 发布测试消息
        test_job_id = "test-job-123"
        test_message = {
            "stage": "cad_parsing",
            "progress": 25,
            "message": "正在解析 CAD 文件...",
            "current_file": "test.dwg"
        }
        
        channel = f"job:{test_job_id}:progress"
        
        print_info(f"发布测试消息到频道: {channel}")
        print_redis_message(channel, test_message)
        
        await redis_client.publish(channel, json.dumps(test_message))
        
        print_info("✅ 测试消息已发布")
        
        await redis_client.close()
    
    except Exception as e:
        print_error(f"发布失败: {e}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis 和 WebSocket 消息监控")
    parser.add_argument(
        "mode",
        choices=["redis", "websocket", "test"],
        help="监控模式: redis=监控Redis消息, websocket=监控WebSocket连接, test=发布测试消息"
    )
    
    args = parser.parse_args()
    
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("Redis & WebSocket 消息监控工具".center(80))
    print("=" * 80)
    print(f"{Colors.ENDC}\n")
    
    print(f"{Colors.CYAN}配置信息:{Colors.ENDC}")
    print(f"  Redis URL: {settings.REDIS_URL}")
    print(f"  监控模式: {args.mode}")
    print()
    
    if args.mode == "redis":
        await monitor_redis()
    elif args.mode == "websocket":
        await monitor_websocket_connections()
    elif args.mode == "test":
        await test_publish_message()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}程序已退出{Colors.ENDC}")
