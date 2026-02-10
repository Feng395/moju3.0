"""
测试材质字段映射修复

验证：
1. LLM 解析时正确识别 material 字段应该在 features 表
2. 自动修正逻辑能够纠正错误的表映射
3. ID 映射能够正确处理 part_code 和 part_name
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser


async def test_material_field_mapping():
    """测试材质字段映射"""
    print("=" * 60)
    print("测试材质字段映射修复")
    print("=" * 60)
    
    # 初始化 NLP Parser（不使用 LLM，只测试验证逻辑）
    parser = NLPParser(use_llm=False)
    
    # 模拟上下文数据
    context = {
        "features": [
            {
                "feature_id": 1001,
                "subgraph_id": "fd21e3a4-8223-425a-a29a-4327457fa311_PH2-04",
                "material": "45钢",
                "length_mm": 100,
                "width_mm": 50,
                "thickness_mm": 20
            }
        ],
        "subgraphs": [
            {
                "subgraph_id": "fd21e3a4-8223-425a-a29a-4327457fa311_PH2-04",
                "part_name": "上夹板",
                "part_code": "PH2-04",
                "wire_process": "fast_and_one",
                "wire_process_note": "快丝割一刀"
            }
        ],
        "price_snapshots": []
    }
    
    print("\n" + "=" * 60)
    print("测试 1: 自动修正错误的表映射（material 从 subgraphs 改为 features）")
    print("=" * 60)
    
    # 模拟 LLM 错误地将 material 映射到 subgraphs 表
    wrong_changes = [
        {
            "table": "subgraphs",  # ❌ 错误：应该是 features
            "id": "PH2-04",
            "field": "material",
            "value": "45#",
            "original_text": "将零件PH2-04的材质设为45#"
        }
    ]
    
    print(f"\n📋 输入（错误映射）:")
    print(f"  - table: {wrong_changes[0]['table']} ❌")
    print(f"  - field: {wrong_changes[0]['field']}")
    print(f"  - id: {wrong_changes[0]['id']}")
    print(f"  - value: {wrong_changes[0]['value']}")
    
    # 验证并自动修正
    validated = parser._validate_changes(wrong_changes, context)
    
    if validated:
        print(f"\n✅ 输出（自动修正）:")
        print(f"  - table: {validated[0]['table']} ✅")
        print(f"  - field: {validated[0]['field']}")
        print(f"  - id: {validated[0]['id']}")
        print(f"  - value: {validated[0]['value']}")
        
        if validated[0]['table'] == 'features':
            print("\n✅ 测试通过：material 字段已自动修正到 features 表")
        else:
            print(f"\n❌ 测试失败：表名仍然是 {validated[0]['table']}")
    else:
        print("\n❌ 测试失败：验证返回空列表")
    
    print("\n" + "=" * 60)
    print("测试 2: 正确的字段映射（features 表字段）")
    print("=" * 60)
    
    correct_changes = [
        {
            "table": "features",
            "id": "PH2-04",
            "field": "length_mm",
            "value": "120",
            "original_text": "PH2-04长度改为120"
        }
    ]
    
    print(f"\n📋 输入:")
    print(f"  - table: {correct_changes[0]['table']}")
    print(f"  - field: {correct_changes[0]['field']}")
    
    validated = parser._validate_changes(correct_changes, context)
    
    if validated and validated[0]['table'] == 'features':
        print("\n✅ 测试通过：features 表字段保持不变")
    else:
        print("\n❌ 测试失败")
    
    print("\n" + "=" * 60)
    print("测试 3: 工艺字段映射（subgraphs 表字段）")
    print("=" * 60)
    
    process_changes = [
        {
            "table": "subgraphs",
            "id": "PH2-04",
            "field": "wire_process",
            "value": "slow_and_one",
            "original_text": "PH2-04工艺改为慢丝割一刀"
        }
    ]
    
    print(f"\n📋 输入:")
    print(f"  - table: {process_changes[0]['table']}")
    print(f"  - field: {process_changes[0]['field']}")
    
    validated = parser._validate_changes(process_changes, context)
    
    if validated and validated[0]['table'] == 'subgraphs':
        print("\n✅ 测试通过：subgraphs 表字段保持不变")
    else:
        print("\n❌ 测试失败")
    
    print("\n" + "=" * 60)
    print("测试 4: 批量测试所有字段映射")
    print("=" * 60)
    
    field_mappings = {
        "material": "features",
        "length_mm": "features",
        "width_mm": "features",
        "thickness_mm": "features",
        "quantity": "features",
        "wire_process": "subgraphs",
        "wire_process_note": "subgraphs",
        "part_name": "subgraphs",
        "part_code": "subgraphs",
        "price": "price_snapshots"
    }
    
    all_passed = True
    
    for field, expected_table in field_mappings.items():
        # 故意使用错误的表名
        wrong_table = "subgraphs" if expected_table != "subgraphs" else "features"
        
        test_change = [{
            "table": wrong_table,
            "id": "PH2-04",
            "field": field,
            "value": "test_value"
        }]
        
        validated = parser._validate_changes(test_change, context)
        
        if validated and validated[0]['table'] == expected_table:
            print(f"  ✅ {field:20s} → {expected_table}")
        else:
            actual_table = validated[0]['table'] if validated else "None"
            print(f"  ❌ {field:20s} → 期望 {expected_table}, 实际 {actual_table}")
            all_passed = False
    
    if all_passed:
        print("\n✅ 所有字段映射测试通过")
    else:
        print("\n❌ 部分字段映射测试失败")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    
    await parser.close()


if __name__ == "__main__":
    asyncio.run(test_material_field_mapping())
