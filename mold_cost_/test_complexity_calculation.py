"""
测试复杂度计算和方案3实现

测试场景：
1. 简单句式（复杂度 < 5）→ 应该使用正则
2. 复杂句式（复杂度 >= 5）→ 应该使用 LLM
"""
import asyncio
import logging
from agents.nlp_parser import NLPParser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_complexity_calculation():
    """测试复杂度计算"""
    
    parser = NLPParser(use_llm=True)
    
    # 测试用例
    test_cases = [
        # 简单句式（应该 < 5）
        {
            "text": "UP01工艺改成慢丝割一修一",
            "expected_complexity": "< 5",
            "expected_method": "正则"
        },
        {
            "text": "LP-02的工艺改为慢丝割一修三",
            "expected_complexity": "< 5",
            "expected_method": "正则"
        },
        {
            "text": "下模板类的零件工艺改成慢丝割一修一",
            "expected_complexity": "< 5",
            "expected_method": "正则"
        },
        {
            "text": "全部工艺改成中丝割一修一",
            "expected_complexity": "< 5",
            "expected_method": "正则"
        },
        
        # 复杂句式（应该 >= 5）
        {
            "text": "把上夹板类的工艺改为中丝割一修一，把冲头类和上脱板类和下模板类和拼料板类和下垫板类的工艺改为中丝割一修一，",
            "expected_complexity": ">= 5",
            "expected_method": "LLM",
            "reason": "多个'把'字(2个) + 多个逗号(2个) + 多个'和'字(4个) + 多个'类'字(6个) + 长度>40"
        },
        {
            "text": "DIE-04和LP-02和PH2-04的工艺改成慢丝割一修二",
            "expected_complexity": "< 5",
            "expected_method": "正则",
            "reason": "只有2个'和'字，不超过阈值"
        },
        {
            "text": "这几个零件DIE-04、DIE-03、PH2-04的工艺改为慢丝割一修三",
            "expected_complexity": ">= 5",
            "expected_method": "LLM",
            "reason": "多个逗号(2个) + 长度>40"
        },
        {
            "text": "把上夹板类改为中丝，把冲头类改为快丝",
            "expected_complexity": ">= 5",
            "expected_method": "LLM",
            "reason": "多个'把'字(2个) + 多个逗号(1个)"
        },
        {
            "text": "上夹板类和冲头类和上脱板类和下模板类的工艺改为中丝割一修一",
            "expected_complexity": ">= 5",
            "expected_method": "LLM",
            "reason": "多个'和'字(3个) + 多个'类'字(4个) + 长度>40"
        },
        # 🆕 筛选条件测试
        {
            "text": "UB开头的工艺改为慢丝割一修三",
            "expected_complexity": ">= 5",
            "expected_method": "LLM",
            "reason": "包含筛选条件关键词'开头'"
        },
        {
            "text": "以UP结尾的零件工艺改为快丝割一刀",
            "expected_complexity": ">= 5",
            "expected_method": "LLM",
            "reason": "包含筛选条件关键词'结尾'和'的零件'"
        },
        {
            "text": "包含DIE的零件改为中丝割一修一",
            "expected_complexity": ">= 5",
            "expected_method": "LLM",
            "reason": "包含筛选条件关键词'包含'和'的零件'"
        }
    ]
    
    print("\n" + "="*80)
    print("测试复杂度计算")
    print("="*80 + "\n")
    
    for i, case in enumerate(test_cases, 1):
        text = case["text"]
        expected = case["expected_complexity"]
        method = case["expected_method"]
        reason = case.get("reason", "")
        
        # 计算复杂度
        complexity = parser._calculate_complexity(text)
        
        # 判断是否符合预期
        if expected == "< 5":
            passed = complexity < 5
        else:
            passed = complexity >= 5
        
        # 输出结果
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"测试 {i}: {status}")
        print(f"  输入: {text}")
        print(f"  复杂度: {complexity} (预期: {expected})")
        print(f"  应使用: {method}")
        if reason:
            print(f"  原因: {reason}")
        print()
    
    await parser.close()


async def test_process_modification_routing():
    """测试工艺修改的路由逻辑"""
    
    parser = NLPParser(use_llm=True)
    
    print("\n" + "="*80)
    print("测试工艺修改路由逻辑")
    print("="*80 + "\n")
    
    # 简单句式
    simple_text = "UP01工艺改成慢丝割一修一"
    print(f"测试简单句式: {simple_text}")
    complexity = parser._calculate_complexity(simple_text)
    print(f"  复杂度: {complexity}")
    print(f"  应使用: {'正则' if complexity < 5 else 'LLM'}")
    print()
    
    # 复杂句式
    complex_text = "把上夹板类的工艺改为中丝割一修一，把冲头类和上脱板类的工艺改为中丝割一修一"
    print(f"测试复杂句式: {complex_text}")
    complexity = parser._calculate_complexity(complex_text)
    print(f"  复杂度: {complexity}")
    print(f"  应使用: {'正则' if complexity < 5 else 'LLM'}")
    print()
    
    # 🆕 筛选条件句式
    filter_text = "UB开头的工艺改为慢丝割一修三"
    print(f"测试筛选条件句式: {filter_text}")
    complexity = parser._calculate_complexity(filter_text)
    print(f"  复杂度: {complexity}")
    print(f"  应使用: {'正则' if complexity < 5 else 'LLM'}")
    print()
    
    await parser.close()


async def test_edge_cases():
    """测试边界情况"""
    
    parser = NLPParser(use_llm=True)
    
    print("\n" + "="*80)
    print("测试边界情况")
    print("="*80 + "\n")
    
    edge_cases = [
        {
            "text": "把上夹板类的工艺改为中丝割一修一",
            "description": "单个'把'字 + 单个'类'字 + 长度<40",
            "expected": "< 5"
        },
        {
            "text": "上夹板类和冲头类的工艺改为中丝割一修一",
            "description": "单个'和'字 + 两个'类'字 + 长度<40",
            "expected": "< 5"
        },
        {
            "text": "上夹板类和冲头类和上脱板类的工艺改为中丝割一修一",
            "description": "两个'和'字 + 三个'类'字 + 长度<40",
            "expected": "< 5"
        },
        {
            "text": "上夹板类和冲头类和上脱板类和下模板类的工艺改为中丝割一修一",
            "description": "三个'和'字 + 四个'类'字 + 长度>40",
            "expected": ">= 5"
        },
        {
            "text": "把A改为X，把B改为Y",
            "description": "两个'把'字 + 一个逗号",
            "expected": ">= 5"
        }
    ]
    
    for i, case in enumerate(edge_cases, 1):
        text = case["text"]
        desc = case["description"]
        expected = case["expected"]
        
        complexity = parser._calculate_complexity(text)
        
        if expected == "< 5":
            passed = complexity < 5
        else:
            passed = complexity >= 5
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"边界测试 {i}: {status}")
        print(f"  输入: {text}")
        print(f"  描述: {desc}")
        print(f"  复杂度: {complexity} (预期: {expected})")
        print()
    
    await parser.close()


async def main():
    """主函数"""
    
    print("\n" + "="*80)
    print("方案3实现测试")
    print("="*80)
    
    # 测试1：复杂度计算
    await test_complexity_calculation()
    
    # 测试2：路由逻辑
    await test_process_modification_routing()
    
    # 测试3：边界情况
    await test_edge_cases()
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
