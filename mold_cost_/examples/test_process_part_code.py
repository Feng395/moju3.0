"""
测试工艺修改支持 part_code

验证：
1. 工艺修改能够识别 part_code（如 DIE-03）
2. 工艺修改能够识别 part_name（如"上夹板"）
3. find_all_by_identifier 方法同时支持两种标识符
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser
from agents.data_view_builder import DataViewBuilder


async def test_process_part_code():
    """测试工艺修改支持 part_code"""
    print("=" * 60)
    print("测试工艺修改支持 part_code")
    print("=" * 60)
    
    # 初始化 NLP Parser
    parser = NLPParser(use_llm=False)
    
    # 模拟上下文数据
    context = {
        "features": [
            {"feature_id": 1001, "subgraph_id": "sg_001", "material": "45钢"},
            {"feature_id": 1002, "subgraph_id": "sg_002", "material": "718"}
        ],
        "subgraphs": [
            {"subgraph_id": "sg_001", "part_name": "上夹板", "part_code": "LP-01", "wire_process": "slow_and_one"},
            {"subgraph_id": "sg_002", "part_name": "导柱", "part_code": "DIE-03", "wire_process": "fast_and_one"}
        ],
        "price_snapshots": [],
        "display_view": [
            {"part_code": "LP-01", "part_name": "上夹板", "_source": {"subgraph_id": "sg_001"}},
            {"part_code": "DIE-03", "part_name": "导柱", "_source": {"subgraph_id": "sg_002"}}
        ]
    }
    
    print("\n" + "=" * 60)
    print("测试 1: find_all_by_identifier 方法")
    print("=" * 60)
    
    display_view = context["display_view"]
    
    # 测试 part_code
    print("\n📋 测试 part_code: DIE-03")
    matches = DataViewBuilder.find_all_by_identifier(display_view, "DIE-03")
    print(f"  - 找到 {len(matches)} 个匹配")
    if matches:
        print(f"  - part_code: {matches[0].get('part_code')}")
        print(f"  - part_name: {matches[0].get('part_name')}")
        print("  ✅ 通过 part_code 查找成功")
    else:
        print("  ❌ 未找到匹配")
    
    # 测试 part_name
    print("\n📋 测试 part_name: 上夹板")
    matches = DataViewBuilder.find_all_by_identifier(display_view, "上夹板")
    print(f"  - 找到 {len(matches)} 个匹配")
    if matches:
        print(f"  - part_code: {matches[0].get('part_code')}")
        print(f"  - part_name: {matches[0].get('part_name')}")
        print("  ✅ 通过 part_name 查找成功")
    else:
        print("  ❌ 未找到匹配")
    
    # 测试不存在的标识符
    print("\n📋 测试不存在的标识符: XXX-99")
    matches = DataViewBuilder.find_all_by_identifier(display_view, "XXX-99")
    print(f"  - 找到 {len(matches)} 个匹配")
    if len(matches) == 0:
        print("  ✅ 正确返回空列表")
    else:
        print("  ❌ 应该返回空列表")
    
    print("\n" + "=" * 60)
    print("测试 2: 工艺修改使用 part_code")
    print("=" * 60)
    
    text = "DIE-03工艺设置为慢丝割一修一"
    print(f"\n📋 输入: {text}")
    
    # 提取实体
    part_name, process_desc = parser._extract_process_modification_entities(text)
    print(f"  - 提取的标识符: {part_name}")
    print(f"  - 工艺描述: {process_desc}")
    
    # 解析工艺修改
    changes = await parser._parse_process_modification(text, context)
    
    print(f"\n✅ 输出:")
    print(f"  - 修改数量: {len(changes)}")
    
    if len(changes) == 2:
        print("\n✅ 测试通过：生成了 2 个修改（1个零件 × 2个字段）")
        for i, change in enumerate(changes, 1):
            print(f"    {i}. table={change['table']}, id={change['id']}, field={change['field']}")
    else:
        print(f"\n❌ 测试失败：期望 2 条记录，实际 {len(changes)} 条")
    
    print("\n" + "=" * 60)
    print("测试 3: 工艺修改使用 part_name")
    print("=" * 60)
    
    text = "上夹板工艺改为快丝割一刀"
    print(f"\n📋 输入: {text}")
    
    changes = await parser._parse_process_modification(text, context)
    
    print(f"\n✅ 输出:")
    print(f"  - 修改数量: {len(changes)}")
    
    if len(changes) == 2:
        print("\n✅ 测试通过：生成了 2 个修改（1个零件 × 2个字段）")
        for i, change in enumerate(changes, 1):
            print(f"    {i}. table={change['table']}, id={change['id']}, field={change['field']}")
    else:
        print(f"\n❌ 测试失败：期望 2 条记录，实际 {len(changes)} 条")
    
    print("\n" + "=" * 60)
    print("测试 4: 对比两种方式的结果")
    print("=" * 60)
    
    # 使用 part_code
    text1 = "DIE-03工艺设置为慢丝割一修一"
    changes1 = await parser._parse_process_modification(text1, context)
    
    # 使用 part_name
    text2 = "导柱工艺设置为慢丝割一修一"
    changes2 = await parser._parse_process_modification(text2, context)
    
    print(f"\n📋 使用 part_code (DIE-03): {len(changes1)} 个修改")
    print(f"📋 使用 part_name (导柱): {len(changes2)} 个修改")
    
    if len(changes1) == len(changes2) == 2:
        # 检查是否修改了同一个 subgraph_id
        id1 = changes1[0]['id']
        id2 = changes2[0]['id']
        
        print(f"\n  - part_code 修改的 subgraph_id: {id1}")
        print(f"  - part_name 修改的 subgraph_id: {id2}")
        
        if id1 == id2:
            print("\n✅ 测试通过：两种方式修改了同一个零件")
        else:
            print("\n❌ 测试失败：两种方式修改了不同的零件")
    else:
        print("\n❌ 测试失败：修改数量不对")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    
    await parser.close()


if __name__ == "__main__":
    asyncio.run(test_process_part_code())
