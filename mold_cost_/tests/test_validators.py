"""
验证器测试
负责人：人员B2

测试内容：
1. 字段验证器测试
2. 业务规则验证器测试
3. 修改验证器测试
"""
import pytest
from shared.validators import (
    FieldValidator,
    BusinessValidator,
    ModificationValidator,
    ValidationResult
)


class TestFieldValidator:
    """字段验证器测试"""
    
    def test_validate_material_valid(self):
        """测试有效的材质代码"""
        is_valid, error = FieldValidator.validate_material("P20")
        assert is_valid is True
        assert error is None
        
        is_valid, error = FieldValidator.validate_material("718")
        assert is_valid is True
        
        is_valid, error = FieldValidator.validate_material("nak80")  # 小写
        assert is_valid is True
    
    def test_validate_material_invalid(self):
        """测试无效的材质代码"""
        is_valid, error = FieldValidator.validate_material("INVALID")
        assert is_valid is False
        assert "无效的材质代码" in error
        
        is_valid, error = FieldValidator.validate_material("")
        assert is_valid is False
        
        is_valid, error = FieldValidator.validate_material(None)
        assert is_valid is False
    
    def test_validate_weight_valid(self):
        """测试有效的重量"""
        is_valid, error = FieldValidator.validate_weight(5.5)
        assert is_valid is True
        
        is_valid, error = FieldValidator.validate_weight(100)
        assert is_valid is True
        
        is_valid, error = FieldValidator.validate_weight("10.5")  # 字符串数字
        assert is_valid is True
    
    def test_validate_weight_invalid(self):
        """测试无效的重量"""
        is_valid, error = FieldValidator.validate_weight(-1)
        assert is_valid is False
        assert "必须大于0" in error
        
        is_valid, error = FieldValidator.validate_weight(0)
        assert is_valid is False
        
        is_valid, error = FieldValidator.validate_weight(100000)
        assert is_valid is False
        assert "不能超过" in error
        
        is_valid, error = FieldValidator.validate_weight("abc")
        assert is_valid is False
    
    def test_validate_price_valid(self):
        """测试有效的价格"""
        is_valid, error = FieldValidator.validate_price(1000)
        assert is_valid is True
        
        is_valid, error = FieldValidator.validate_price(0)  # 0 是有效的
        assert is_valid is True
    
    def test_validate_price_invalid(self):
        """测试无效的价格"""
        is_valid, error = FieldValidator.validate_price(-100)
        assert is_valid is False
        assert "不能为负数" in error
        
        is_valid, error = FieldValidator.validate_price(20000000)
        assert is_valid is False
    
    def test_validate_quantity_valid(self):
        """测试有效的数量"""
        is_valid, error = FieldValidator.validate_quantity(10)
        assert is_valid is True
        
        is_valid, error = FieldValidator.validate_quantity("5")
        assert is_valid is True
    
    def test_validate_quantity_invalid(self):
        """测试无效的数量"""
        is_valid, error = FieldValidator.validate_quantity(0)
        assert is_valid is False
        
        is_valid, error = FieldValidator.validate_quantity(-5)
        assert is_valid is False
        
        is_valid, error = FieldValidator.validate_quantity(5.5)  # 不是整数
        assert is_valid is False
    
    def test_validate_string_valid(self):
        """测试有效的字符串"""
        is_valid, error = FieldValidator.validate_string("测试字符串")
        assert is_valid is True
        
        is_valid, error = FieldValidator.validate_string("", max_length=10)
        assert is_valid is True
    
    def test_validate_string_invalid(self):
        """测试无效的字符串"""
        is_valid, error = FieldValidator.validate_string("a" * 1000, max_length=100)
        assert is_valid is False
        assert "长度不能超过" in error
        
        is_valid, error = FieldValidator.validate_string(123)
        assert is_valid is False
    
    def test_validate_field_auto(self):
        """测试自动字段验证"""
        # 材质字段
        is_valid, error = FieldValidator.validate_field("material", "P20")
        assert is_valid is True
        
        # 重量字段
        is_valid, error = FieldValidator.validate_field("weight", 5.5)
        assert is_valid is True
        
        # 价格字段
        is_valid, error = FieldValidator.validate_field("price", 1000)
        assert is_valid is True


class TestBusinessValidator:
    """业务规则验证器测试"""
    
    def test_validate_subgraph_valid(self):
        """测试有效的子图数据"""
        subgraph = {
            "subgraph_id": "UP01",
            "material": "P20",
            "weight": 5.5
        }
        
        is_valid, error = BusinessValidator.validate_subgraph_data(subgraph)
        assert is_valid is True
        assert error is None
    
    def test_validate_subgraph_missing_field(self):
        """测试缺少必需字段的子图"""
        subgraph = {
            "subgraph_id": "UP01",
            "material": "P20"
            # 缺少 weight
        }
        
        is_valid, error = BusinessValidator.validate_subgraph_data(subgraph)
        assert is_valid is False
        assert "缺少必需字段" in error
    
    def test_validate_subgraph_invalid_weight(self):
        """测试重量超出范围的子图"""
        subgraph = {
            "subgraph_id": "UP01",
            "material": "NAK80",
            "weight": 10000  # 超出 NAK80 的范围
        }
        
        is_valid, error = BusinessValidator.validate_subgraph_data(subgraph)
        assert is_valid is False
        assert "重量应在" in error
    
    def test_validate_data_consistency(self):
        """测试数据一致性"""
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
        assert is_valid is True


class TestModificationValidator:
    """修改验证器测试"""
    
    def test_validate_single_change_valid(self):
        """测试有效的单个修改"""
        change = {
            "table": "subgraphs",
            "id": "UP01",
            "field": "material",
            "value": "718"
        }
        
        current_data = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
            ]
        }
        
        result = ModificationValidator.validate_single_change(change, current_data)
        assert result.is_valid is True
    
    def test_validate_single_change_missing_field(self):
        """测试缺少必需字段的修改"""
        change = {
            "table": "subgraphs",
            "id": "UP01"
            # 缺少 field 和 value
        }
        
        current_data = {"subgraphs": []}
        
        result = ModificationValidator.validate_single_change(change, current_data)
        assert result.is_valid is False
        assert "缺少必需字段" in result.error_message
    
    def test_validate_single_change_invalid_table(self):
        """测试无效的表名"""
        change = {
            "table": "invalid_table",
            "id": "UP01",
            "field": "material",
            "value": "718"
        }
        
        current_data = {}
        
        result = ModificationValidator.validate_single_change(change, current_data)
        assert result.is_valid is False
        assert "无效的表名" in result.error_message
    
    def test_validate_single_change_record_not_found(self):
        """测试记录不存在"""
        change = {
            "table": "subgraphs",
            "id": "NOT_EXIST",
            "field": "material",
            "value": "718"
        }
        
        current_data = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
            ]
        }
        
        result = ModificationValidator.validate_single_change(change, current_data)
        assert result.is_valid is False
        assert "不存在" in result.error_message
    
    def test_validate_single_change_invalid_field(self):
        """测试不允许修改的字段"""
        change = {
            "table": "subgraphs",
            "id": "UP01",
            "field": "subgraph_id",  # ID 字段不允许修改
            "value": "NEW_ID"
        }
        
        current_data = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
            ]
        }
        
        result = ModificationValidator.validate_single_change(change, current_data)
        assert result.is_valid is False
        assert "不允许修改字段" in result.error_message
    
    def test_validate_single_change_invalid_value(self):
        """测试无效的字段值"""
        change = {
            "table": "subgraphs",
            "id": "UP01",
            "field": "material",
            "value": "INVALID_MATERIAL"
        }
        
        current_data = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
            ]
        }
        
        result = ModificationValidator.validate_single_change(change, current_data)
        assert result.is_valid is False
        assert "值验证失败" in result.error_message
    
    def test_validate_changes_multiple(self):
        """测试多个修改"""
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
        
        current_data = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
            ]
        }
        
        result = ModificationValidator.validate_changes(changes, current_data)
        assert result.is_valid is True
    
    def test_validate_changes_empty(self):
        """测试空修改列表"""
        changes = []
        current_data = {}
        
        result = ModificationValidator.validate_changes(changes, current_data)
        assert result.is_valid is False
        assert "修改列表为空" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
