"""
测试 LLM 修复 - 验证 User-Agent 修复是否生效
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def test_intent_recognizer():
    """测试 IntentRecognizer 的 LLM 调用"""
    print("=" * 60)
    print("测试 1: IntentRecognizer LLM 调用")
    print("=" * 60)
    
    from agents.intent_recognizer import IntentRecognizer
    
    recognizer = IntentRecognizer(use_llm=True)
    
    # 测试数据
    context = {
        "subgraphs": [
            {"subgraph_id": "UP01", "material": "P20", "weight": 5.0},
            {"subgraph_id": "UP02", "material": "718", "weight": 3.0}
        ]
    }
    
    # 测试消息
    message = "将 UP01 的材质改为 718"
    
    print(f"📝 测试消息: {message}")
    print("🔍 调用 LLM 识别意图...")
    
    try:
        result = await recognizer.recognize(message, context)
        print(f"✅ 识别成功!")
        print(f"   意图类型: {result.intent_type}")
        print(f"   置信度: {result.confidence}")
        print(f"   参数: {result.parameters}")
    except Exception as e:
        print(f"❌ 识别失败: {e}")
    finally:
        await recognizer.close()
    
    print()


async def test_general_chat_handler():
    """测试 GeneralChatHandler 的 LLM 调用"""
    print("=" * 60)
    print("测试 2: GeneralChatHandler LLM 调用")
    print("=" * 60)
    
    from agents.action_handlers.general_chat_handler import GeneralChatHandler
    from agents.intent_types import IntentResult, IntentType
    
    handler = GeneralChatHandler()
    
    # 测试数据
    context = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模", "material": "P20"},
            {"subgraph_id": "UP02", "part_name": "下模", "material": "718"}
        ]
    }
    
    intent_result = IntentResult(
        intent_type=IntentType.GENERAL_CHAT,
        confidence=0.9,
        raw_message="你好，这个系统可以做什么？"
    )
    
    print(f"📝 测试消息: {intent_result.raw_message}")
    print("🔍 调用 LLM 生成回复...")
    
    try:
        result = await handler.handle(intent_result, "test-job-id", context, None)
        print(f"✅ 生成成功!")
        print(f"   状态: {result.status}")
        print(f"   回复: {result.message[:100]}...")
    except Exception as e:
        print(f"❌ 生成失败: {e}")
    
    print()


async def test_interaction_agent():
    """测试 InteractionAgent 的 LLM 调用"""
    print("=" * 60)
    print("测试 3: InteractionAgent LLM 调用")
    print("=" * 60)
    
    from agents.interaction_agent import InteractionAgent
    
    agent = InteractionAgent()
    
    # 测试数据
    context_data = {
        "subgraphs": [
            {"subgraph_id": "UP01", "material": "P20", "weight": 5.0}
        ]
    }
    
    messages = [
        {"role": "system", "content": "你是一个测试助手"},
        {"role": "user", "content": "你好"}
    ]
    
    print("📝 测试消息: 你好")
    print("🔍 调用 LLM...")
    
    try:
        response = await agent._call_llm(messages)
        print(f"✅ 调用成功!")
        print(f"   回复: {response[:100]}...")
    except Exception as e:
        print(f"❌ 调用失败: {e}")
    
    print()


async def main():
    """主函数"""
    print("=" * 60)
    print("LLM 修复验证测试")
    print("=" * 60)
    print("测试所有使用 LLM 的组件是否能正常工作")
    print()
    
    # 测试 1: IntentRecognizer
    await test_intent_recognizer()
    
    # 测试 2: GeneralChatHandler
    await test_general_chat_handler()
    
    # 测试 3: InteractionAgent
    await test_interaction_agent()
    
    print("=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
