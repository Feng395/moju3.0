"""
测试 LLM 连接

快速验证 LLM API 是否可用
"""
import asyncio
import os
import sys
import httpx

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()


async def test_llm_connection():
    """测试 LLM API 连接"""
    print("=" * 60)
    print("LLM 连接测试")
    print("=" * 60)
    
    # 读取配置
    use_llm = os.getenv("USE_LLM", "false").lower() == "true"
    base_url = os.getenv("OPENAI_BASE_URL", "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    timeout = float(os.getenv("LLM_TIMEOUT", "30"))
    
    print(f"\n配置信息:")
    print(f"  USE_LLM: {use_llm}")
    print(f"  OPENAI_BASE_URL: {base_url}")
    print(f"  OPENAI_API_KEY: {api_key[:10]}..." if api_key else "  OPENAI_API_KEY: (未设置)")
    print(f"  OPENAI_MODEL: {model}")
    print(f"  LLM_TIMEOUT: {timeout}s")
    
    if not use_llm:
        print("\n⚠️  USE_LLM=false，跳过测试")
        return
    
    if not base_url:
        print("\n❌ OPENAI_BASE_URL 未设置")
        return
    
    if not api_key:
        print("\n⚠️  OPENAI_API_KEY 未设置，可能会失败")
    
    # 测试连接
    print(f"\n🔌 测试连接: {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 测试简单的 chat completion
            response = await client.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": "你好，请回复'连接成功'"
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 50
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "curl/8.0"
                }
            )
            
            print(f"✅ HTTP 状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"✅ LLM 响应: {content}")
                print(f"\n🎉 连接成功！")
                return True
            else:
                print(f"❌ 请求失败: {response.text}")
                return False
    
    except httpx.ConnectError as e:
        print(f"❌ 连接失败: {e}")
        print(f"\n可能的原因:")
        print(f"  1. LLM 服务未启动")
        print(f"  2. URL 地址错误: {base_url}")
        print(f"  3. 网络不通")
        return False
    
    except httpx.TimeoutException as e:
        print(f"❌ 连接超时: {e}")
        print(f"\n可能的原因:")
        print(f"  1. LLM 服务响应慢")
        print(f"  2. 网络延迟高")
        print(f"  3. 超时时间设置过短: {timeout}s")
        return False
    
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    success = await test_llm_connection()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ LLM 连接正常，可以运行完整测试")
        print("=" * 60)
        print("\n运行完整测试:")
        print("  python test_intent_recognition_enhanced.py")
    else:
        print("\n" + "=" * 60)
        print("❌ LLM 连接失败")
        print("=" * 60)
        print("\n解决方案:")
        print("  1. 检查 .env 文件中的配置")
        print("  2. 确认 LLM 服务已启动")
        print("  3. 测试网络连接:")
        print(f"     curl {os.getenv('OPENAI_BASE_URL', 'http://...')}/models")
        print("\n或者使用规则识别模式:")
        print("  在 .env 中设置 USE_LLM=false")


if __name__ == "__main__":
    asyncio.run(main())
