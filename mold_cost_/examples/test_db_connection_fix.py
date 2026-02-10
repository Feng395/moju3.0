"""
测试数据库连接泄漏修复
验证流式聊天不会导致连接泄漏
"""
import asyncio
import httpx
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def test_streaming_chat():
    """测试流式聊天（多次调用，检查是否有连接泄漏）"""
    print("=" * 60)
    print("测试流式聊天 - 连接泄漏检查")
    print("=" * 60)
    
    # 配置
    BASE_URL = "http://localhost:8211"
    TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiJhNjNiNzg2My01ZmFmLTRiMDAtOWVjMy03NTg0OTViMGZiNjYiLCJyb2xlIjoiYWRtaW4iLCJlbWFpbCI6ImFkbWluQGV4YW1wbGUuY29tIiwicmVhbF9uYW1lIjoiXHU3Y2ZiXHU3ZWRmXHU3YmExXHU3NDA2XHU1NDU4IiwiZXhwIjoxNzcwMzUxOTA3LCJpYXQiOjE3Njg1NTE5MDd9.hb70q_x6TSz1GXWPkANTiXNxWvq2vU-qVX5XMgyCmkk"  # 替换为实际的 token
    JOB_ID = "752d4c99-8bd1-4933-8eb6-f519d3b32297"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\n📝 配置:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Job ID: {JOB_ID}")
    print(f"   测试次数: 10 次")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 连续发送 10 次流式聊天请求
        for i in range(1, 11):
            print(f"🔄 第 {i} 次请求...")
            
            try:
                async with client.stream(
                    "POST",
                    f"{BASE_URL}/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "job_id": JOB_ID,
                        "message": f"测试消息 {i}",
                        "stream": True,
                        "history": []
                    }
                ) as response:
                    if response.status_code == 200:
                        # 读取流式响应
                        chunk_count = 0
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                chunk_count += 1
                        
                        print(f"   ✅ 成功 - 收到 {chunk_count} 个数据块")
                    else:
                        print(f"   ❌ 失败 - 状态码: {response.status_code}")
                
                # 短暂延迟
                await asyncio.sleep(0.5)
            
            except Exception as e:
                print(f"   ❌ 错误: {e}")
    
    print()
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    print()
    print("检查要点:")
    print("1. 查看服务器日志，确认没有连接泄漏警告")
    print("2. 所有请求都应该成功完成")
    print("3. 数据库连接应该正确关闭")
    print()


async def test_non_streaming_chat():
    """测试非流式聊天"""
    print("=" * 60)
    print("测试非流式聊天")
    print("=" * 60)
    
    # 配置
    BASE_URL = "http://localhost:8211"
    TOKEN = "your_test_token_here"  # 替换为实际的 token
    JOB_ID = "test-job-001"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\n📝 配置:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Job ID: {JOB_ID}")
    print(f"   测试次数: 5 次")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 连续发送 5 次非流式聊天请求
        for i in range(1, 6):
            print(f"🔄 第 {i} 次请求...")
            
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "job_id": JOB_ID,
                        "message": f"测试消息 {i}",
                        "stream": False,
                        "history": []
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ 成功 - 回复: {result['data']['message'][:50]}...")
                else:
                    print(f"   ❌ 失败 - 状态码: {response.status_code}")
                
                # 短暂延迟
                await asyncio.sleep(0.5)
            
            except Exception as e:
                print(f"   ❌ 错误: {e}")
    
    print()
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


async def main():
    """主函数"""
    print()
    print("=" * 60)
    print("数据库连接泄漏修复验证")
    print("=" * 60)
    print()
    print("⚠️  注意:")
    print("1. 确保 API Gateway 服务正在运行")
    print("2. 替换脚本中的 TOKEN 为实际的 JWT Token")
    print("3. 确保 JOB_ID 对应的审核会话已启动")
    print()
    
    choice = input("选择测试类型 (1=流式, 2=非流式, 3=全部): ")
    
    if choice == "1":
        await test_streaming_chat()
    elif choice == "2":
        await test_non_streaming_chat()
    elif choice == "3":
        await test_streaming_chat()
        print("\n" + "=" * 60 + "\n")
        await test_non_streaming_chat()
    else:
        print("❌ 无效的选择")


if __name__ == "__main__":
    asyncio.run(main())
