"""
测试 NC Agent 连接和基本功能
"""
import asyncio
import httpx
import os
from pathlib import Path

# 从环境变量读取配置
NC_AGENT_URL = os.getenv("NC_AGENT_URL", "http://192.168.0.65:8001")
NC_AGENT_TIMEOUT = int(os.getenv("NC_AGENT_TIMEOUT", "60"))


async def test_nc_agent_health():
    """测试 NC Agent 健康检查"""
    print(f"🔍 测试 NC Agent 连接: {NC_AGENT_URL}")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 尝试访问根路径或健康检查端点
            response = await client.get(f"{NC_AGENT_URL}/")
            print(f"✅ NC Agent 响应成功: status={response.status_code}")
            return True
    except httpx.ConnectError:
        print(f"❌ 无法连接到 NC Agent: {NC_AGENT_URL}")
        print("   请检查：")
        print("   1. NC Agent 服务是否正在运行")
        print("   2. 网络连接是否正常")
        print("   3. 防火墙设置是否允许访问")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


async def test_nc_agent_api_docs():
    """测试 NC Agent API 文档"""
    print(f"\n🔍 检查 API 文档: {NC_AGENT_URL}/docs")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{NC_AGENT_URL}/docs")
            if response.status_code == 200:
                print(f"✅ API 文档可访问: {NC_AGENT_URL}/docs")
                print("   你可以在浏览器中打开此链接查看完整的 API 文档")
                return True
            else:
                print(f"⚠️ API 文档返回状态码: {response.status_code}")
                return False
    except Exception as e:
        print(f"⚠️ 无法访问 API 文档: {e}")
        return False


async def test_nc_agent_workflow_endpoint():
    """测试 NC Agent 工作流端点（不实际调用，只检查端点是否存在）"""
    print(f"\n🔍 检查工作流端点: {NC_AGENT_URL}/api/v1/workflow/3d/run")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 发送一个空的 POST 请求，预期会返回 422（参数验证错误）
            response = await client.post(
                f"{NC_AGENT_URL}/api/v1/workflow/3d/run",
                files={},
                data={}
            )
            
            if response.status_code == 422:
                print(f"✅ 工作流端点存在（返回 422 参数验证错误，符合预期）")
                return True
            elif response.status_code == 404:
                print(f"❌ 工作流端点不存在（404）")
                print("   请确认 NC Agent 版本是否支持 /api/v1/workflow/3d/run 端点")
                return False
            else:
                print(f"⚠️ 工作流端点返回意外状态码: {response.status_code}")
                print(f"   响应内容: {response.text[:200]}")
                return True  # 端点存在，只是返回了其他状态码
                
    except Exception as e:
        print(f"❌ 检查工作流端点失败: {e}")
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("NC Agent 连接测试")
    print("=" * 60)
    print(f"配置信息:")
    print(f"  NC_AGENT_URL: {NC_AGENT_URL}")
    print(f"  NC_AGENT_TIMEOUT: {NC_AGENT_TIMEOUT}秒")
    print("=" * 60)
    
    # 运行测试
    results = []
    results.append(await test_nc_agent_health())
    results.append(await test_nc_agent_api_docs())
    results.append(await test_nc_agent_workflow_endpoint())
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if all(results):
        print("✅ 所有测试通过！NC Agent 连接正常")
        print("\n下一步:")
        print("1. 准备测试用的 PRT 和 DXF 文件")
        print("2. 确保文件路径在数据库中正确配置")
        print("3. 运行完整的集成测试")
    else:
        print("❌ 部分测试失败，请检查上述错误信息")
        print("\n建议:")
        print("1. 确认 NC Agent 服务正在运行")
        print("2. 检查网络连接和防火墙设置")
        print("3. 验证 .env 文件中的 NC_AGENT_URL 配置")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
