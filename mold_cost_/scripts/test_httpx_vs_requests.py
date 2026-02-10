"""
测试 httpx 和 requests 的差异
验证修复后的代码是否能正常工作
"""
import asyncio
import httpx
import requests
import time
import json


def test_with_requests():
    """使用 requests 测试（服务管理员推荐的方式）"""
    print("=" * 80)
    print("【测试 1】使用 requests 库（推荐方式）")
    print("=" * 80)
    
    url = "http://192.168.1.51:8300/api/pricing/recalculate"
    
    data = {
        "job_id": "03aae990-9c50-4273-8e37-0bb524a94ddc",
        "subgraph_ids": [
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_LP-02",
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_PH2-04"
        ],
        "options": {
            "force_recalculate": True,
            "skip_search": False
        }
    }
    
    try:
        start = time.time()
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=data,  # 使用 json 参数
            timeout=60
        )
        elapsed = time.time() - start
        
        print(f"✅ 请求成功")
        print(f"⏱️  耗时: {elapsed:.2f}秒")
        print(f"📊 状态码: {response.status_code}")
        print(f"📋 响应: {response.text[:200]}")
        
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    print()


async def test_with_httpx_old():
    """使用 httpx 测试（旧方式 - 300秒超时）"""
    print("=" * 80)
    print("【测试 2】使用 httpx 库（旧方式 - 300秒超时）")
    print("=" * 80)
    
    url = "http://192.168.1.51:8300/api/pricing/recalculate"
    
    data = {
        "job_id": "03aae990-9c50-4273-8e37-0bb524a94ddc",
        "subgraph_ids": [
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_DIE-03",
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_DIE-04"
        ],
        "options": {
            "force_recalculate": True,
            "skip_search": False
        }
    }
    
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=data)
            elapsed = time.time() - start
            
            print(f"✅ 请求成功")
            print(f"⏱️  耗时: {elapsed:.2f}秒")
            print(f"📊 状态码: {response.status_code}")
            print(f"📋 响应: {response.text[:200]}")
            
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ 请求失败: {e}")
        print(f"⏱️  耗时: {elapsed:.2f}秒")
    
    print()


async def test_with_httpx_new():
    """使用 httpx 测试（新方式 - 60秒超时 + 明确请求头）"""
    print("=" * 80)
    print("【测试 3】使用 httpx 库（新方式 - 60秒超时 + 明确请求头）")
    print("=" * 80)
    
    url = "http://192.168.1.51:8300/api/pricing/recalculate"
    
    data = {
        "job_id": "03aae990-9c50-4273-8e37-0bb524a94ddc",
        "subgraph_ids": [
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_LP-02"
        ],
        "options": {
            "force_recalculate": True,
            "skip_search": False
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                json=data,
                headers=headers
            )
            elapsed = time.time() - start
            
            print(f"✅ 请求成功")
            print(f"⏱️  耗时: {elapsed:.2f}秒")
            print(f"📊 状态码: {response.status_code}")
            print(f"📋 响应: {response.text[:200]}")
            
    except httpx.TimeoutException as e:
        elapsed = time.time() - start
        print(f"⏱️  超时: {elapsed:.2f}秒")
        print(f"💡 建议: 服务器可能正在处理其他请求，请稍后重试")
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ 请求失败: {e}")
        print(f"⏱️  耗时: {elapsed:.2f}秒")
    
    print()


async def main():
    """主测试流程"""
    print("\n")
    print("🔍 测试 httpx vs requests")
    print("目标: 验证修复后的代码是否能正常工作")
    print("\n")
    
    # 测试 1: requests（基准）
    test_with_requests()
    
    # 等待几秒，避免服务器过载
    print("⏳ 等待 5 秒...")
    await asyncio.sleep(5)
    
    # 测试 2: httpx 旧方式
    await test_with_httpx_old()
    
    # 等待几秒
    print("⏳ 等待 5 秒...")
    await asyncio.sleep(5)
    
    # 测试 3: httpx 新方式
    await test_with_httpx_new()
    
    # 总结
    print("=" * 80)
    print("💡 总结")
    print("=" * 80)
    print("""
1. 如果测试 1 成功 → requests 库工作正常（基准）
2. 如果测试 2 失败/超时 → 旧的 httpx 方式有问题
3. 如果测试 3 成功 → 新的 httpx 方式修复了问题

关键改进：
- 超时时间从 300 秒改为 60 秒
- 明确设置 Content-Type 请求头
- 使用 json 参数（而不是 data）

如果测试 3 仍然失败，可能需要：
- 检查服务器是否正在处理其他请求
- 重启目标服务器
- 增加请求之间的间隔时间
    """)


if __name__ == "__main__":
    asyncio.run(main())
