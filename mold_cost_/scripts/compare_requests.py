"""
对比 Postman 请求和代码请求的差异
用于诊断 502 问题
"""
import asyncio
import httpx
import json


async def test_with_different_configs():
    """使用不同配置测试 API"""
    
    api_url = "http://192.168.1.51:8300/api/pricing/recalculate"
    
    # Postman 的请求参数
    postman_params = {
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
    
    # 代码中的请求参数（从日志复制）
    code_params = {
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
    
    print("=" * 80)
    print("🔍 对比测试：Postman vs 代码请求")
    print("=" * 80)
    print()
    
    # 测试 1: Postman 参数
    print("【测试 1】使用 Postman 参数")
    print(f"📋 job_id: {postman_params['job_id']}")
    await test_request(api_url, postman_params, "Postman")
    print()
    
    # 测试 2: 代码参数
    print("【测试 2】使用代码参数")
    print(f"📋 job_id: {code_params['job_id']}")
    await test_request(api_url, code_params, "代码")
    print()
    
    # 测试 3: 不同的 httpx 配置
    print("【测试 3】测试不同的 httpx 配置")
    await test_with_headers(api_url, postman_params)
    print()
    
    print("=" * 80)
    print("🏁 测试完成")
    print("=" * 80)


async def test_request(api_url: str, params: dict, label: str):
    """测试单个请求"""
    try:
        # 使用与代码相同的配置
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(api_url, json=params)
            
            print(f"✅ {label} 请求成功")
            print(f"📊 状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"📋 响应: {json.dumps(result, indent=2, ensure_ascii=False)[:300]}")
                except:
                    print(f"📋 响应: {response.text[:300]}")
            else:
                print(f"📋 响应: {response.text[:300]}")
                
    except httpx.HTTPStatusError as e:
        print(f"❌ {label} HTTP 错误: {e.response.status_code}")
        print(f"📋 响应: {e.response.text[:300]}")
    except Exception as e:
        print(f"❌ {label} 请求失败: {type(e).__name__}: {e}")


async def test_with_headers(api_url: str, params: dict):
    """测试添加不同请求头"""
    
    headers_configs = [
        {
            "name": "默认（无额外请求头）",
            "headers": {}
        },
        {
            "name": "添加 User-Agent",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        },
        {
            "name": "添加 Accept",
            "headers": {
                "Accept": "application/json"
            }
        },
        {
            "name": "完整请求头（模拟 Postman）",
            "headers": {
                "User-Agent": "PostmanRuntime/7.32.3",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }
        }
    ]
    
    for config in headers_configs:
        print(f"  📌 {config['name']}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    api_url,
                    json=params,
                    headers=config['headers']
                )
                print(f"     ✅ 状态码: {response.status_code}")
        except httpx.HTTPStatusError as e:
            print(f"     ❌ HTTP 错误: {e.response.status_code}")
        except Exception as e:
            print(f"     ❌ 失败: {type(e).__name__}")
        print()


async def check_service_status():
    """检查服务状态"""
    print("=" * 80)
    print("🔍 检查目标服务状态")
    print("=" * 80)
    print()
    
    base_url = "http://192.168.1.51:8300"
    
    # 测试根路径
    print("【测试】访问根路径")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(base_url)
            print(f"✅ 服务可访问: {response.status_code}")
            print(f"📋 响应: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 服务不可访问: {e}")
    
    print()
    
    # 测试健康检查端点（如果有）
    health_endpoints = ["/health", "/api/health", "/ping", "/api/ping"]
    
    print("【测试】健康检查端点")
    for endpoint in health_endpoints:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}{endpoint}")
                print(f"✅ {endpoint}: {response.status_code}")
        except httpx.HTTPStatusError as e:
            print(f"⚠️  {endpoint}: {e.response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: 不可访问")
    
    print()


if __name__ == "__main__":
    # 先检查服务状态
    asyncio.run(check_service_status())
    
    # 再对比请求
    asyncio.run(test_with_different_configs())
