"""
测试实体提取功能
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser


async def test_entity_extraction():
    """测试实体提取"""
    parser = NLPParser(use_llm=False)  # 不使用 LLM，只测试规则
    
    test_cases = [
        "修改LP-02长度为100",
        "把LP-02的长度改为100",
        "将LP-02的长度设置为100",
        "LP-02长度改成100",
        "修改P001材料为45钢",
        "把零件01的宽度改为50"
    ]
    
    print("=" * 60)
    print("实体提取测试")
    print("=" * 60)
    
    for text in test_cases:
        print(f"\n输入: {text}")
        result = await parser._extract_entities_from_text(text)
        if result:
            print(f"✅ 成功: {result}")
        else:
            print(f"❌ 失败: 未能提取实体")
    
    await parser.close()


if __name__ == "__main__":
    asyncio.run(test_entity_extraction())
