"""
乐观锁测试
负责人：人员B2

测试场景：
1. 版本哈希计算（单元测试）
2. 版本哈希一致性（单元测试）
3. 版本哈希变化检测（单元测试）

注意：API 集成测试需要真实的测试环境（数据库 + Redis + JWT）
"""
import pytest
from agents.interaction_agent import InteractionAgent


@pytest.mark.asyncio
async def test_calculate_data_version():
    """测试版本哈希计算"""
    agent = InteractionAgent()
    
    # 测试数据
    data = {
        "subgraphs": [
            {
                "subgraph_id": "UP01",
                "material": "P20",
                "weight": 10.5
            },
            {
                "subgraph_id": "UP02",
                "material": "718",
                "weight": 8.3
            }
        ],
        "features": [
            {
                "feature_id": "F001",
                "name": "孔"
            }
        ]
    }
    
    # 计算版本
    version = agent._calculate_data_version(data)
    
    # 验证
    assert "subgraphs:UP01" in version
    assert "subgraphs:UP02" in version
    assert "features:F001" in version
    assert len(version) == 3
    
    # 验证哈希值是字符串
    for key, hash_value in version.items():
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 哈希长度


@pytest.mark.asyncio
async def test_version_hash_consistency():
    """测试版本哈希一致性"""
    agent = InteractionAgent()
    
    # 相同数据
    data1 = {
        "subgraphs": [
            {"subgraph_id": "UP01", "material": "P20", "weight": 10.5}
        ]
    }
    
    data2 = {
        "subgraphs": [
            {"subgraph_id": "UP01", "material": "P20", "weight": 10.5}
        ]
    }
    
    # 计算版本
    version1 = agent._calculate_data_version(data1)
    version2 = agent._calculate_data_version(data2)
    
    # 相同数据应该产生相同哈希
    assert version1 == version2


@pytest.mark.asyncio
async def test_version_hash_change_detection():
    """测试版本哈希变化检测"""
    agent = InteractionAgent()
    
    # 原始数据
    data1 = {
        "subgraphs": [
            {"subgraph_id": "UP01", "material": "P20", "weight": 10.5}
        ]
    }
    
    # 修改后的数据
    data2 = {
        "subgraphs": [
            {"subgraph_id": "UP01", "material": "718", "weight": 10.5}  # 材质改变
        ]
    }
    
    # 计算版本
    version1 = agent._calculate_data_version(data1)
    version2 = agent._calculate_data_version(data2)
    
    # 不同数据应该产生不同哈希
    assert version1["subgraphs:UP01"] != version2["subgraphs:UP01"]


@pytest.mark.asyncio
async def test_empty_data():
    """测试空数据"""
    agent = InteractionAgent()
    
    # 空数据
    data = {
        "subgraphs": [],
        "features": []
    }
    
    # 计算版本
    version = agent._calculate_data_version(data)
    
    # 应该返回空字典
    assert version == {}


@pytest.mark.asyncio
async def test_missing_id_field():
    """测试缺少 ID 字段的记录"""
    agent = InteractionAgent()
    
    # 缺少 ID 的数据
    data = {
        "subgraphs": [
            {"material": "P20", "weight": 10.5}  # 缺少 subgraph_id
        ]
    }
    
    # 计算版本
    version = agent._calculate_data_version(data)
    
    # 应该跳过没有 ID 的记录
    assert version == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
