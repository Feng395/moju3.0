"""
测试 DataViewBuilder
"""
import pytest
from agents.data_view_builder import DataViewBuilder


def test_build_display_view():
    """测试构建展示视图"""
    
    # 准备测试数据
    raw_data = {
        "subgraphs": [
            {
                "subgraph_id": "sg_001",
                "part_code": "P001",
                "part_name": "零件1"
            }
        ],
        "features": [
            {
                "feature_id": "ft_001",
                "subgraph_id": "sg_001",
                "material": "45钢",
                "length_mm": 100.0,
                "width_mm": 50.0,
                "thickness_mm": 10.0,
                "quantity": 2
            }
        ],
        "process_snapshots": [
            {
                "snapshot_id": "ps_001",
                "feature_type": "wire",
                "name": "零件1",
                "conditions": "slow_and_one"
            }
        ],
        "price_snapshots": [
            {
                "snapshot_id": "wp_001",
                "category": "wire",
                "sub_category": "slow_and_one",
                "price": 0.5
            },
            {
                "snapshot_id": "mp_001",
                "category": "material",
                "sub_category": "45钢",
                "price": 8.5
            }
        ]
    }
    
    # 构建展示视图
    display_view = DataViewBuilder.build_display_view(raw_data)
    
    # 验证结果
    assert len(display_view) == 1
    
    item = display_view[0]
    assert item["part_code"] == "P001"
    assert item["part_name"] == "零件1"
    assert item["material"] == "45钢"
    assert item["length_mm"] == 100.0
    assert item["process_code"] == "slow_and_one"
    assert item["process_unit_price"] == 0.5
    assert item["material_unit_price"] == 8.5
    
    # 验证 _source
    source = item["_source"]
    assert source["subgraph_id"] == "sg_001"
    assert source["feature_id"] == "ft_001"
    assert source["process_snapshot_id"] == "ps_001"
    assert source["wire_price_snapshot_id"] == "wp_001"
    assert source["material_price_snapshot_id"] == "mp_001"


def test_map_display_to_tables():
    """测试反向映射"""
    
    # 准备测试数据
    raw_data = {
        "subgraphs": [
            {"subgraph_id": "sg_001", "part_code": "P001", "part_name": "零件1"}
        ],
        "features": [
            {
                "feature_id": "ft_001",
                "subgraph_id": "sg_001",
                "material": "45钢"
            }
        ],
        "process_snapshots": [],
        "price_snapshots": []
    }
    
    # 展示层修改
    display_changes = [
        {
            "part_code": "P001",
            "field": "material",
            "value": "40Cr"
        }
    ]
    
    # 反向映射
    table_changes = DataViewBuilder.map_display_to_tables(
        display_changes,
        raw_data
    )
    
    # 验证结果
    assert len(table_changes) == 1
    
    change = table_changes[0]
    assert change["table"] == "features"
    assert change["id"] == "ft_001"
    assert change["field"] == "material"
    assert change["value"] == "40Cr"


def test_find_by_part_code():
    """测试通过 part_code 查找"""
    
    display_view = [
        {"part_code": "P001", "part_name": "零件1"},
        {"part_code": "P002", "part_name": "零件2"}
    ]
    
    # 查找存在的
    item = DataViewBuilder.find_by_part_code(display_view, "P001")
    assert item is not None
    assert item["part_name"] == "零件1"
    
    # 查找不存在的
    item = DataViewBuilder.find_by_part_code(display_view, "P999")
    assert item is None


def test_validate_mapping():
    """测试验证映射完整性"""
    
    # 完整的映射
    display_item = {
        "_source": {
            "subgraph_id": "sg_001",
            "feature_id": "ft_001",
            "process_snapshot_id": "ps_001",
            "wire_price_snapshot_id": "wp_001",
            "material_price_snapshot_id": "mp_001"
        }
    }
    
    result = DataViewBuilder.validate_mapping(display_item)
    assert result["is_valid"] is True
    assert len(result["missing_sources"]) == 0
    
    # 缺少 feature_id
    display_item = {
        "_source": {
            "subgraph_id": "sg_001"
        }
    }
    
    result = DataViewBuilder.validate_mapping(display_item)
    assert result["is_valid"] is True  # subgraph_id 存在即可
    assert len(result["warnings"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
