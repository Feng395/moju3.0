"""
测试 DataViewBuilder 4表升级的向后兼容性

验证：
1. 3表架构的 raw_data 仍能正常工作
2. 4表架构的 raw_data 正常工作
3. 查询方法返回正确结果
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.data_view_builder import DataViewBuilder


def test_3_table_backward_compatibility():
    """测试 3 表架构的向后兼容性"""
    print("\n" + "="*60)
    print("测试 1: 3表架构向后兼容性")
    print("="*60)
    
    # 3表架构的原始数据（不包含 processing_cost_calculation_details）
    raw_data_3_tables = {
        "subgraphs": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "part_code": "P001",
                "part_name": "零件1",
                "subgraph_file_url": "http://example.com/sg001.json",
                "wire_process": "slow_wire",
                "wire_process_note": "慢走丝",
                "created_at": "2024-01-01T10:00:00",
                "slow_wire_length": 100.5,
                "drilling_time": 2.5,
                "nc_roughing_time": 3.0,
                "nc_milling_time": 1.5,
                "edm_time": 4.0
            }
        ],
        "features": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "feature_id": "ft-001",
                "version": 1,
                "material": "45钢",
                "length_mm": 100.0,
                "width_mm": 50.0,
                "thickness_mm": 20.0,
                "quantity": 10,
                "heat_treatment": "淬火"
            }
        ],
        "price_snapshots": [
            {
                "job_id": "job-001",
                "snapshot_id": "ps-001",
                "category": "wire",
                "sub_category": "slow_wire",
                "price": 150.0
            },
            {
                "job_id": "job-001",
                "snapshot_id": "ps-002",
                "category": "material",
                "sub_category": "45钢",
                "price": 8.5
            }
        ]
        # 注意：没有 processing_cost_calculation_details
    }
    
    # 构建展示视图
    display_view = DataViewBuilder.build_display_view(raw_data_3_tables)
    
    # 验证结果
    assert len(display_view) == 1, f"期望 1 条记录，实际 {len(display_view)} 条"
    
    item = display_view[0]
    
    # 验证基础字段
    assert item["part_code"] == "P001", "part_code 不匹配"
    assert item["part_name"] == "零件1", "part_name 不匹配"
    assert item["material"] == "45钢", "material 不匹配"
    assert item["process_unit_price"] == 150.0, "process_unit_price 不匹配"
    assert item["material_unit_price"] == 8.5, "material_unit_price 不匹配"
    
    # 验证新增字段
    assert item["drilling_time"] == 2.5, "drilling_time 不匹配"
    assert item["wire_length"] == 100.5, "wire_length 不匹配"
    assert item["heat_treatment"] == "淬火", "heat_treatment 不匹配"
    
    # 验证 weight 字段为 None（因为没有成本记录）
    assert item["weight"] is None, f"期望 weight 为 None，实际为 {item['weight']}"
    
    # 验证 _source
    assert item["_source"]["processing_cost_detail_id"] is None, "processing_cost_detail_id 应该为 None"
    
    print("✅ 3表架构向后兼容性测试通过")
    print(f"   - 成功构建 {len(display_view)} 条记录")
    print(f"   - weight 字段正确设置为 None")
    print(f"   - 所有原有字段正常工作")


def test_4_table_with_cost_details():
    """测试 4 表架构（包含成本记录）"""
    print("\n" + "="*60)
    print("测试 2: 4表架构（包含成本记录）")
    print("="*60)
    
    # 4表架构的原始数据
    raw_data_4_tables = {
        "subgraphs": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "part_code": "P001",
                "part_name": "零件1",
                "subgraph_file_url": "http://example.com/sg001.json",
                "wire_process": "slow_wire",
                "wire_process_note": "慢走丝",
                "created_at": "2024-01-01T10:00:00",
                "slow_wire_length": 100.5,
                "drilling_time": 2.5,
                "nc_roughing_time": 3.0,
                "nc_milling_time": 1.5,
                "edm_time": 4.0
            }
        ],
        "features": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "feature_id": "ft-001",
                "version": 1,
                "material": "45钢",
                "length_mm": 100.0,
                "width_mm": 50.0,
                "thickness_mm": 20.0,
                "quantity": 10,
                "heat_treatment": "淬火"
            }
        ],
        "price_snapshots": [
            {
                "job_id": "job-001",
                "snapshot_id": "ps-001",
                "category": "wire",
                "sub_category": "slow_wire",
                "price": 150.0
            },
            {
                "job_id": "job-001",
                "snapshot_id": "ps-002",
                "category": "material",
                "sub_category": "45钢",
                "price": 8.5
            }
        ],
        # 🆕 新增成本记录
        "processing_cost_calculation_details": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "detail_id": 123,
                "weight": 2.5
            }
        ]
    }
    
    # 构建展示视图
    display_view = DataViewBuilder.build_display_view(raw_data_4_tables)
    
    # 验证结果
    assert len(display_view) == 1, f"期望 1 条记录，实际 {len(display_view)} 条"
    
    item = display_view[0]
    
    # 验证基础字段
    assert item["part_code"] == "P001", "part_code 不匹配"
    assert item["material"] == "45钢", "material 不匹配"
    
    # 验证 weight 字段（应该有值）
    assert item["weight"] == 2.5, f"期望 weight 为 2.5，实际为 {item['weight']}"
    
    # 验证 _source
    assert item["_source"]["processing_cost_detail_id"] == 123, "processing_cost_detail_id 不匹配"
    
    print("✅ 4表架构测试通过")
    print(f"   - 成功构建 {len(display_view)} 条记录")
    print(f"   - weight 字段正确关联: {item['weight']}")
    print(f"   - processing_cost_detail_id 正确记录: {item['_source']['processing_cost_detail_id']}")


def test_find_methods():
    """测试查询方法"""
    print("\n" + "="*60)
    print("测试 3: 查询方法")
    print("="*60)
    
    raw_data = {
        "subgraphs": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "part_code": "P001",
                "part_name": "零件1",
                "created_at": "2024-01-01T10:00:00"
            },
            {
                "job_id": "job-001",
                "subgraph_id": "sg-002",
                "part_code": "P002",
                "part_name": "零件2",
                "created_at": "2024-01-01T11:00:00"
            }
        ],
        "features": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "feature_id": "ft-001",
                "version": 1,
                "material": "45钢"
            },
            {
                "job_id": "job-001",
                "subgraph_id": "sg-002",
                "feature_id": "ft-002",
                "version": 1,
                "material": "Cr12"
            }
        ],
        "price_snapshots": []
    }
    
    display_view = DataViewBuilder.build_display_view(raw_data)
    
    # 测试 find_by_part_code
    item = DataViewBuilder.find_by_part_code(display_view, "P001")
    assert item is not None, "find_by_part_code 应该找到记录"
    assert item["part_code"] == "P001", "part_code 不匹配"
    
    # 测试 find_by_subgraph_id
    item = DataViewBuilder.find_by_subgraph_id(display_view, "sg-002")
    assert item is not None, "find_by_subgraph_id 应该找到记录"
    assert item["part_code"] == "P002", "part_code 不匹配"
    
    # 测试 find_all_by_part_name
    items = DataViewBuilder.find_all_by_part_name(display_view, "零件1")
    assert len(items) == 1, f"期望找到 1 条记录，实际 {len(items)} 条"
    
    print("✅ 查询方法测试通过")
    print(f"   - find_by_part_code: 正常")
    print(f"   - find_by_subgraph_id: 正常")
    print(f"   - find_all_by_part_name: 正常")


def test_validate_mapping():
    """测试映射验证"""
    print("\n" + "="*60)
    print("测试 4: 映射验证")
    print("="*60)
    
    # 测试完整的 source
    display_item_complete = {
        "part_code": "P001",
        "_source": {
            "subgraph_id": "sg-001",
            "feature_id": "ft-001",
            "wire_price_snapshot_id": "ps-001",
            "material_price_snapshot_id": "ps-002",
            "processing_cost_detail_id": 123
        }
    }
    
    result = DataViewBuilder.validate_mapping(display_item_complete)
    assert result["is_valid"] == True, "完整的 source 应该验证通过"
    assert len(result["warnings"]) == 0, "不应该有警告"
    print("✅ 完整 source 验证通过")
    
    # 测试缺少 processing_cost_detail_id
    display_item_no_cost = {
        "part_code": "P001",
        "_source": {
            "subgraph_id": "sg-001",
            "feature_id": "ft-001",
            "wire_price_snapshot_id": "ps-001",
            "material_price_snapshot_id": "ps-002"
        }
    }
    
    result = DataViewBuilder.validate_mapping(display_item_no_cost)
    assert result["is_valid"] == True, "缺少 processing_cost_detail_id 仍应该验证通过"
    assert len(result["warnings"]) == 1, "应该有 1 个警告"
    assert "processing_cost_detail_id" in result["warnings"][0], "警告应该提到 processing_cost_detail_id"
    print("✅ 缺少 processing_cost_detail_id 的警告正确")
    
    # 测试缺少 subgraph_id（应该验证失败）
    display_item_no_subgraph = {
        "part_code": "P001",
        "_source": {
            "feature_id": "ft-001"
        }
    }
    
    result = DataViewBuilder.validate_mapping(display_item_no_subgraph)
    assert result["is_valid"] == False, "缺少 subgraph_id 应该验证失败"
    assert "subgraph_id" in result["missing_sources"], "missing_sources 应该包含 subgraph_id"
    print("✅ 缺少 subgraph_id 的验证失败正确")


def test_reverse_mapping():
    """测试反向映射（展示层 → 存储层）"""
    print("\n" + "="*60)
    print("测试 5: 反向映射")
    print("="*60)
    
    raw_data = {
        "subgraphs": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "part_code": "P001",
                "part_name": "零件1",
                "created_at": "2024-01-01T10:00:00"
            }
        ],
        "features": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "feature_id": "ft-001",
                "version": 1,
                "material": "45钢"
            }
        ],
        "price_snapshots": [],
        "processing_cost_calculation_details": [
            {
                "job_id": "job-001",
                "subgraph_id": "sg-001",
                "detail_id": 123,
                "weight": 2.5
            }
        ]
    }
    
    # 测试修改 material（features 表）
    display_changes = [
        {
            "part_code": "P001",
            "field": "material",
            "value": "Cr12"
        }
    ]
    
    table_changes = DataViewBuilder.map_display_to_tables(display_changes, raw_data)
    assert len(table_changes) == 1, f"期望 1 个表修改，实际 {len(table_changes)} 个"
    assert table_changes[0]["table"] == "features", "应该映射到 features 表"
    assert table_changes[0]["field"] == "material", "字段应该是 material"
    print("✅ material 字段反向映射正确")
    
    # 测试修改 weight（processing_cost_calculation_details 表）
    display_changes = [
        {
            "part_code": "P001",
            "field": "weight",
            "value": 3.0
        }
    ]
    
    table_changes = DataViewBuilder.map_display_to_tables(display_changes, raw_data)
    assert len(table_changes) == 1, f"期望 1 个表修改，实际 {len(table_changes)} 个"
    assert table_changes[0]["table"] == "processing_cost_calculation_details", "应该映射到 processing_cost_calculation_details 表"
    assert table_changes[0]["field"] == "weight", "字段应该是 weight"
    assert table_changes[0]["id"] == 123, "detail_id 应该是 123"
    print("✅ weight 字段反向映射正确")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("DataViewBuilder 4表升级 - 向后兼容性测试")
    print("="*60)
    
    try:
        test_3_table_backward_compatibility()
        test_4_table_with_cost_details()
        test_find_methods()
        test_validate_mapping()
        test_reverse_mapping()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        print("\n总结：")
        print("  ✓ 3表架构向后兼容")
        print("  ✓ 4表架构正常工作")
        print("  ✓ 查询方法正常")
        print("  ✓ 映射验证正常")
        print("  ✓ 反向映射正常")
        print("\n🎉 DataViewBuilder 4表升级实施成功！")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
