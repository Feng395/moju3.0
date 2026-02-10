"""
测试 SSE 流式聊天接口

使用方法：
    python examples/test_sse_chat.py --job-id YOUR_JOB_ID

功能：
1. 测试 SSE 流式输出
2. 模拟多轮对话
3. 验证流式响应格式
"""
import asyncio
import httpx
import json
import sys
import argparse
from datetime import datetime


# ========== 配置 ==========

API_BASE_URL = "http://localhost:8211"
TOKEN = None  # 将在运行时生成


# ========== 生成测试 Token ==========

def generate_test_token():
    """生成测试 Token"""
    import jwt
    from datetime import datetime, timedelta
    
    # JWT 配置（与 API Gateway 一致）
    SECRET_KEY = "your-secret-key-change-in-production"
    ALGORITHM = "HS256"
    
    # 创建 Token
    payload = {
        "sub": "test-user-123",
        "user_id": "test-user-123",
        "username": "test_user",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


# ========== SSE 客户端 ==========

async def test_sse_chat(job_id: str, message: str, history: list = None):
    """
    测试 SSE 流式聊天
    
    Args:
        job_id: 任务ID
        message: 用户消息
        history: 历史消息
    """
    print(f"\n{'='*60}")
    print(f"💬 SSE 流式聊天测试")
    print(f"{'='*60}")
    print(f"任务ID: {job_id}")
    print(f"消息: {message}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    url = f"{API_BASE_URL}/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "job_id": job_id,
        "message": message,
        "history": history or [],
        "stream": True
    }
    
    print(f"📤 发送请求...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                print(f"📥 响应状态: {response.status_code}\n")
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"❌ 错误: {error_text.decode()}")
                    return None
                
                print(f"{'='*60}")
                print(f"🤖 AI 回复（流式输出）:")
                print(f"{'='*60}\n")
                
                full_response = ""
                message_id = None
                
                # 逐行读取 SSE 流
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    
                    # 移除 "data: " 前缀
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    try:
                        # 解析 JSON
                        data = json.loads(line)
                        
                        # 处理不同类型的消息
                        if data["type"] == "start":
                            message_id = data.get("message_id")
                            print(f"[开始] message_id={message_id}\n")
                        
                        elif data["type"] == "content":
                            delta = data.get("delta", "")
                            full_response += delta
                            # 实时打印（不换行）
                            print(delta, end="", flush=True)
                        
                        elif data["type"] == "done":
                            finish_reason = data.get("finish_reason")
                            print(f"\n\n[完成] finish_reason={finish_reason}")
                        
                        elif data["type"] == "error":
                            error_msg = data.get("message")
                            print(f"\n\n❌ 错误: {error_msg}")
                    
                    except json.JSONDecodeError:
                        continue
                
                print(f"\n{'='*60}")
                print(f"✅ 流式输出完成")
                print(f"{'='*60}\n")
                
                return full_response
    
    except httpx.HTTPError as e:
        print(f"❌ HTTP 错误: {e}")
        return None
    
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_multi_turn_chat(job_id: str):
    """测试多轮对话"""
    print(f"\n{'='*60}")
    print(f"🔄 多轮对话测试")
    print(f"{'='*60}\n")
    
    history = []
    
    # 第一轮
    print("【第一轮对话】")
    message1 = "你好，我想修改 UP01 的材质"
    response1 = await test_sse_chat(job_id, message1, history)
    
    if response1:
        history.append({"role": "user", "content": message1})
        history.append({"role": "assistant", "content": response1})
    
    await asyncio.sleep(1)
    
    # 第二轮
    print("\n【第二轮对话】")
    message2 = "改成 718 材质"
    response2 = await test_sse_chat(job_id, message2, history)
    
    if response2:
        history.append({"role": "user", "content": message2})
        history.append({"role": "assistant", "content": response2})
    
    await asyncio.sleep(1)
    
    # 第三轮
    print("\n【第三轮对话】")
    message3 = "好的，请帮我确认一下"
    response3 = await test_sse_chat(job_id, message3, history)
    
    print(f"\n{'='*60}")
    print(f"✅ 多轮对话测试完成")
    print(f"{'='*60}\n")


async def test_non_stream_chat(job_id: str, message: str):
    """测试非流式聊天"""
    print(f"\n{'='*60}")
    print(f"📝 非流式聊天测试")
    print(f"{'='*60}\n")
    
    url = f"{API_BASE_URL}/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "job_id": job_id,
        "message": message,
        "history": [],
        "stream": False  # 非流式
    }
    
    print(f"📤 发送请求...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"📥 响应状态: {response.status_code}\n")
            
            if response.status_code == 200:
                data = response.json()
                print(f"响应:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
                print(f"\n✅ 非流式测试通过")
            else:
                print(f"❌ 错误: {response.text}")
    
    except Exception as e:
        print(f"❌ 异常: {e}")


# ========== 主函数 ==========

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试 SSE 流式聊天接口")
    parser.add_argument("--job-id", required=True, help="任务ID")
    parser.add_argument("--message", default="将 UP01 的材质改为 718", help="测试消息")
    parser.add_argument("--multi-turn", action="store_true", help="测试多轮对话")
    parser.add_argument("--non-stream", action="store_true", help="测试非流式")
    
    args = parser.parse_args()
    
    # 生成 Token
    global TOKEN
    TOKEN = generate_test_token()
    
    print(f"\n{'='*60}")
    print(f"SSE 流式聊天测试")
    print(f"{'='*60}")
    print(f"API 地址: {API_BASE_URL}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    print(f"🔑 生成测试 Token...")
    print(f"Token: {TOKEN[:50]}...")
    print(f"任务 ID: {args.job_id}\n")
    
    # 测试流式聊天
    if not args.multi_turn and not args.non_stream:
        await test_sse_chat(args.job_id, args.message)
    
    # 测试多轮对话
    if args.multi_turn:
        await test_multi_turn_chat(args.job_id)
    
    # 测试非流式
    if args.non_stream:
        await test_non_stream_chat(args.job_id, args.message)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(0)
