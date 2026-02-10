"""
测试工艺修改功能

测试场景：
1. 通过 part_name 修改工艺
2. 通过 part_code 修改工艺
3. 验证 ID 映射是否正确
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser


async def test_process_modification():
    """测试工艺修改"""
    
    # 模拟数据
    context = {
        "subgraphs": [
            {
                "subgraph_id": "sg001",
                "part_code": "LP-02",
                "part_name": "上夹板",
                "material": "P20"
            },
            {
                "subgraph_id": "sg002",
                "part_code": "PH2-04",
                "part_name": "下夹板",
                "material": "718"
            }
        ],
        "process_snapshots": [
            {
                "snapshot_id": "prs001",
                "name": "上夹板加工",
                "feature_type": "wire",
                "conditions": "慢丝割两刀"
            },
            {
                "snapshot_id": "prs002",
                "name": "下夹板加工",
                "feature_type": "wire",
                "conditions": "快丝割一刀"
            }
        ],
        "features": [],
        "price_snapshots": []
    }
    
    # 创建 Parser
    parser = NLPParser(use_llm=False)  # 先测试规则解析
    
    print("=" * 60)
    print("测试1: 通过 part_name 修改工艺")
    print("=" * 60)
    
    text1 = "上夹板工艺改为快丝割一刀"
    changes1 = await parser.parse(text1, context)
    
    print(f"\n输入: {text1}")
    print(f"解析结果: {changes1}")
    
    if changes1:
        for change in changes1:
            print(f"\n修改详情:")
            print(f"  表名: {change['table']}")
            print(f"  ID: {change['id']}")
            print(f"  字段: {change['field']}")
            print(f"  值: {change['value']}")
    
    print("\n" + "=" * 60)
    print("测试2: 通过 part_code 修改工艺")
    print("=" * 60)
    
    text2 = "LP-02 的工艺改为快丝割一刀"
    changes2 = await parser.parse(text2, context)
    
    print(f"\n输入: {text2}")
    print(f"解析结果: {changes2}")
    
    if changes2:
        for change in changes2:
            print(f"\n修改详情:")
            print(f"  表名: {change['table']}")
            print(f"  ID: {change['id']}")
            print(f"  字段: {change['field']}")
            print(f"  值: {change['value']}")
    
    print("\n" + "=" * 60)
    print("测试3: 使用 LLM 解析")
    print("=" * 60)
    
    parser_llm = NLPParser(use_llm=True)
    
    text3 = "上夹板工艺改为快丝割一刀"
    changes3 = await parser_llm.parse(text3, context)
    
    print(f"\n输入: {text3}")
    print(f"解析结果: {changes3}")
    
    if changes3:
        for change in changes3:
            print(f"\n修改详情:")
            print(f"  表名: {change['table']}")
            print(f"  ID (原始): {change['id']}")
            print(f"  字段: {change['field']}")
            print(f"  值: {change['value']}")
            
            # 测试 ID 映射
            mapped_id = parser_llm._map_identifier_to_id(
                change['id'],
                change['table'],
                context
            )
            print(f"  ID (映射后): {mapped_id}")
    
    await parser.http_client.aclose()
    await parser_llm.http_client.aclose()


if __name__ == "__main__":
    asyncio.run(test_process_modification())
