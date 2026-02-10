"""
InteractionAgent 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.interaction_agent import InteractionAgent


@pytest.mark.asyncio
async def test_basic_missing_params():
    """测试基础参数缺失检测"""
    agent = InteractionAgent(use_llm=False)
    
    context = {
        "job_id": "test-001",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
            }
        ]
    }
    
    result = await agent.process(context)
    
    assert result.status == "need_input"
    assert len(result.data["missing_params"]) == 2  # thickness_mm, material
    assert result.data["prompt"] != ""


@pytest.mark.asyncio
async def test_complete_params():
    """测试参数完整的情况"""
    agent = InteractionAgent(use_llm=False)
    
    context = {
        "job_id": "test-002",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                "thickness_mm": 30,
                "material": "P20"
            }
        ]
    }
    
    result = await agent.process(context)
    
    assert result.status == "ok"
    assert result.message == "参数完整，无需用户交互"


@pytest.mark.asyncio
async def test_user_input_validation():
    """测试用户输入验证"""
    agent = InteractionAgent(use_llm=False)
    
    # 第一次检查
    context = {
        "job_id": "test-003",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
            }
        ]
    }
    
    result1 = await agent.process(context)
    assert result1.status == "need_input"
    
    # 用户补充参数
    context["user_input"] = {
        "UP01": {
            "thickness_mm": 30,
            "material": "P20"
        }
    }
    
    result2 = await agent.process(context)
    assert result2.status == "ok"
    
    # 验证参数已更新
    updated_feature = result2.data["features"][0]
    assert updated_feature["thickness_mm"] == 30
    assert updated_feature["material"] == "P20"


@pytest.mark.asyncio
async def test_wire_cut_param():
    """测试线割参数检查"""
    agent = InteractionAgent(use_llm=False)
    
    context = {
        "job_id": "test-004",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                "thickness_mm": 30,
                "material": "P20",
                "needs_wire_cut": True,
                # wire_length_mm 缺失
            }
        ]
    }
    
    result = await agent.process(context)
    
    assert result.status == "need_input"
    
    # 检查是否包含 wire_length_mm
    param_names = [p["param_name"] for p in result.data["missing_params"]]
    assert "wire_length_mm" in param_names


@pytest.mark.asyncio
async def test_multiple_subgraphs():
    """测试多个子图"""
    agent = InteractionAgent(use_llm=False)
    
    context = {
        "job_id": "test-005",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
            },
            {
                "subgraph_id": "UP02",
                "volume_mm3": 2000,
                "thickness_mm": 50,
            },
            {
                "subgraph_id": "CORE01",
                "volume_mm3": 1500,
                "material": "718"
            }
        ]
    }
    
    result = await agent.process(context)
    
    assert result.status == "need_input"
    
    # UP01 缺 2 个，UP02 缺 1 个，CORE01 缺 1 个
    assert len(result.data["missing_params"]) == 4
    
    # 检查子图分组
    subgraph_ids = [p["subgraph_id"] for p in result.data["missing_params"]]
    assert "UP01" in subgraph_ids
    assert "UP02" in subgraph_ids
    assert "CORE01" in subgraph_ids


@pytest.mark.asyncio
async def test_partial_user_input():
    """测试部分用户输入"""
    agent = InteractionAgent(use_llm=False)
    
    context = {
        "job_id": "test-006",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
            }
        ]
    }
    
    # 只补充一个参数
    context["user_input"] = {
        "UP01": {
            "thickness_mm": 30,
            # material 仍然缺失
        }
    }
    
    result = await agent.process(context)
    
    assert result.status == "need_input"
    assert len(result.data["missing_params"]) == 1
    
    # 只剩 material 缺失
    assert result.data["missing_params"][0]["param_name"] == "material"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
