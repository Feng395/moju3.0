"""
测试材料价格修改功能

验证表名映射是否正确工作
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.action_handlers.data_modification_handler import DataModificationHandler


def test_table_name_mapping():
    """测试表名映射"""
    print("=" * 80)
    print("🧪 测试表名映射")
    print("=" * 80)
    
    handler = DataModificationHandler()
    
    # 模拟数据（使用简化键名）
    mock_data = {
        "price_snapshots": [
            {
                "job_id": "test-job-123",
                "snapshot_id": 1,
                "category": "material",
                "sub_category": "CR12",
                "price": 10.0
            },
            {
                "job_id": "test-job-123",
                "snapshot_id": 2,
                "category": "material",
                "sub_category": "45#",
                "price": 5.0
            },
            {
                "job_id": "test-job-123",
                "snapshot_id": 3,
                "category": "wire",
                "sub_category": "slow_and_one",
                "price": 0.001
            }
        ]
    }
    
    # 模拟修改（使用数据库表名）
    changes = [
        {
            "table": "job_price_snapshots",  # LLM 生成的表名
            "filter": {
                "category": "material",
                "sub_category": "CR12"
            },
            "field": "price",
            "value": 5.0
        }
    ]
    
    print("\n📊 原始数据:")
    for record in mock_data["price_snapshots"]:
        if record["category"] == "material" and record["sub_category"] == "CR12":
            print(f"  CR12 价格: {record['price']}")
    
    print("\n🔧 应用修改...")
    modified_data = handler._apply_changes(
        mock_data,
        changes,
        job_id="test-job-123",
        user_id="test-user"
    )
    
    print("\n📊 修改后数据:")
    for record in modified_data["price_snapshots"]:
        if record["category"] == "material" and record["sub_category"] == "CR12":
            print(f"  CR12 价格: {record['price']}")
            if record['price'] == 5.0:
                print("  ✅ 修改成功！")
            else:
                print("  ❌ 修改失败！")


def test_filter_matching():
    """测试过滤条件匹配"""
    print("\n" + "=" * 80)
    print("🧪 测试过滤条件匹配")
    print("=" * 80)
    
    handler = DataModificationHandler()
    
    # 测试用例
    test_cases = [
        {
            "name": "精确匹配",
            "record": {"category": "material", "sub_category": "CR12"},
            "filter": {"category": "material", "sub_category": "CR12"},
            "expected": True
        },
        {
            "name": "大小写不敏感",
            "record": {"category": "material", "sub_category": "CR12"},
            "filter": {"category": "material", "sub_category": "cr12"},
            "expected": True
        },
        {
            "name": "不匹配",
            "record": {"category": "material", "sub_category": "45#"},
            "filter": {"category": "material", "sub_category": "CR12"},
            "expected": False
        },
        {
            "name": "部分匹配（category 匹配，sub_category 不匹配）",
            "record": {"category": "material", "sub_category": "45#"},
            "filter": {"category": "material", "sub_category": "CR12"},
            "expected": False
        }
    ]
    
    for test in test_cases:
        result = handler._match_filter(test["record"], test["filter"])
        status = "✅" if result == test["expected"] else "❌"
        print(f"\n{status} {test['name']}")
        print(f"  记录: {test['record']}")
        print(f"  过滤: {test['filter']}")
        print(f"  结果: {result} (期望: {test['expected']})")


if __name__ == "__main__":
    test_table_name_mapping()
    test_filter_matching()
    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)
