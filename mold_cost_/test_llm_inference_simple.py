"""
简单测试 LLM 子图推断功能
"""
import asyncio
import os
import httpx


async def test_llm_inference():
    """测试 LLM 推断子图 ID"""
    print("=" * 60)
    print("测试 LLM 子图推断")
    print("=" * 60)
    
    # 模拟历史上下文
    history_context = [
        "user: PH2-04 的价格怎么算的？",
        "assistant: PH2-04 的总成本是 125.50 元，主要包括材料费、热处理费和线割费。",
        "user: 材质改为 Cr12mov"
    ]
    
    user_message = "材质改为 Cr12mov"
    
    print(f"\n📚 历史上下文:")
    for msg in history_context[:-1]:
        print(f"  {msg}")
    
    print(f"\n❓ 当前消息: {user_message}")
    
    # 构建 Prompt
    history_text = "\n".join(history_context[:-1])
    
    prompt = f"""你是一个智能助手，需要从对话历史中推断用户当前想要操作的子图ID。

对话历史：
{history_text}

用户当前消息：
{user_message}

任务：
1. 分析对话历史，找出最近讨论的子图ID（格式如：UP01, LP-02, PH2-04, DIE-03 等）
2. 如果用户当前消息没有明确指定子图，推断用户想要操作的是哪个子图
3. 只返回子图ID，不要其他解释

注意：
- 子图ID通常是2-4个大写字母 + 连字符/下划线（可选）+ 2位数字
- 例如：UP01, LP-02, PH2-04, DIE-03
- 不要把材料名称（如CR12, P20, 718, NAK80, Cr12mov, 45#）当作子图ID
- 如果无法推断，返回 "NONE"

请只返回子图ID或"NONE"："""

    print(f"\n🤖 调用 LLM...")
    
    try:
        llm_base_url = os.getenv("OPENAI_BASE_URL", "https://qwen3.qyagent.top/v1")
        llm_api_key = os.getenv("OPENAI_API_KEY", "sk-xxx")
        llm_model = os.getenv("OPENAI_MODEL", "Qwen3-30B-A3B-Instruct")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{llm_base_url}/chat/completions",
                json={
                    "model": llm_model,
                    "messages": [
                        {"role": "system", "content": "你是一个精确的子图ID识别助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 50
                },
                headers={
                    "Authorization": f"Bearer {llm_api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            llm_response = result["choices"][0]["message"]["content"].strip()
            print(f"\n✅ LLM 响应: {llm_response}")
            
            # 解析响应
            if llm_response.upper() == "NONE" or not llm_response:
                print(f"\n❌ LLM 无法推断子图ID")
                return None
            
            # 清理响应
            subgraph_id = llm_response.strip().strip('"').strip("'").upper()
            
            # 验证格式
            if len(subgraph_id) >= 4 and len(subgraph_id) <= 8:
                print(f"\n🎯 推断结果: {subgraph_id}")
                print(f"✅ 格式验证通过")
                return subgraph_id
            else:
                print(f"\n⚠️  LLM 返回的子图ID格式异常: {subgraph_id}")
                return None
    
    except httpx.TimeoutException as e:
        print(f"\n❌ LLM API 请求超时: {e}")
        return None
    except httpx.HTTPStatusError as e:
        print(f"\n❌ LLM API 返回错误状态: {e.response.status_code}")
        print(f"   响应内容: {e.response.text}")
        return None
    except Exception as e:
        print(f"\n❌ LLM 推断失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_multiple_scenarios():
    """测试多个场景"""
    print("\n" + "=" * 60)
    print("测试多个场景")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "场景1：PH2-04 后续修改",
            "history": [
                "user: PH2-04 的价格怎么算的？",
                "assistant: PH2-04 的总成本是 125.50 元"
            ],
            "message": "材质改为 Cr12mov",
            "expected": "PH2-04"
        },
        {
            "name": "场景2：UP01 后续查询",
            "history": [
                "user: UP01 的材料费是多少？",
                "assistant: UP01 的材料费是 45.00 元"
            ],
            "message": "那线割费呢？",
            "expected": "UP01"
        },
        {
            "name": "场景3：无历史",
            "history": [],
            "message": "材质改为 718",
            "expected": "NONE"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{'=' * 60}")
        print(f"📋 {scenario['name']}")
        print(f"{'=' * 60}")
        print(f"历史: {scenario['history']}")
        print(f"消息: {scenario['message']}")
        print(f"期望: {scenario['expected']}")
        
        # 这里可以调用实际的推断函数
        # result = await infer_subgraph(scenario['history'], scenario['message'])
        # print(f"结果: {result}")


if __name__ == "__main__":
    print("\n🧪 开始测试 LLM 子图推断功能\n")
    
    # 测试单个场景
    result = asyncio.run(test_llm_inference())
    
    if result:
        print(f"\n🎉 测试成功！推断出子图: {result}")
    else:
        print(f"\n⚠️  测试失败，无法推断子图")
    
    # 测试多个场景（仅显示，不实际调用）
    asyncio.run(test_multiple_scenarios())
