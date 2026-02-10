"""
测试聊天历史功能
展示完整的使用流程
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
            response = await client.get(f"{BASE_URL}/api/v1/review/health")
            return response.status_code == 200
    except Exception as e:
        return False


async def test_complete_flow():
    """测试完整流程"""
    # 检查服务器
    print("检查 API Gateway 是否运行...")
    if not await check_server():
        print("❌ 错误: API Gateway 未运行!")
        print("\n请先启动 API Gateway:")
        print("  cd moldCost")
        print("  python -m api_gateway.main")
        sys.exit(1)
    
    print("✅ API Gateway 正在运行\n")
    
    # 检查 Token
    if TOKEN == "YOUR_JWT_TOKEN":
        print("❌ 错误: 请先设置 JWT Token!")
        print("\n生成 Token:")
        print("  python generate_test_token.py")
        print("\n然后修改 examples/test_chat_history.py 中的 TOKEN 变量")
        sys.exit(1)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        job_id = "test_chat_history_001"
        
        print("=" * 60)
        print("测试聊天历史功能")
        print("=" * 60)
        
        # 1. 启动审核（自动创建会话和系统消息）
        print("\n1. 启动审核...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/start",
            headers=headers,
            json={"job_id": job_id}
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 2. 提交第一次修改（自动记录用户消息和助手回复）
        print("\n2. 提交第一次修改...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/{job_id}/modify",
            headers=headers,
            json={"modification_text": "将 UP01 的材质改为 718"}
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 3. 提交第二次修改
        print("\n3. 提交第二次修改...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/{job_id}/modify",
            headers=headers,
            json={"modification_text": "将 DOWN01 的重量改为 7.5kg"}
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 4. 确认修改（自动记录系统消息）
        print("\n4. 确认修改...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/{job_id}/confirm",
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 5. 查看聊天历史
        print("\n5. 查看聊天历史...")
        response = await client.get(
            f"{BASE_URL}/api/v1/chat/history/{job_id}",
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            history = response.json()
            print(f"\n会话信息:")
            print(f"  会话ID: {history['session_id']}")
            print(f"  消息数: {history['total_count']}")
            
            print(f"\n消息列表:")
            for i, msg in enumerate(history['messages'], 1):
                role_emoji = {
                    'system': 'ℹ️ ',
                    'user': '👤',
                    'assistant': '🤖'
                }.get(msg['role'], '❓')
                
                print(f"\n  [{i}] {role_emoji} {msg['role'].upper()}")
                print(f"      时间: {msg['timestamp']}")
                print(f"      内容: {msg['content']}")
                if msg.get('metadata'):
                    print(f"      元数据: {json.dumps(msg['metadata'], ensure_ascii=False)}")
        else:
            print(f"错误: {response.text}")
        
        # 6. 获取用户的所有会话
        print("\n6. 获取用户的所有会话...")
        response = await client.get(
            f"{BASE_URL}/api/v1/chat/sessions",
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            sessions = response.json()
            print(f"\n用户会话列表:")
            print(f"  总数: {sessions['total_count']}")
            for i, session in enumerate(sessions['sessions'], 1):
                print(f"\n  [{i}] {session['session_id']}")
                print(f"      任务ID: {session['job_id']}")
                print(f"      状态: {session['status']}")
                print(f"      消息数: {session['message_count']}")
                print(f"      创建时间: {session['created_at']}")
        else:
            print(f"错误: {response.text}")


async def test_sse_chat_with_history():
    """测试 SSE 聊天（会自动记录历史）"""
    async with httpx.AsyncClient() as client:
        job_id = "test_chat_history_002"
        
        print("\n" + "=" * 60)
        print("测试 SSE 聊天历史记录")
        print("=" * 60)
        
        # 1. 启动审核
        print("\n1. 启动审核...")
        await client.post(
            f"{BASE_URL}/api/v1/review/start",
            headers=headers,
            json={"job_id": job_id}
        )
        
        # 2. 发送聊天消息（非流式）
        print("\n2. 发送聊天消息...")
        response = await client.post(
            f"{BASE_URL}/api/v1/chat/completions",
            headers=headers,
            json={
                "job_id": job_id,
                "message": "帮我检查一下数据",
                "stream": False
            }
        )
        print(f"AI回复: {response.json()}")
        
        # 3. 查看历史
        print("\n3. 查看聊天历史...")
        response = await client.get(
            f"{BASE_URL}/api/v1/chat/history/{job_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            history = response.json()
            print(f"共有 {history['total_count']} 条消息")
            for msg in history['messages']:
                print(f"[{msg['role']}] {msg['content']}")


if __name__ == "__main__":
    print("请确保:")
    print("1. API Gateway 正在运行 (python -m api_gateway.main)")
    print("2. 数据库表已创建 (psql -f scripts/create_chat_history_table.sql)")
    print("3. 已设置正确的 JWT Token")
    print()
    
    # 运行测试
    asyncio.run(test_complete_flow())
    
    # 可选：测试 SSE 聊天
    # asyncio.run(test_sse_chat_with_history())
