"""
验证器功能测试脚本

使用方法：
    python examples/test_validators.py

功能：
1. 测试字段验证器
2. 测试业务规则验证器
3. 测试修改验证器
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.validators import (
    FieldValidator,
    BusinessValidator,
    ModificationValidator
)


def print_result(title, is_valid, error=None):
    """打印测试结果"""
    status = "✅ 通过" if is_valid else "❌ 失败"
    print(f"{title}: {status}")
    if error:
        print(f"   错误: {error}")
    print()


def test_field_validator():
    """测试字段验证器"""
    print("=" * 60)
    print("字段验证器测试")
    print("=" * 60)
    print()
    
    # 测试材质验证
    print("【材质验证】")
    is_valid, error = FieldValidator.validate_material("P20")
    print_result("有效材质 (P20)", is_valid, error)
    
    is_valid, error = FieldValidator.validate_material("INVALID")
    print_result("无效材质 (INVALID)", not is_valid, error)
    
    # 测试重量验证
    print("【重量验证】")
    is_valid, error = FieldValidator.validate_weight(5.5)
    print_result("有效重量 (5.5kg)", is_valid, error)
    
    is_valid, error = FieldValidator.validate_weight(-1)
    print_result("无效重量 (-1kg)", not is_valid, error)
    
    # 测试价格验证
    print("【价格验证】")
    is_valid, error = FieldValidator.validate_price(1000)
    print_result("有效价格 (1000元)", is_valid, error)
    
    is_valid, error = FieldValidator.validate_price(-100)
    print_result("无效价格 (-100元)", not is_valid, error)
    
    # 测试自动字段验证
    print("【自动字段验证】")
    is_valid, error = FieldValidator.validate_field("material", "718")
    print_result("自动验证材质字段", is_valid, error)
    
    is_valid, error = FieldValidator.validate_field("weight", 10.5)
    print_result("自动验证重量字段", is_valid, error)


def test_business_validator():
    """测试业务规则验证器"""
    print("=" * 60)
    print("业务规则验证器测试")
    print("=" * 60)
    print()
    
    # 测试子图数据验证
    print("【子图数据验证】")
    
    valid_subgraph = {
        "subgraph_id": "UP01",
        "material": "P20",
        "weight": 5.5
    }
    is_valid, error = BusinessValidator.validate_subgraph_data(valid_subgraph)
    print_result("有效子图数据", is_valid, error)
    
    invalid_subgraph = {
        "subgraph_id": "UP01",
        "material": "P20"
        # 缺少 weight
    }
    is_valid, error = BusinessValidator.validate_subgraph_data(invalid_subgraph)
    print_result("缺少必需字段的子图", not is_valid, error)
    
    # 测试数据一致性
    print("【数据一致性验证】")
    
    data = {
        "subgraphs": [
            {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
        ],
        "features": [
            {"feature_id": "F01", "feature_type": "hole"}
        ],
        "price_snapshots": [
            {"snapshot_id": "PS01", "total_price": 1000}
        ],
        "process_snapshots": [
            {"snapshot_id": "PRS01", "process_type": "milling"}
        ]
    }
    
    is_valid, error = BusinessValidator.validate_data_consistency(data)
    print_result("完整数据一致性", is_valid, error)


def test_modification_validator():
    """测试修改验证器"""
    print("=" * 60)
    print("修改验证器测试")
    print("=" * 60)
    print()
    
    current_data = {
        "subgraphs": [
            {"subgraph_id": "UP01", "material": "P20", "weight": 5.5},
            {"subgraph_id": "DOWN01", "material": "718", "weight": 6.2}
        ],
        "features": [],
        "price_snapshots": [],
        "process_snapshots": []
    }
    
    # 测试有效修改
    print("【有效修改】")
    
    valid_change = {
        "table": "subgraphs",
        "id": "UP01",
        "field": "material",
        "value": "718"
    }
    
    result = ModificationValidator.validate_single_change(valid_change, current_data)
    print_result("修改材质 (P20 → 718)", result.is_valid, result.error_message)
    
    # 测试无效修改 - 无效材质
    print("【无效修改 - 无效材质】")
    
    invalid_change = {
        "table": "subgraphs",
        "id": "UP01",
        "field": "material",
        "value": "INVALID_MATERIAL"
    }
    
    result = ModificationValidator.validate_single_change(invalid_change, current_data)
    print_result("修改为无效材质", not result.is_valid, result.error_message)
    
    # 测试无效修改 - 记录不存在
    print("【无效修改 - 记录不存在】")
    
    invalid_change = {
        "table": "subgraphs",
        "id": "NOT_EXIST",
        "field": "material",
        "value": "718"
    }
    
    result = ModificationValidator.validate_single_change(invalid_change, current_data)
    print_result("修改不存在的记录", not result.is_valid, result.error_message)
    
    # 测试无效修改 - 不允许修改的字段
    print("【无效修改 - 不允许修改的字段】")
    
    invalid_change = {
        "table": "subgraphs",
        "id": "UP01",
        "field": "subgraph_id",  # ID 字段不允许修改
        "value": "NEW_ID"
    }
    
    result = ModificationValidator.validate_single_change(invalid_change, current_data)
    print_result("修改 ID 字段", not result.is_valid, result.error_message)
    
    # 测试多个修改
    print("【多个修改】")
    
    changes = [
        {
            "table": "subgraphs",
            "id": "UP01",
            "field": "material",
            "value": "718"
        },
        {
            "table": "subgraphs",
            "id": "UP01",
            "field": "weight",
            "value": 6.5
        }
    ]
    
    result = ModificationValidator.validate_changes(changes, current_data)
    print_result("批量修改（2个）", result.is_valid, result.error_message)
    if result.warnings:
        print(f"   警告: {', '.join(result.warnings)}")
        print()


def main():
    """主函数"""
    print("\n")
    print("=" * 60)
    print("验证器功能测试")
    print("=" * 60)
    print()
    
    # 测试字段验证器
    test_field_validator()
    
    # 测试业务规则验证器
    test_business_validator()
    
    # 测试修改验证器
    test_modification_validator()
    
    print("=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
