"""
阶段3 快速测试
负责人：人员B2

功能：快速验证 NLP Parser 是否正常工作

使用方法：
    python examples/test_stage3_quick.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.nlp_parser import NLPParser
from dotenv import load_dotenv

load_dotenv()


async def main():
    """快速测试"""
    print("=" * 60)
    print("阶段3 快速测试 - NLP Parser")
    print("=" * 60)
    
    # 测试数据
    context = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模板"},
            {"subgraph_id": "UP02", "part_name": "下模板"}
        ],
        "features": [],
        "price_snapshots": [],
        "process_snapshots": []
    }
    
    # 测试1: 规则解析
    print("\n📋 测试1: 规则解析")
    print("-" * 60)
    parser = NLPParser(use_llm=False)
    
    text = "将 UP01 的材质改为 718"
    print(f"输入: {text}")
    
    changes = await parser.parse(text, context)
    if changes:
        print(f"✅ 成功: {len(changes)} 个修改")
        for c in changes:
            print(f"   - {c['table']}.{c['id']}.{c['field']} = {c['value']}")
    else:
        print("❌ 失败")
    
    await parser.close()
    
    # 测试2: LLM 解析
    print("\n🤖 测试2: LLM 解析")
    print("-" * 60)
    parser = NLPParser(use_llm=True)
    
    text = "请把上模板的材料换成 718"
    print(f"输入: {text}")
    
    try:
        changes = await parser.parse(text, context)
        if changes:
            print(f"✅ 成功: {len(changes)} 个修改")
            for c in changes:
                print(f"   - {c['table']}.{c['id']}.{c['field']} = {c['value']}")
        else:
            print("⚠️  LLM 返回空结果（可能降级到规则解析）")
    except Exception as e:
        print(f"⚠️  LLM 调用失败: {e}")
        print("   （这是正常的，会自动降级到规则解析）")
    
    await parser.close()
    
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
