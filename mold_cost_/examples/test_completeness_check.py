"""
测试数据完整性检查功能
演示如何使用新的补全功能
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.validators.completeness_validator import CompletenessValidator


def test_completeness_check():
    """测试完整性检查"""
    
    # 模拟查询到的数据
    data = {
        "features": [
            {
                "feature_id": 64,
                "subgraph_id": "PH2-04",
                "length_mm": 309.5,
                "width_mm": 87,
                "thickness_mm": 47,
                "quantity": 1,
                "material": "Cr12mov",  # 完整
                "heat_treatment": "HRC56~58"
            },
            {
                "feature_id": 65,
                "subgraph_id": "DIE-03",
                "length_mm": None,  # 缺失
                "width_mm": None,   # 缺失
                "thickness_mm": 37,
                "quantity": 0,      # 缺失(为0)
                "material": None,   # 缺失
                "heat_treatment": "HRC50~52",
                "processing_instructions": {
                    "L": "2 -%%C10.00割,单+0.005(合销)",
                    "M": "2 -%%c10.5钻穿,正面M12xP1.75攻穿"
                }
            }
        ],
        "price_snapshots": [],
        "process_snapshots": [],
        "subgraphs": []
    }
    
    # 检查完整性
    result = CompletenessValidator.check_data_completeness(data)
    
    print("=" * 60)
    print("数据完整性检查结果")
    print("=" * 60)
    print(f"\n是否完整: {result['is_complete']}")
    print(f"摘要: {result['summary']}")
    
    if not result['is_complete']:
        print(f"\n缺失字段详情:")
        for item in result['missing_fields']:
            print(f"\n  记录: {item['record_name']} (ID: {item['record_id']})")
            print(f"  表: {item['table']}")
            print(f"  缺失: {', '.join(item['missing'].values())}")
    
    # 生成补全提示
    if not result['is_complete']:
        print("\n" + "=" * 60)
        print("LLM 补全提示")
        print("=" * 60)
        
        prompt = CompletenessValidator.generate_completion_prompt(
            result['missing_fields'],
            data
        )
        
        print(f"\n{prompt}")


if __name__ == "__main__":
    test_completeness_check()
