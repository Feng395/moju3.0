"""
快速测试 502 问题
"""
import asyncio
import httpx


async def quick_test():
    """快速测试"""
    
    api_url = "http://192.168.1.51:8300/api/pricing/recalculate"
    
    # 测试 1: 使用 Postman 成功的参数
    print("=" * 60)
    print("测试 1: 使用 Postman 成功的 job_id")
    print("=" * 60)
    
    success_params = {
        "job_id": "03aae990-9c50-4273-8e37-0bb524a94ddc",
        "subgraph_ids": [
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_LP-02",
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_PH2-04",
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_DIE-03",
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_DIE-04"
        ],
        "options": {
            "force_recalculate": True,
            "skip_search": False
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"📤 发送请求...")
            response = await client.post(api_url, json=success_params)
            print(f"✅ 成功! 状态码: {response.status_code}")
            print(f"📋 响应: {response.text[:500]}")
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 错误: {e.response.status_code}")
        print(f"📋 响应: {e.response.text[:500]}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    print()
    
    # 测试 2: 使用代码中失败的参数
    print("=" * 60)
    print("测试 2: 使用代码中失败的 job_id")
    print("=" * 60)
    
    fail_params = {
        "job_id": "26f6c8fa-6038-4673-b991-cc6435a63c77",
        "subgraph_ids": [
            "b60caf7b-467a-4054-a849-d5dcf7185e7d_LP-02",
            "b60caf7b-467a-4054-a849-d5dcf7185e7d_PH2-04",
            "b60caf7b-467a-4054-a849-d5dcf7185e7d_DIE-03",
            "b60caf7b-467a-4054-a849-d5dcf7185e7d_DIE-04"
        ],
        "options": {
            "force_recalculate": True,
            "skip_search": False
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"📤 发送请求...")
            response = await client.post(api_url, json=fail_params)
            print(f"✅ 成功! 状态码: {response.status_code}")
            print(f"📋 响应: {response.text[:500]}")
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 错误: {e.response.status_code}")
        print(f"📋 响应: {e.response.text[:500]}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    print()
    print("=" * 60)
    print("💡 结论:")
    print("如果测试1成功、测试2失败 → 问题在于 job_id 数据")
    print("如果两个都失败 → 问题在于服务本身或网络")
    print("如果两个都成功 → 问题可能在于代码的其他配置")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(quick_test())
