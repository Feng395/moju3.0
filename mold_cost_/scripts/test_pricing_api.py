"""
测试价格计算 API 连接
用于诊断 502 Bad Gateway 问题
"""
import asyncio
import httpx
import json
from datetime import datetime


async def test_pricing_api():
    """测试价格计算 API"""
    
    # 测试参数
    api_url = "http://192.168.1.51:8300/api/pricing/recalculate"
    test_params = {
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
    
    print("=" * 60)
    print("🔍 价格计算 API 连接测试")
    print("=" * 60)
    print(f"📍 API 地址: {api_url}")
    print(f"📋 请求参数: {json.dumps(test_params, indent=2, ensure_ascii=False)}")
    print()
    
    # 测试 1: 基础连接测试
    print("【测试 1】基础连接测试")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://192.168.1.51:8300/")
            print(f"✅ 服务器可访问: {response.status_code}")
    except Exception as e:
        print(f"❌ 服务器不可访问: {e}")
        return
    
    print()
    
    # 测试 2: API 调用测试（短超时）
    print("【测试 2】API 调用测试（10秒超时）")
    try:
        start_time = datetime.now()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=test_params)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ API 调用成功")
            print(f"📊 状态码: {response.status_code}")
            print(f"⏱️  耗时: {elapsed:.2f}秒")
            print(f"📋 响应: {response.text[:500]}")
    except httpx.TimeoutException as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"⏱️  超时: {elapsed:.2f}秒")
        print(f"💡 建议: API 可能需要更长时间，尝试增加超时时间")
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 错误: {e.response.status_code}")
        print(f"📋 响应: {e.response.text}")
    except Exception as e:
        print(f"❌ 调用失败: {type(e).__name__}: {e}")
    
    print()
    
    # 测试 3: API 调用测试（长超时）
    print("【测试 3】API 调用测试（300秒超时）")
    try:
        start_time = datetime.now()
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(api_url, json=test_params)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ API 调用成功")
            print(f"📊 状态码: {response.status_code}")
            print(f"⏱️  耗时: {elapsed:.2f}秒")
            
            try:
                result = response.json()
                print(f"📋 响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
            except:
                print(f"📋 响应: {response.text[:500]}")
    except httpx.TimeoutException as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"⏱️  超时: {elapsed:.2f}秒")
        print(f"❌ API 执行时间超过 5 分钟")
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 错误: {e.response.status_code}")
        print(f"📋 响应: {e.response.text}")
    except Exception as e:
        print(f"❌ 调用失败: {type(e).__name__}: {e}")
    
    print()
    print("=" * 60)
    print("🏁 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_pricing_api())
