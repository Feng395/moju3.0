"""
详细诊断 502 问题
"""
import asyncio
import httpx
import socket


async def diagnose():
    """详细诊断"""
    
    print("=" * 80)
    print("🔍 502 Bad Gateway 详细诊断")
    print("=" * 80)
    print()
    
    # 1. 检查 DNS 解析
    print("【步骤 1】DNS 解析检查")
    try:
        ip = socket.gethostbyname("192.168.1.51")
        print(f"✅ IP 地址: {ip}")
    except Exception as e:
        print(f"❌ DNS 解析失败: {e}")
    print()
    
    # 2. 检查端口连通性
    print("【步骤 2】端口连通性检查")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(("192.168.1.51", 8300))
        sock.close()
        
        if result == 0:
            print(f"✅ 端口 8300 可访问")
        else:
            print(f"❌ 端口 8300 不可访问")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    print()
    
    # 3. 检查服务根路径
    print("【步骤 3】服务根路径检查")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://192.168.1.51:8300/")
            print(f"✅ 根路径响应: {response.status_code}")
            print(f"📋 响应内容: {response.text[:200]}")
    except httpx.HTTPStatusError as e:
        print(f"⚠️  HTTP 错误: {e.response.status_code}")
        print(f"📋 响应: {e.response.text[:200]}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    print()
    
    # 4. 检查健康检查端点
    print("【步骤 4】健康检查端点")
    health_urls = [
        "http://192.168.1.51:8300/health",
        "http://192.168.1.51:8300/api/health",
        "http://192.168.1.51:8300/ping",
    ]
    
    for url in health_urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                print(f"✅ {url}: {response.status_code}")
        except httpx.HTTPStatusError as e:
            print(f"⚠️  {url}: {e.response.status_code}")
        except Exception as e:
            print(f"❌ {url}: 不可访问")
    print()
    
    # 5. 测试目标 API（详细信息）
    print("【步骤 5】目标 API 详细测试")
    api_url = "http://192.168.1.51:8300/api/pricing/recalculate"
    
    test_params = {
        "job_id": "03aae990-9c50-4273-8e37-0bb524a94ddc",
        "subgraph_ids": [
            "50ae53af-943a-4ebd-a27c-57ab10072bc6_LP-02"
        ],
        "options": {
            "force_recalculate": True,
            "skip_search": False
        }
    }
    
    print(f"📍 URL: {api_url}")
    print(f"📋 参数: {test_params}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("📤 发送请求...")
            response = await client.post(api_url, json=test_params)
            
            print(f"📊 状态码: {response.status_code}")
            print(f"📋 响应头:")
            for key, value in response.headers.items():
                print(f"   {key}: {value}")
            print()
            print(f"📋 响应体: {response.text[:500]}")
            
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 错误: {e.response.status_code}")
        print(f"📋 响应头:")
        for key, value in e.response.headers.items():
            print(f"   {key}: {value}")
        print()
        print(f"📋 响应体: {e.response.text[:500]}")
        
    except Exception as e:
        print(f"❌ 请求失败: {type(e).__name__}: {e}")
    
    print()
    
    # 6. 分析结论
    print("=" * 80)
    print("💡 诊断结论:")
    print("=" * 80)
    print()
    print("如果看到 502 Bad Gateway，可能的原因：")
    print()
    print("1. 【最常见】目标服务 (192.168.1.51:8300) 的后端服务挂了")
    print("   - 检查该服务依赖的数据库是否正常")
    print("   - 检查该服务依赖的其他微服务是否正常")
    print()
    print("2. 【配置问题】如果该服务前面有 Nginx/反向代理")
    print("   - 检查 Nginx 配置")
    print("   - 检查 upstream 配置是否正确")
    print()
    print("3. 【服务崩溃】目标服务本身有 bug")
    print("   - 查看该服务的日志: tail -f /path/to/service/logs")
    print("   - 检查该服务是否在运行: ps aux | grep pricing")
    print()
    print("4. 【资源耗尽】服务器资源不足")
    print("   - 检查内存: free -h")
    print("   - 检查 CPU: top")
    print()
    print("=" * 80)
    print()
    print("🔧 建议的排查步骤:")
    print("=" * 80)
    print()
    print("1. SSH 登录到 192.168.1.51 服务器")
    print("2. 检查价格计算服务的日志:")
    print("   tail -f /var/log/pricing-service/error.log")
    print()
    print("3. 检查服务状态:")
    print("   systemctl status pricing-service")
    print("   # 或")
    print("   docker ps | grep pricing")
    print()
    print("4. 如果有 Nginx，检查 Nginx 日志:")
    print("   tail -f /var/log/nginx/error.log")
    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose())
