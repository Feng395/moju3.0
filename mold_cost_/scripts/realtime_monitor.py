"""
实时监控 Redis 和 WebSocket 消息
在一个终端窗口中同时显示所有信息
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis.asyncio as redis
from api_gateway.config import settings


class ColoredOutput:
    """彩色输出"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # 颜色
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    @staticmethod
    def print_box(title: str, content: dict, color: str):
        """打印带边框的消息"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n{color}╔{'═' * 78}╗{ColoredOutput.RESET}")
        print(f"{color}║ {ColoredOutput.BOLD}[{timestamp}] {title}{ColoredOutput.RESET}{color}{' ' * (76 - len(timestamp) - len(title))}║{ColoredOutput.RESET}")
        print(f"{color}╠{'═' * 78}╣{ColoredOutput.RESET}")
        
        for key, value in content.items():
            # 格式化值
            if isinstance(value, dict):
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
                lines = value_str.split('\n')
                print(f"{color}║{ColoredOutput.RESET} {ColoredOutput.YELLOW}{key:20s}{ColoredOutput.RESET}: {lines[0]}{' ' * (54 - len(lines[0]))} {color}║{ColoredOutput.RESET}")
                for line in lines[1:]:
                    print(f"{color}║{ColoredOutput.RESET}   {line}{' ' * (73 - len(line))} {color}║{ColoredOutput.RESET}")
            else:
                value_str = str(value)
                if len(value_str) > 54:
                    value_str = value_str[:51] + "..."
                print(f"{color}║{ColoredOutput.RESET} {ColoredOutput.YELLOW}{key:20s}{ColoredOutput.RESET}: {value_str}{' ' * (54 - len(value_str))} {color}║{ColoredOutput.RESET}")
        
        print(f"{color}╚{'═' * 78}╝{ColoredOutput.RESET}")


async def monitor_all():
    """同时监控 Redis 和 WebSocket"""
    
    # 打印标题
    print(f"\n{ColoredOutput.BOLD}{ColoredOutput.MAGENTA}")
    print("=" * 80)
    print("实时消息监控 - Redis & WebSocket".center(80))
    print("=" * 80)
    print(f"{ColoredOutput.RESET}\n")
    
    print(f"{ColoredOutput.CYAN}配置信息:{ColoredOutput.RESET}")
    print(f"  Redis URL: {settings.REDIS_URL}")
    print(f"  监听频道: job:*:progress")
    print(f"\n{ColoredOutput.GREEN}开始监控...{ColoredOutput.RESET}")
    print(f"{ColoredOutput.YELLOW}{'─' * 80}{ColoredOutput.RESET}\n")
    
    redis_client = None
    message_count = 0
    
    try:
        # 连接 Redis
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        # 测试连接
        await redis_client.ping()
        print(f"{ColoredOutput.GREEN}✅ Redis 连接成功{ColoredOutput.RESET}\n")
        
        # 订阅频道
        pubsub = redis_client.pubsub()
        await pubsub.psubscribe("job:*:progress")
        print(f"{ColoredOutput.GREEN}✅ 已订阅频道: job:*:progress{ColoredOutput.RESET}\n")
        print(f"{ColoredOutput.CYAN}等待消息...{ColoredOutput.RESET}\n")
        
        # 监听消息
        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                message_count += 1
                
                # 解析频道
                channel = message['channel']
                if isinstance(channel, bytes):
                    channel = channel.decode('utf-8')
                
                # 解析数据
                data_str = message['data']
                if isinstance(data_str, bytes):
                    data_str = data_str.decode('utf-8')
                
                try:
                    data = json.loads(data_str)
                    
                    # 提取 job_id
                    parts = channel.split(':')
                    job_id = parts[1] if len(parts) >= 2 else "unknown"
                    
                    # 1. 显示 Redis 接收到的消息
                    redis_info = {
                        "频道": channel,
                        "任务ID": job_id,
                        "阶段": data.get('stage', 'N/A'),
                        "进度": f"{data.get('progress', 0)}%",
                        "消息": data.get('message', 'N/A'),
                    }
                    
                    if 'current_file' in data:
                        redis_info["当前文件"] = data['current_file']
                    
                    ColoredOutput.print_box(
                        "📥 Redis 消息接收",
                        redis_info,
                        ColoredOutput.CYAN
                    )
                    
                    # 2. 显示 WebSocket 推送的消息
                    ws_message = {
                        "类型": "progress",
                        "任务ID": job_id,
                        "时间戳": datetime.now().isoformat(),
                        "数据": data
                    }
                    
                    ws_info = {
                        "推送目标": f"job_id={job_id} 的所有连接",
                        "消息类型": "progress",
                        "阶段": data.get('stage', 'N/A'),
                        "进度": f"{data.get('progress', 0)}%",
                        "状态消息": data.get('message', 'N/A'),
                    }
                    
                    ColoredOutput.print_box(
                        "📤 WebSocket 推送",
                        ws_info,
                        ColoredOutput.GREEN
                    )
                    
                    # 显示统计
                    print(f"\n{ColoredOutput.BOLD}{ColoredOutput.WHITE}统计信息: 已处理 {message_count} 条消息{ColoredOutput.RESET}")
                    print(f"{ColoredOutput.YELLOW}{'─' * 80}{ColoredOutput.RESET}\n")
                
                except json.JSONDecodeError as e:
                    print(f"{ColoredOutput.RED}❌ JSON 解析失败: {e}{ColoredOutput.RESET}")
                except Exception as e:
                    print(f"{ColoredOutput.RED}❌ 处理消息失败: {e}{ColoredOutput.RESET}")
    
    except KeyboardInterrupt:
        print(f"\n{ColoredOutput.YELLOW}用户中断监控{ColoredOutput.RESET}")
    
    except Exception as e:
        print(f"{ColoredOutput.RED}❌ 监控失败: {e}{ColoredOutput.RESET}")
        import traceback
        traceback.print_exc()
    
    finally:
        if redis_client:
            await redis_client.close()
            print(f"\n{ColoredOutput.CYAN}Redis 连接已关闭{ColoredOutput.RESET}")


async def test_publish():
    """发布测试消息"""
    print(f"\n{ColoredOutput.BOLD}{ColoredOutput.MAGENTA}")
    print("=" * 80)
    print("测试消息发布".center(80))
    print("=" * 80)
    print(f"{ColoredOutput.RESET}\n")
    
    try:
        # 连接 Redis
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        print(f"{ColoredOutput.GREEN}✅ Redis 连接成功{ColoredOutput.RESET}\n")
        
        # 发布多条测试消息
        test_job_id = "test-job-" + datetime.now().strftime("%H%M%S")
        
        stages = [
            {"stage": "initializing", "progress": 0, "message": "任务初始化..."},
            {"stage": "cad_parsing", "progress": 10, "message": "正在解析 CAD 文件...", "current_file": "test.dwg"},
            {"stage": "feature_extraction", "progress": 30, "message": "正在提取特征...", "features_found": 15},
            {"stage": "pricing", "progress": 60, "message": "正在计算价格..."},
            {"stage": "completed", "progress": 100, "message": "任务完成！", "total_cost": 12500.50},
        ]
        
        for i, stage_data in enumerate(stages, 1):
            channel = f"job:{test_job_id}:progress"
            
            print(f"{ColoredOutput.CYAN}[{i}/{len(stages)}] 发布消息到: {channel}{ColoredOutput.RESET}")
            print(f"  内容: {json.dumps(stage_data, ensure_ascii=False)}\n")
            
            await redis_client.publish(channel, json.dumps(stage_data))
            
            print(f"{ColoredOutput.GREEN}✅ 消息已发布{ColoredOutput.RESET}\n")
            
            # 等待一下，让监控脚本有时间处理
            await asyncio.sleep(2)
        
        print(f"{ColoredOutput.BOLD}{ColoredOutput.GREEN}所有测试消息已发布完成！{ColoredOutput.RESET}")
        print(f"{ColoredOutput.YELLOW}请在监控终端查看接收到的消息{ColoredOutput.RESET}\n")
        
        await redis_client.close()
    
    except Exception as e:
        print(f"{ColoredOutput.RED}❌ 发布失败: {e}{ColoredOutput.RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="实时监控 Redis 和 WebSocket 消息")
    parser.add_argument(
        "--test",
        action="store_true",
        help="发布测试消息（在另一个终端运行）"
    )
    
    args = parser.parse_args()
    
    try:
        if args.test:
            asyncio.run(test_publish())
        else:
            asyncio.run(monitor_all())
    except KeyboardInterrupt:
        print(f"\n{ColoredOutput.YELLOW}程序已退出{ColoredOutput.RESET}")
