"""
测试 LLM API 连接
测试 Qwen3 API 是否可用
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()


async def test_llm_api():
    """测试 LLM API"""
    print("\n" + "="*60)
    print("测试 LLM API 连接")
    print("="*60)
    
    # 读取配置
    api_key = os.getenv("OPENAI_API_KEY", "sk-dummy")
    base_url = os.getenv("OPENAI_BASE_URL", "https://qwen3.qyagent.top/v1")
    model = os.getenv("OPENAI_MODEL", "Qwen3-30B-A3B-Instruct")
    
    print(f"\n配置信息：")
    print(f"  API Key: {api_key[:10]}..." if len(api_key) > 10 else f"  API Key: {api_key}")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    
    # 测试请求
    print(f"\n发送测试请求...")
    
    try:
        import httpx
        
        # 构建请求
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个有帮助的助手。"},
                {"role": "user", "content": "你好，请回复'测试成功'"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        print(f"\n请求 URL: {url}")
        print(f"请求头: Authorization: Bearer {api_key[:10]}...")
        print(f"请求体: {data}")
        
        # 发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            
            print(f"\n响应状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ 请求成功！")
                print(f"响应内容: {result}")
                
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    print(f"\n🤖 AI 回复: {content}")
                    return True
                else:
                    print(f"\n⚠️  响应格式异常")
                    return False
            else:
                print(f"\n❌ 请求失败！")
                print(f"错误信息: {response.text}")
                
                # 分析错误原因
                if response.status_code == 403:
                    print(f"\n可能的原因：")
                    print(f"  1. API Key 无效或已过期")
                    print(f"  2. 请求内容触发了安全策略")
                    print(f"  3. IP 地址被限制")
                    print(f"  4. 需要添加特定的请求头（如 User-Agent）")
                elif response.status_code == 401:
                    print(f"\n可能的原因：")
                    print(f"  1. API Key 错误")
                    print(f"  2. Authorization 头格式错误")
                elif response.status_code == 429:
                    print(f"\n可能的原因：")
                    print(f"  1. 请求频率过高")
                    print(f"  2. 配额已用完")
                
                return False
    
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_user_agent():
    """测试添加 User-Agent 后的请求"""
    print("\n" + "="*60)
    print("测试 2: 添加 User-Agent")
    print("="*60)
    
    # 读取配置
    api_key = os.getenv("OPENAI_API_KEY", "sk-dummy")
    base_url = os.getenv("OPENAI_BASE_URL", "https://qwen3.qyagent.top/v1")
    model = os.getenv("OPENAI_MODEL", "Qwen3-30B-A3B-Instruct")
    
    print(f"\n发送测试请求（带 User-Agent）...")
    
    try:
        import httpx
        
        # 构建请求
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "curl/8.0"  # 添加 User-Agent
        }
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "temperature": 0.7,
            "max_tokens": 50
        }
        
        print(f"请求头: {headers}")
        
        # 发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            
            print(f"\n响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ 请求成功！")
                content = result["choices"][0]["message"]["content"]
                print(f"🤖 AI 回复: {content}")
                return True
            else:
                print(f"\n❌ 请求失败！")
                print(f"错误信息: {response.text}")
                return False
    
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return False


async def test_simple_message():
    """测试简单消息（避免触发安全策略）"""
    print("\n" + "="*60)
    print("测试 3: 简单消息")
    print("="*60)
    
    # 读取配置
    api_key = os.getenv("OPENAI_API_KEY", "sk-dummy")
    base_url = os.getenv("OPENAI_BASE_URL", "https://qwen3.qyagent.top/v1")
    model = os.getenv("OPENAI_MODEL", "Qwen3-30B-A3B-Instruct")
    
    print(f"\n发送简单消息...")
    
    try:
        import httpx
        
        # 构建请求
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "curl/8.0"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": "1+1=?"}  # 非常简单的问题
            ],
            "temperature": 0,
            "max_tokens": 10
        }
        
        # 发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            
            print(f"\n响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ 请求成功！")
                content = result["choices"][0]["message"]["content"]
                print(f"🤖 AI 回复: {content}")
                return True
            else:
                print(f"\n❌ 请求失败！")
                print(f"错误信息: {response.text}")
                return False
    
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return False


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("LLM API 连接测试")
    print("="*60)
    
    results = []
    
    # 测试 1: 基础请求
    result1 = await test_llm_api()
    results.append(("基础请求", result1))
    
    # 测试 2: 添加 User-Agent
    result2 = await test_with_user_agent()
    results.append(("添加 User-Agent", result2))
    
    # 测试 3: 简单消息
    result3 = await test_simple_message()
    results.append(("简单消息", result3))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, result in results:
        status = "✅ 成功" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    success_count = sum(1 for _, r in results if r)
    print(f"\n成功: {success_count}/{len(results)}")
    
    if success_count == 0:
        print("\n建议：")
        print("  1. 检查 API Key 是否正确")
        print("  2. 检查 Base URL 是否可访问")
        print("  3. 尝试更换 API 服务商")
        print("  4. 联系 API 服务商获取支持")
    elif success_count < len(results):
        print("\n部分测试成功，可能需要调整请求参数")
    else:
        print("\n所有测试通过！LLM API 工作正常")


if __name__ == "__main__":
    asyncio.run(main())
