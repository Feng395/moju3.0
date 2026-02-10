"""
测试"全部工艺"修改功能

验证：
1. 规则解析能够识别"全部工艺"关键词
2. 系统能够将 part_name="ALL" 展开为所有零件
3. 批量修改所有零件的工艺（同时修改 wire_process 和 wire_process_note）
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser


async def test_all_process_modification():
    """测试全部工艺修改功能"""
    print("=" * 60)
    print("测试'全部工艺'修改功能")
    print("=" * 60)
    
    # 初始化 NLP Parser（不使用 LLM，只测试规则解析）
    parser = NLPParser(use_llm=False)
    
    # 模拟上下文数据（4个零件）
    context = {
        "features": [
            {"feature_id": 1001, "subgraph_id": "sg_001", "material": "45钢"},
            {"feature_id": 1002, "subgraph_id": "sg_002", "material": "718"},
            {"feature_id": 1003, "subgraph_id": "sg_003", "material": "P20"},
            {"feature_id": 1004, "subgraph_id": "sg_004", "material": "S136"}
        ],
        "subgraphs": [
            {"subgraph_id": "sg_001", "part_name": "上夹板", "part_code": "LP-01", "wire_process": "slow_and_one"},
            {"subgraph_id": "sg_002", "part_name": "下夹板", "part_code": "LP-02", "wire_process": "fast_and_one"},
            {"subgraph_id": "sg_003", "part_name": "导柱", "part_code": "PH-01", "wire_process": "mid_and_one"},
            {"subgraph_id": "sg_004", "part_name": "导套", "part_code": "PH-02", "wire_process": "fast_and_one"}
        ],
        "price_snapshots": [],
        "display_view": [
            {"part_code": "LP-01", "part_name": "上夹板", "_source": {"subgraph_id": "sg_001"}},
            {"part_code": "LP-02", "part_name": "下夹板", "_source": {"subgraph_id": "sg_002"}},
            {"part_code": "PH-01", "part_name": "导柱", "_source": {"subgraph_id": "sg_003"}},
            {"part_code": "PH-02", "part_name": "导套", "_source": {"subgraph_id": "sg_004"}}
        ]
    }
    
    print("\n" + "=" * 60)
    print("测试 1: 提取'全部工艺'实体")
    print("=" * 60)
    
    test_texts = [
        "全部工艺改为快丝割一刀",
        "所有工艺改为慢丝割一刀",
        "全体工艺修改为中丝割一刀"
    ]
    
    for text in test_texts:
        part_name, process_desc = parser._extract_process_modification_entities(text)
        print(f"\n📋 输入: {text}")
        print(f"  - part_name: {part_name}")
        print(f"  - process_desc: {process_desc}")
        
        if part_name == "ALL":
            print(f"  ✅ 正确识别为全部修改")
        else:
            print(f"  ❌ 未识别为全部修改")
    
    print("\n" + "=" * 60)
    print("测试 2: 解析'全部工艺'修改（规则解析）")
    print("=" * 60)
    
    text = "全部工艺改为快丝割一刀"
    print(f"\n📋 输入: {text}")
    
    # 调用工艺修改解析
    changes = await parser._parse_process_modification(text, context)
    
    print(f"\n✅ 输出:")
    print(f"  - 修改数量: {len(changes)}")
    
    # 应该生成 4个零件 × 2个字段 = 8个修改
    if len(changes) == 8:
        print("\n✅ 测试通过：生成了 8 个修改（4个零件 × 2个字段）")
        
        # 统计字段
        wire_process_count = sum(1 for c in changes if c['field'] == 'wire_process')
        wire_process_note_count = sum(1 for c in changes if c['field'] == 'wire_process_note')
        
        print(f"  - wire_process 修改: {wire_process_count} 条")
        print(f"  - wire_process_note 修改: {wire_process_note_count} 条")
        
        # 显示前2个修改
        print(f"\n  示例修改:")
        for i, change in enumerate(changes[:2], 1):
            print(f"    {i}. table={change['table']}, id={change['id']}, field={change['field']}, value={change['value']}")
    else:
        print(f"\n❌ 测试失败：期望 8 条记录，实际 {len(changes)} 条")
    
    print("\n" + "=" * 60)
    print("测试 3: 单个零件工艺修改（对比）")
    print("=" * 60)
    
    text = "上夹板工艺改为快丝割一刀"
    print(f"\n📋 输入: {text}")
    
    changes = await parser._parse_process_modification(text, context)
    
    print(f"\n✅ 输出:")
    print(f"  - 修改数量: {len(changes)}")
    
    # 应该生成 1个零件 × 2个字段 = 2个修改
    if len(changes) == 2:
        print("\n✅ 测试通过：生成了 2 个修改（1个零件 × 2个字段）")
        for i, change in enumerate(changes, 1):
            print(f"    {i}. table={change['table']}, id={change['id']}, field={change['field']}")
    else:
        print(f"\n❌ 测试失败：期望 2 条记录，实际 {len(changes)} 条")
    
    print("\n" + "=" * 60)
    print("测试 4: 验证字段值")
    print("=" * 60)
    
    text = "全部工艺改为快丝割一刀"
    print(f"\n📋 输入: {text}")
    
    changes = await parser._parse_process_modification(text, context)
    
    if changes:
        # 检查 wire_process_note 的值
        note_changes = [c for c in changes if c['field'] == 'wire_process_note']
        if note_changes:
            note_value = note_changes[0]['value']
            print(f"\n✅ wire_process_note 值: {note_value}")
            
            if note_value == "快丝割一刀":
                print("  ✅ 值正确")
            else:
                print(f"  ❌ 值错误，期望'快丝割一刀'，实际'{note_value}'")
        
        # 检查 wire_process 的值（可能为空，因为没有查询 process_rules）
        process_changes = [c for c in changes if c['field'] == 'wire_process']
        if process_changes:
            process_value = process_changes[0]['value']
            print(f"\n✅ wire_process 值: '{process_value}'")
            print("  ℹ️  注意：未查询 process_rules，所以可能为空字符串")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    
    await parser.close()


if __name__ == "__main__":
    asyncio.run(test_all_process_modification())
