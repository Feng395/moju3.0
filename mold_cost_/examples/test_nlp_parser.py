"""
NLP Parser 测试示例
负责人：人员B2

功能：
1. 测试规则解析
2. 测试 LLM 解析
3. 测试 Fallback 机制

使用方法：
    python examples/test_nlp_parser.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.nlp_parser import NLPParser
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


# 测试数据
SAMPLE_CONTEXT = {
    "features": [
        {
            "feature_id": 1,
            "subgraph_id": "UP01",
            "length_mm": 100.0,
            "width_mm": 50.0,
            "thickness_mm": 10.0,
            "material": "P20"
        }
    ],
    "subgraphs": [
        {
            "subgraph_id": "UP01",
            "part_name": "上模板",
            "weight_kg": 5.5,
            "total_cost": 1000.0,
            "process_description": "铣削加工"
        },
        {
            "subgraph_id": "UP02",
            "part_name": "下模板",
            "weight_kg": 6.0,
            "total_cost": 1200.0,
            "process_description": "线切割"
        },
        {
            "subgraph_id": "DOWN01",
            "part_name": "侧板",
            "weight_kg": 3.2,
            "total_cost": 800.0,
            "process_description": "数控加工"
        }
    ],
    "price_snapshots": [],
    "process_snapshots": []
}


async def test_rule_parsing():
    """测试规则解析"""
    print("\n" + "=" * 60)
    print("📋 测试规则解析（不使用 LLM）")
    print("=" * 60)
    
    parser = NLPParser(use_llm=False)
    
    test_cases = [
        "将 UP01 的材质改为 718",
        "修改 UP02 的重量为 7.5kg",
        "把 DOWN01 的工艺说明设置为精密铣削",
        "UP01 的总成本改成 1500",
        "将 UP01 的材质改为 718，把 UP02 的重量设置为 7kg"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {text}")
        print("-" * 60)
        
        changes = await parser.parse(text, SAMPLE_CONTEXT)
        
        if changes:
            print(f"✅ 解析成功，找到 {len(changes)} 个修改:")
            for j, change in enumerate(changes, 1):
                print(f"  {j}. 表: {change['table']}")
                print(f"     ID: {change['id']}")
                print(f"     字段: {change['field']}")
                print(f"     值: {change['value']}")
        else:
            print("❌ 解析失败，未找到修改")
    
    await parser.close()


async def test_llm_parsing():
    """测试 LLM 解析"""
    print("\n" + "=" * 60)
    print("🤖 测试 LLM 解析（使用本地 Qwen）")
    print("=" * 60)
    
    parser = NLPParser(use_llm=True)
    
    test_cases = [
        "将 UP01 的材质改为 718",
        "请把上模板的材料换成 718",
        "下模板的重量改为 7.5 公斤",
        "把侧板的加工说明改成精密铣削加工",
        "将上模板的材质改为 718，下模板的重量改为 7.5kg"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {text}")
        print("-" * 60)
        
        try:
            changes = await parser.parse(text, SAMPLE_CONTEXT)
            
            if changes:
                print(f"✅ 解析成功，找到 {len(changes)} 个修改:")
                for j, change in enumerate(changes, 1):
                    print(f"  {j}. 表: {change['table']}")
                    print(f"     ID: {change['id']}")
                    print(f"     字段: {change['field']}")
                    print(f"     值: {change['value']}")
            else:
                print("❌ 解析失败，未找到修改")
        
        except Exception as e:
            print(f"❌ 解析异常: {e}")
    
    await parser.close()


async def test_interactive():
    """交互式测试"""
    print("\n" + "=" * 60)
    print("💬 交互式测试（输入 'quit' 退出）")
    print("=" * 60)
    
    parser = NLPParser(use_llm=True)
    
    print("\n当前数据:")
    print("  - UP01: 上模板 (材质: P20, 重量: 5.5kg, 成本: 1000)")
    print("  - UP02: 下模板 (重量: 6.0kg, 成本: 1200)")
    print("  - DOWN01: 侧板 (重量: 3.2kg, 成本: 800)")
    
    while True:
        print("\n" + "-" * 60)
        text = input("请输入修改指令: ").strip()
        
        if text.lower() in ['quit', 'exit', 'q']:
            break
        
        if not text:
            continue
        
        try:
            changes = await parser.parse(text, SAMPLE_CONTEXT)
            
            if changes:
                print(f"\n✅ 解析成功，找到 {len(changes)} 个修改:")
                for i, change in enumerate(changes, 1):
                    print(f"  {i}. {change['table']}.{change['id']}.{change['field']} = {change['value']}")
            else:
                print("\n❌ 解析失败，未找到修改")
        
        except Exception as e:
            print(f"\n❌ 解析异常: {e}")
    
    await parser.close()
    print("\n👋 再见！")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NLP Parser 测试")
    parser.add_argument(
        "--mode",
        choices=["rule", "llm", "interactive", "all"],
        default="all",
        help="测试模式"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("NLP Parser 测试")
    print("=" * 60)
    
    if args.mode in ["rule", "all"]:
        await test_rule_parsing()
    
    if args.mode in ["llm", "all"]:
        await test_llm_parsing()
    
    if args.mode == "interactive":
        await test_interactive()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 测试已取消")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
