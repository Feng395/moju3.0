"""
简化版聊天历史测试
只测试 API 接口，不依赖真实数据
"""
import asyncio
import httpx
import json
import sys

# 配置
BASE_URL = "http://localhost:8211"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYTYzYjc4NjMtNWZhZi00YjAwLTllYzMtNzU4NDk1YjBmYjY2IiwidXNlcm5hbWUiOiJ0ZXN0X3VzZXIiLCJyb2xlcyI6WyJhZG1pbiJdLCJleHAiOjE3Njg2MzgyMDR9.j1zuwCV3KhVWq6aCtJD6_itgsIoDWaV26U5PqaIaaPY"  # 替换为实际的 JWT Token

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


async def check_server():
    """检查服务器是否运行"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/api/v1/chat/health")
            return response.status_code == 200
    except:
        return False


async def test_api_endpoints():
    """测试 API 接口"""
    
    # 检查服务器
    print("检查 API Gateway 是否运行...")
    if not await check_server():
        print("❌ 错误: API Gateway 未运行!")
        print("\n请先启动 API Gateway:")
        print("  cd moldCost")
        print("  python -m api_gateway.main")
        return False
    
    print("✅ API Gateway 正在运行\n")
    
    # 检查 Token
    if TOKEN == "YOUR_JWT_TOKEN":
        print("⚠️  警告: 使用默认 Token，可能会失败")
        print("\n生成 Token:")
        print("  python generate_test_token.py")
        print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        session_id = "test_simple_001"
        
        print("=" * 60)
        print("测试聊天历史 API 接口")
        print("=" * 60)
        
        # 1. 测试获取不存在的会话（应该返回 404）
        print("\n1. 测试获取不存在的会话...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/chat/history/{session_id}",
                headers=headers
            )
            print(f"   状态码: {response.status_code}")
            if response.status_code == 404:
                print("   ✅ 正确返回 404（会话不存在）")
            elif response.status_code == 401:
                print("   ❌ 401 未授权 - 请检查 JWT Token")
                return False
            else:
                print(f"   响应: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return False
        
        # 2. 测试获取会话列表
        print("\n2. 测试获取会话列表...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/chat/sessions?limit=10",
                headers=headers
            )
            print(f"   状态码: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 成功获取会话列表")
                print(f"   用户ID: {data.get('user_id', 'N/A')}")
                print(f"   会话数: {data.get('total_count', 0)}")
            elif response.status_code == 401:
                print("   ❌ 401 未授权 - 请检查 JWT Token")
                return False
            else:
                print(f"   响应: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return False
        
        # 3. 测试健康检查
        print("\n3. 测试健康检查...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/chat/health",
                headers=headers
            )
            print(f"   状态码: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ 服务健康")
                print(f"   响应: {response.json()}")
            else:
                print(f"   响应: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return False
        
        print("\n" + "=" * 60)
        print("✅ API 接口测试完成")
        print("=" * 60)
        return True


async def main():
    """主函数"""
    print("聊天历史功能 - 简化测试")
    print()
    
    success = await test_api_endpoints()
    
    if success:
        print("\n下一步:")
        print("1. 确保数据库表已创建")
        print("   psql -h 192.168.0.30 -p 5432 -U postgres -d mold_cost_db \\")
        print("        -f scripts/create_chat_history_table.sql")
        print()
        print("2. 运行完整测试")
        print("   python examples/test_chat_history.py")
    else:
        print("\n请先解决上述问题，然后重试")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
