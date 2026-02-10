"""
测试 /confirm 接口超时问题
诊断 30 秒延迟的原因
"""
import asyncio
import httpx
import time
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://192.168.0.118:8001"
JOB_ID = "2c344545-e7f8-4f51-ac82-0edd5415ed40"


async def test_confirm_timeout():
    """测试确认接口的超时问题"""
    
    print("=" * 60)
    print("测试 /confirm 接口超时问题")
    print("=" * 60)
    
    # 从环境变量获取 token
    token = os.getenv("TEST_TOKEN")
    if not token:
        print("❌ 请设置环境变量 TEST_TOKEN")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 测试 1: 检查 Redis 中的 pending_action
        print("\n【步骤 1】检查 Redis 中的 pending_action")
        print(f"Key: review:pending_action:{JOB_ID}")
        
        # 测试 2: 调用 /confirm 接口
        print("\n【步骤 2】调用 /confirm 接口")
        print(f"URL: {BASE_URL}/api/v1/review/{JOB_ID}/confirm")
        
        start_time = time.time()
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/review/{JOB_ID}/confirm",
                json={"comment": "测试确认"},
                headers=headers
            )
            
            elapsed = time.time() - start_time
            
            print(f"\n⏱️  耗时: {elapsed:.2f} 秒")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text[:500]}")
            
            if elapsed > 10:
                print(f"\n⚠️  警告: 响应时间过长 ({elapsed:.2f}s)")
                print("可能的原因:")
                print("1. 数据库查询慢")
                print("2. Redis 连接超时")
                print("3. 外部 API 调用超时")
                print("4. 锁等待超时")
            
        except httpx.TimeoutException:
            elapsed = time.time() - start_time
            print(f"\n❌ 请求超时 ({elapsed:.2f}s)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ 请求失败 ({elapsed:.2f}s): {e}")


async def check_redis_data():
    """检查 Redis 中的数据"""
    print("\n【诊断】检查 Redis 数据")
    
    try:
        from api_gateway.utils.redis_client import redis_client
        
        # 检查 pending_action
        key = f"review:pending_action:{JOB_ID}"
        data = await redis_client.get(key)
        
        if data:
            import json
            pending_action = json.loads(data)
            print(f"✅ 找到 pending_action:")
            print(f"   action_type: {pending_action.get('action_type')}")
            print(f"   created_at: {pending_action.get('created_at')}")
        else:
            print(f"❌ 未找到 pending_action (key: {key})")
        
        # 检查 review state
        state_key = f"review:state:{JOB_ID}"
        state_data = await redis_client.get(state_key)
        
        if state_data:
            print(f"✅ 找到 review state")
        else:
            print(f"❌ 未找到 review state (key: {state_key})")
        
        # 检查锁
        lock_key = f"review:lock:{JOB_ID}"
        lock_data = await redis_client.get(lock_key)
        
        if lock_data:
            print(f"✅ 找到分布式锁")
        else:
            print(f"❌ 未找到分布式锁 (key: {lock_key})")
    
    except Exception as e:
        print(f"❌ Redis 检查失败: {e}")


if __name__ == "__main__":
    print("开始诊断...")
    asyncio.run(check_redis_data())
    asyncio.run(test_confirm_timeout())
