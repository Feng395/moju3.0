"""
测试工艺 ID 映射功能

模拟实际场景：LLM 返回 part_code，需要映射到 snapshot_id
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.nlp_parser import NLPParser


async def test_id_mapping():
    """测试 ID 映射"""
    
    # 模拟真实数据结构
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
            },
            {
                "subgraph_id": "sg003",
                "part_code": "DIE-03",
                "part_name": "模芯",
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
            },
            {
                "snapshot_id": "prs003",
                "name": "模芯加工",
                "feature_type": "wire",
                "conditions": "慢丝割一刀"
            }
        ],
        "features": [],
        "price_snapshots": []
    }
    
    parser = NLPParser(use_llm=False)
    
    print("=" * 70)
    print("测试场景：LLM 返回 part_code，需要映射到 snapshot_id")
    print("=" * 70)
    
    # 模拟 LLM 返回的结果（使用 part_code）
    test_cases = [
        {
            "name": "测试1: 使用 part_code (LP-02)",
            "change": {
                "table": "process_snapshots",
                "id": "LP-02",  # LLM 返回的是 part_code
                "field": "conditions",
                "value": "快丝割一刀"
            },
            "expected_id": "prs001"
        },
        {
            "name": "测试2: 使用 part_name (上夹板)",
            "change": {
                "table": "process_snapshots",
                "id": "上夹板",  # LLM 返回的是 part_name
                "field": "conditions",
                "value": "快丝割一刀"
            },
            "expected_id": "prs001"
        },
        {
            "name": "测试3: 使用 part_code (PH2-04)",
            "change": {
                "table": "process_snapshots",
                "id": "PH2-04",
                "field": "conditions",
                "value": "慢丝割两刀"
            },
            "expected_id": "prs002"
        },
        {
            "name": "测试4: 使用 part_code (DIE-03)",
            "change": {
                "table": "process_snapshots",
                "id": "DIE-03",
                "field": "conditions",
                "value": "快丝割三刀"
            },
            "expected_id": "prs003"
        },
        {
            "name": "测试5: 直接使用 snapshot_id",
            "change": {
                "table": "process_snapshots",
                "id": "prs001",  # 直接使用正确的 ID
                "field": "conditions",
                "value": "快丝割一刀"
            },
            "expected_id": "prs001"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}")
        print("-" * 70)
        
        change = test_case['change']
        expected_id = test_case['expected_id']
        
        print(f"输入 ID: {change['id']}")
        print(f"期望 ID: {expected_id}")
        
        # 执行映射
        mapped_id = parser._map_identifier_to_id(
            change['id'],
            change['table'],
            context
        )
        
        print(f"映射后 ID: {mapped_id}")
        
        # 验证结果
        if mapped_id == expected_id:
            print("✅ 映射成功")
        else:
            print(f"❌ 映射失败：期望 {expected_id}，实际 {mapped_id}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    
    await parser.http_client.aclose()


if __name__ == "__main__":
    asyncio.run(test_id_mapping())
