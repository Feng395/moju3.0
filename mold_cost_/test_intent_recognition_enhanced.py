"""
测试增强后的意图识别

测试场景：
1. 验证性问题识别
2. 数据修改识别
3. 上下文推断
4. 置信度调整
"""
import asyncio
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 🆕 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

from agents.intent_recognizer import IntentRecognizer
from agents.intent_types import IntentType


async def test_verification_questions():
    """测试验证性问题识别"""
    print("\n" + "=" * 60)
    print("测试 1：验证性问题识别")
    print("=" * 60)
    
    recognizer = IntentRecognizer(use_llm=True, use_chat_history=False)
    
    test_cases = [
        {
            "message": "大水磨长条加工这道工序，耗时 1.5 小时，按 60元/小时计算，费用为 90.00 元 这样对吗？",
            "expected": IntentType.QUERY_DETAILS,
            "description": "验证计算结果"
        },
        {
            "message": "B2-03大水磨长条费用 耗时 1.5 小时，按 60元/小时，费用为 90.00 元 这样对吗？",
            "expected": IntentType.QUERY_DETAILS,
            "description": "验证特定子图的计算"
        },
        {
            "message": "UP01 的材料费是 500 元，正确吗？",
            "expected": IntentType.QUERY_DETAILS,
            "description": "验证材料费"
        },
        {
            "message": "重新计算 UP01 的价格",
            "expected": IntentType.PRICE_CALCULATION,
            "description": "明确要求重新计算"
        }
    ]
    
    context = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模"},
            {"subgraph_id": "B2-03", "part_name": "大水磨长条"}
        ]
    }
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test['description']}")
        print(f"输入: {test['message']}")
        
        result = await recognizer.recognize(test["message"], context)
        
        print(f"识别结果: {result.intent_type}")
        print(f"置信度: {result.confidence}")
        print(f"参数: {result.parameters}")
        
        if result.intent_type == test["expected"]:
            print("✅ 通过")
        else:
            print(f"❌ 失败 - 期望: {test['expected']}, 实际: {result.intent_type}")
    
    await recognizer.close()


async def test_data_modification():
    """测试数据修改识别"""
    print("\n" + "=" * 60)
    print("测试 2：数据修改识别")
    print("=" * 60)
    
    recognizer = IntentRecognizer(use_llm=True, use_chat_history=False)
    
    test_cases = [
        {
            "message": "将 UP01 的材质改为 718",
            "expected": IntentType.DATA_MODIFICATION,
            "description": "修改材质"
        },
        {
            "message": "UP01 的宽度设置为 200",
            "expected": IntentType.DATA_MODIFICATION,
            "description": "设置宽度"
        },
        {
            "message": "把 B2-03 的长度改成 150",
            "expected": IntentType.DATA_MODIFICATION,
            "description": "修改长度"
        },
        {
            "message": "UP01 的材质是什么？",
            "expected": IntentType.QUERY_DETAILS,
            "description": "查询材质（不是修改）"
        }
    ]
    
    context = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模"},
            {"subgraph_id": "B2-03", "part_name": "大水磨长条"}
        ]
    }
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test['description']}")
        print(f"输入: {test['message']}")
        
        result = await recognizer.recognize(test["message"], context)
        
        print(f"识别结果: {result.intent_type}")
        print(f"置信度: {result.confidence}")
        print(f"参数: {result.parameters}")
        
        if result.intent_type == test["expected"]:
            print("✅ 通过")
        else:
            print(f"❌ 失败 - 期望: {test['expected']}, 实际: {result.intent_type}")
    
    await recognizer.close()


async def test_context_inference():
    """测试上下文推断（需要数据库）"""
    print("\n" + "=" * 60)
    print("测试 3：上下文推断（模拟）")
    print("=" * 60)
    
    recognizer = IntentRecognizer(use_llm=True, use_chat_history=True)
    
    # 模拟聊天历史
    chat_history = [
        {"role": "user", "content": "UP01 的价格是多少？"},
        {"role": "assistant", "content": "UP01 的总价是 1500 元"},
        {"role": "user", "content": "那材料费呢？"}
    ]
    
    context = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模"},
            {"subgraph_id": "LP-02", "part_name": "下模"}
        ]
    }
    
    print("\n历史对话:")
    for msg in chat_history:
        role_name = "用户" if msg["role"] == "user" else "助手"
        print(f"  {role_name}: {msg['content']}")
    
    print("\n当前输入: 那材料费呢？")
    print("期望: 识别为 QUERY_DETAILS，subgraph_id = UP01（从历史推断）")
    
    # 注意：这里无法真正测试，因为需要数据库连接
    # 实际测试需要通过 API 端点进行
    print("\n⚠️  此测试需要数据库连接，请通过 API 端点测试")
    
    await recognizer.close()


async def test_rules_fallback():
    """测试规则识别（Fallback）"""
    print("\n" + "=" * 60)
    print("测试 4：规则识别（Fallback）")
    print("=" * 60)
    
    # 禁用 LLM，测试规则识别
    recognizer = IntentRecognizer(use_llm=False, use_chat_history=False)
    
    test_cases = [
        {
            "message": "费用为 90 元，这样对吗？",
            "expected": IntentType.QUERY_DETAILS,
            "description": "验证性问题（规则识别）"
        },
        {
            "message": "重新识别特征",
            "expected": IntentType.FEATURE_RECOGNITION,
            "description": "特征识别"
        },
        {
            "message": "重新计算价格",
            "expected": IntentType.PRICE_CALCULATION,
            "description": "价格计算"
        },
        {
            "message": "修改材质为 718",
            "expected": IntentType.DATA_MODIFICATION,
            "description": "数据修改"
        }
    ]
    
    context = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模"}
        ]
    }
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test['description']}")
        print(f"输入: {test['message']}")
        
        result = await recognizer.recognize(test["message"], context)
        
        print(f"识别结果: {result.intent_type}")
        print(f"置信度: {result.confidence}")
        
        if result.intent_type == test["expected"]:
            print("✅ 通过")
        else:
            print(f"❌ 失败 - 期望: {test['expected']}, 实际: {result.intent_type}")
    
    await recognizer.close()


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("意图识别增强测试")
    print("=" * 60)
    
    # 检查环境变量
    use_llm = os.getenv("USE_LLM", "false").lower() == "true"
    openai_base_url = os.getenv("OPENAI_BASE_URL", "Not set")
    openai_model = os.getenv("OPENAI_MODEL", "Not set")
    use_chat_history = os.getenv("USE_CHAT_HISTORY", "true").lower() == "true"
    
    print(f"\n环境配置:")
    print(f"  USE_LLM: {use_llm}")
    print(f"  USE_CHAT_HISTORY: {use_chat_history}")
    print(f"  OPENAI_BASE_URL: {openai_base_url}")
    print(f"  OPENAI_MODEL: {openai_model}")
    
    if not use_llm:
        print("\n⚠️  警告: USE_LLM=false，只会测试规则识别")
        print("  建议设置 USE_LLM=true 以测试完整功能")
    elif openai_base_url == "Not set":
        print("\n⚠️  警告: OPENAI_BASE_URL 未设置")
        print("  请在 .env 文件中设置 OPENAI_BASE_URL")
    else:
        print(f"\n✅ LLM 配置正常，将测试完整功能")
        print(f"  API 地址: {openai_base_url}")
        print(f"  模型: {openai_model}")
    
    try:
        # 测试 1：验证性问题
        await test_verification_questions()
        
        # 测试 2：数据修改
        await test_data_modification()
        
        # 测试 3：上下文推断（模拟）
        await test_context_inference()
        
        # 测试 4：规则识别
        await test_rules_fallback()
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        print("\n建议:")
        print("1. 通过 API 端点测试真实场景")
        print("2. 检查日志文件查看详细识别过程")
        print("3. 测试多轮对话的上下文推断")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
