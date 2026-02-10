"""
测试多个零件的工艺修改

测试场景:
1. "DIE-03, DIE-04工艺改为中丝割一修一"
2. "DIE-03，DIE-04工艺改为中丝割一修一"（中文逗号）
3. "DIE-03、DIE-04工艺改为中丝割一修一"（顿号）
4. "DIE-03 DIE-04工艺改为中丝割一修一"（空格）
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser


async def test_multi_part_process_modification():
    """测试多个零件的工艺修改"""
    
    print("=" * 60)
    print("测试多个零件的工艺修改")
    print("=" * 60)
    
    # 模拟数据
    mock_context = {
        "raw_data": {
            "features": [
                {"feature_id": 1001, "subgraph_id": "sg_001", "material": "45#"},
                {"feature_id": 1002, "subgraph_id": "sg_002", "material": "45#"},
                {"feature_id": 1003, "subgraph_id": "sg_003", "material": "45#"},
            ],
            "subgraphs": [
                {"subgraph_id": "sg_001", "part_code": "DIE-03", "part_name": "下模板"},
                {"subgraph_id": "sg_002", "part_code": "DIE-04", "part_name": "上模板"},
                {"subgraph_id": "sg_003", "part_code": "DIE-05", "part_name": "侧板"},
            ],
            "price_snapshots": []
        },
        "display_view": [
            {
                "part_code": "DIE-03",
                "part_name": "下模板",
                "_source": {"subgraph_id": "sg_001"}
            },
            {
                "part_code": "DIE-04",
                "part_name": "上模板",
                "_source": {"subgraph_id": "sg_002"}
            },
            {
                "part_code": "DIE-05",
                "part_name": "侧板",
                "_source": {"subgraph_id": "sg_003"}
            }
        ]
    }
    
    parser = NLPParser(use_llm=False)  # 不使用 LLM，只测试规则解析
    
    # 测试用例
    test_cases = [
        "DIE-03, DIE-04工艺改为中丝割一修一",
        "DIE-03，DIE-04工艺改为中丝割一修一",
        "DIE-03、DIE-04工艺改为中丝割一修一",
        "DIE-03 DIE-04工艺改为中丝割一修一",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"测试 {i}: {text}")
        print("=" * 60)
        
        try:
            changes = await parser.parse(text, mock_context)
            
            print(f"\n✅ 解析成功: {len(changes)} 个修改")
            
            # 按零件分组显示
            parts = {}
            for change in changes:
                part_id = change["id"]
                if part_id not in parts:
                    parts[part_id] = []
                parts[part_id].append(change)
            
            print(f"\n📋 修改了 {len(parts)} 个零件:")
            for part_id, part_changes in parts.items():
                print(f"\n  零件 {part_id}:")
                for change in part_changes:
                    print(f"    - {change['field']} = {change['value']}")
            
            # 验证结果
            expected_parts = 2  # DIE-03 和 DIE-04
            expected_changes = expected_parts * 2  # 每个零件 2 个字段
            
            if len(parts) == expected_parts and len(changes) == expected_changes:
                print(f"\n✅ 测试通过: 正确修改了 {expected_parts} 个零件")
            else:
                print(f"\n❌ 测试失败: 期望 {expected_parts} 个零件，实际 {len(parts)} 个")
        
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    await parser.close()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_multi_part_process_modification())
