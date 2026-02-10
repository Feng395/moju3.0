"""
测试展示视图完整流程
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser
from agents.data_view_builder import DataViewBuilder


async def test_display_view_flow():
    """测试展示视图完整流程"""
    
    # 1. 模拟原始数据
    raw_data = {
        "subgraphs": [
            {
                "subgraph_id": "b3067267-48a2-4df3-8ac7-e221ec58048b",
                "part_code": "LP-02",
                "part_name": "下模板",
                "subgraph_file_url": "http://example.com/file.svg"
            }
        ],
        "features": [
            {
                "feature_id": "f001",
                "subgraph_id": "b3067267-48a2-4df3-8ac7-e221ec58048b",
                "material": "45钢",
                "length_mm": 97.0,
                "width_mm": 50.0,
                "thickness_mm": 10.0,
                "quantity": 1
            }
        ],
        "process_snapshots": [],
        "price_snapshots": []
    }
    
    print("=" * 60)
    print("展示视图完整流程测试")
    print("=" * 60)
    
    # 2. 构建展示视图
    print("\n步骤1: 构建展示视图")
    display_view = DataViewBuilder.build_display_view(raw_data)
    print(f"✅ 展示视图: {len(display_view)} 条记录")
    for item in display_view:
        print(f"  - part_code={item['part_code']}, material={item['material']}, length_mm={item['length_mm']}")
        print(f"    _source: {item['_source']}")
    
    # 3. 解析用户输入
    print("\n步骤2: 解析用户输入")
    parser = NLPParser(use_llm=False)
    
    test_input = "修改LP-02长度为100"
    print(f"用户输入: {test_input}")
    
    # 构建完整上下文
    context = {
        "raw_data": raw_data,
        "display_view": display_view
    }
    
    # 解析
    changes = await parser._parse_with_display_view(test_input, context)
    
    print(f"\n✅ 解析结果: {len(changes)} 个修改")
    for change in changes:
        print(f"  - table={change['table']}, id={change['id']}, field={change['field']}, value={change['value']}")
    
    # 4. 验证映射
    print("\n步骤3: 验证映射")
    if changes:
        change = changes[0]
        if change['table'] == 'features' and change['id'] == 'f001':
            print("✅ ID 映射正确: LP-02 → feature_id=f001")
        else:
            print(f"❌ ID 映射错误: 期望 features.f001, 实际 {change['table']}.{change['id']}")
    
    await parser.close()


if __name__ == "__main__":
    asyncio.run(test_display_view_flow())
