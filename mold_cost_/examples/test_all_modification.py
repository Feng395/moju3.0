"""
测试"全部"修改功能

验证：
1. LLM 能够识别"全部"、"所有"等关键词
2. 系统能够将 id="ALL" 展开为所有记录
3. 批量修改所有记录的材质
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser


async def test_all_modification():
    """测试全部修改功能"""
    print("=" * 60)
    print("测试'全部'修改功能")
    print("=" * 60)
    
    # 初始化 NLP Parser（不使用 LLM，只测试展开逻辑）
    parser = NLPParser(use_llm=False)
    
    # 模拟上下文数据（4个零件）
    context = {
        "features": [
            {
                "feature_id": 1001,
                "subgraph_id": "sg_001",
                "material": "45钢",
                "length_mm": 100
            },
            {
                "feature_id": 1002,
                "subgraph_id": "sg_002",
                "material": "718",
                "length_mm": 120
            },
            {
                "feature_id": 1003,
                "subgraph_id": "sg_003",
                "material": "P20",
                "length_mm": 80
            },
            {
                "feature_id": 1004,
                "subgraph_id": "sg_004",
                "material": "S136",
                "length_mm": 90
            }
        ],
        "subgraphs": [
            {"subgraph_id": "sg_001", "part_name": "上夹板", "part_code": "LP-01"},
            {"subgraph_id": "sg_002", "part_name": "下夹板", "part_code": "LP-02"},
            {"subgraph_id": "sg_003", "part_name": "导柱", "part_code": "PH-01"},
            {"subgraph_id": "sg_004", "part_name": "导套", "part_code": "PH-02"}
        ],
        "price_snapshots": []
    }
    
    print("\n" + "=" * 60)
    print("测试 1: 展开 ALL 修改（features 表）")
    print("=" * 60)
    
    # 模拟 LLM 返回 id="ALL"
    all_changes = [
        {
            "table": "features",
            "id": "ALL",
            "field": "material",
            "value": "45#",
            "original_text": "全部材质修改为45#"
        }
    ]
    
    print(f"\n📋 输入:")
    print(f"  - table: {all_changes[0]['table']}")
    print(f"  - id: {all_changes[0]['id']} ⭐ 特殊标识")
    print(f"  - field: {all_changes[0]['field']}")
    print(f"  - value: {all_changes[0]['value']}")
    
    # 验证并展开
    validated = parser._validate_changes(all_changes, context)
    
    print(f"\n✅ 输出（已展开）:")
    print(f"  - 修改数量: {len(validated)}")
    
    if len(validated) == 4:
        print("\n✅ 测试通过：ALL 已展开为 4 条记录")
        for i, change in enumerate(validated, 1):
            print(f"  {i}. feature_id={change['id']}, material={change['value']}")
    else:
        print(f"\n❌ 测试失败：期望 4 条记录，实际 {len(validated)} 条")
    
    print("\n" + "=" * 60)
    print("测试 2: 展开 ALL 修改（subgraphs 表）")
    print("=" * 60)
    
    all_subgraph_changes = [
        {
            "table": "subgraphs",
            "id": "ALL",
            "field": "part_name",
            "value": "测试零件",
            "original_text": "全部零件名称改为测试零件"
        }
    ]
    
    print(f"\n📋 输入:")
    print(f"  - table: {all_subgraph_changes[0]['table']}")
    print(f"  - id: {all_subgraph_changes[0]['id']} ⭐ 特殊标识")
    print(f"  - field: {all_subgraph_changes[0]['field']}")
    
    validated = parser._validate_changes(all_subgraph_changes, context)
    
    print(f"\n✅ 输出（已展开）:")
    print(f"  - 修改数量: {len(validated)}")
    
    if len(validated) == 4:
        print("\n✅ 测试通过：ALL 已展开为 4 条记录")
        for i, change in enumerate(validated, 1):
            print(f"  {i}. subgraph_id={change['id']}, part_name={change['value']}")
    else:
        print(f"\n❌ 测试失败：期望 4 条记录，实际 {len(validated)} 条")
    
    print("\n" + "=" * 60)
    print("测试 3: 混合修改（ALL + 具体ID）")
    print("=" * 60)
    
    mixed_changes = [
        {
            "table": "features",
            "id": "ALL",
            "field": "material",
            "value": "45#"
        },
        {
            "table": "features",
            "id": "1001",
            "field": "length_mm",
            "value": "150"
        }
    ]
    
    print(f"\n📋 输入:")
    print(f"  1. ALL 修改 material")
    print(f"  2. 单个修改 length_mm")
    
    validated = parser._validate_changes(mixed_changes, context)
    
    print(f"\n✅ 输出:")
    print(f"  - 修改数量: {len(validated)}")
    
    if len(validated) == 5:  # 4个 material + 1个 length_mm
        print("\n✅ 测试通过：混合修改正确处理")
        material_count = sum(1 for c in validated if c['field'] == 'material')
        length_count = sum(1 for c in validated if c['field'] == 'length_mm')
        print(f"  - material 修改: {material_count} 条")
        print(f"  - length_mm 修改: {length_count} 条")
    else:
        print(f"\n❌ 测试失败：期望 5 条记录，实际 {len(validated)} 条")
    
    print("\n" + "=" * 60)
    print("测试 4: 自动修正 + ALL 展开")
    print("=" * 60)
    
    # 模拟 LLM 错误地将 material 映射到 subgraphs，且使用 ALL
    wrong_all_changes = [
        {
            "table": "subgraphs",  # ❌ 错误
            "id": "ALL",
            "field": "material",
            "value": "45#"
        }
    ]
    
    print(f"\n📋 输入（错误映射）:")
    print(f"  - table: {wrong_all_changes[0]['table']} ❌")
    print(f"  - id: ALL")
    print(f"  - field: material")
    
    validated = parser._validate_changes(wrong_all_changes, context)
    
    print(f"\n✅ 输出:")
    print(f"  - 修改数量: {len(validated)}")
    
    if validated and validated[0]['table'] == 'features':
        print(f"  - table: features ✅ 已自动修正")
        if len(validated) == 4:
            print("\n✅ 测试通过：自动修正 + ALL 展开都正常工作")
        else:
            print(f"\n⚠️  部分通过：表名已修正，但展开数量不对（期望4，实际{len(validated)}）")
    else:
        print("\n❌ 测试失败：表名未修正或展开失败")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    
    await parser.close()


if __name__ == "__main__":
    asyncio.run(test_all_modification())
