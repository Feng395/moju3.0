"""
Redis Pub/Sub测试
模拟Agent发送消息到Redis，验证WebSocket能否收到
"""
import redis
import json
import time
import sys

def test_redis_publish():
    """模拟Agent发送进度消息到Redis"""
    print("=" * 60)
    print("Redis Pub/Sub 测试 - 模拟Agent发送消息")
    print("=" * 60)
    
    # 连接Redis
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis连接成功")
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        print("   请确保Redis已启动: docker-compose up -d redis")
        return
    
    # 任务ID
    job_id = "test-job-redis-123"
    print(f"\n📋 任务ID: {job_id}")
    print(f"📡 频道: job:{job_id}:progress")
    print(f"\n💡 提示：请先在浏览器中打开WebSocket测试页面")
    print(f"   URL: tests/test_websocket_browser.html")
    print(f"   任务ID输入: {job_id}")
    print(f"   然后点击'连接'按钮\n")
    
    input("按Enter键开始发送消息...")
    
    # 模拟Agent发送一系列进度消息
    messages = [
        {
            "stage": "initializing",
            "progress": 0,
            "message": "任务初始化...",
            "details": {"status": "starting"}
        },
        {
            "stage": "cad_parsing",
            "progress": 20,
            "message": "正在解析CAD文件...",
            "details": {"file": "mold_part_001.dwg"}
        },
        {
            "stage": "feature_recognition",
            "progress": 50,
            "message": "正在识别特征...",
            "details": {"subgraphs_found": 5}
        },
        {
            "stage": "decision",
            "progress": 70,
            "message": "正在进行工艺决策...",
            "details": {"wire_mode": "mid"}
        },
        {
            "stage": "pricing",
            "progress": 85,
            "message": "正在计算价格...",
            "details": {"total_cost": 12345.67}
        },
        {
            "stage": "completed",
            "progress": 100,
            "message": "任务完成！",
            "details": {
                "total_cost": 12345.67,
                "report_url": "https://example.com/report.xlsx"
            }
        }
    ]
    
    print("\n开始发送消息...\n")
    
    for i, msg in enumerate(messages, 1):
        channel = f"job:{job_id}:progress"
        
        # 发布消息到Redis
        r.publish(channel, json.dumps(msg))
        
        print(f"📤 [{i}/{len(messages)}] 已发送: {msg['stage']} - {msg['progress']}% - {msg['message']}")
        
        # 等待2秒
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ 所有消息已发送！")
    print("=" * 60)
    print("\n💡 检查浏览器WebSocket测试页面，应该能看到实时消息")

def test_redis_connection():
    """测试Redis连接"""
    print("\n" + "=" * 60)
    print("测试Redis连接")
    print("=" * 60)
    
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis连接成功")
        
        # 测试发布
        r.publish("test:channel", "test message")
        print("✅ Redis发布功能正常")
        
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        print("\n解决方法：")
        print("1. 启动Redis: docker-compose up -d redis")
        print("2. 或者安装Redis: https://redis.io/download")
        return False

if __name__ == "__main__":
    print("\n🧪 Redis Pub/Sub 测试\n")
    
    # 先测试连接
    if not test_redis_connection():
        sys.exit(1)
    
    # 发送测试消息
    test_redis_publish()
