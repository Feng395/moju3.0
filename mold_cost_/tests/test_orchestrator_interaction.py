"""
测试 Orchestrator 与 InteractionAgent 的集成
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.orchestrator_agent import OrchestratorAgent


@pytest.mark.asyncio
async def test_orchestrator_with_complete_params():
    """测试参数完整的情况"""
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    # 模拟完整参数的状态
    initial_state = {
        "job_id": "test-001",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                "thickness_mm": 30,
                "material": "P20"
            }
        ]
    }
    
    # 执行 check_params 阶段
    result_state = await orchestrator._stage_check_params(initial_state)
    
    # 验证结果
    assert result_state["stage"] == "check_params"
    assert result_state["missing_params"] == []
    assert "error" not in result_state


@pytest.mark.asyncio
async def test_orchestrator_with_missing_params():
    """测试参数缺失的情况"""
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    # 模拟缺失参数的状态
    initial_state = {
        "job_id": "test-002",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                # thickness_mm 和 material 缺失
            }
        ]
    }
    
    # 执行 check_params 阶段
    result_state = await orchestrator._stage_check_params(initial_state)
    
    # 验证结果
    assert result_state["stage"] == "check_params"
    assert len(result_state["missing_params"]) == 2
    assert result_state["interaction_prompt"] != ""
    
    # 验证缺失的参数
    param_names = [p["param_name"] for p in result_state["missing_params"]]
    assert "thickness_mm" in param_names
    assert "material" in param_names


@pytest.mark.asyncio
async def test_orchestrator_with_user_input():
    """测试用户补充参数的情况"""
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    # 第一次检查：参数缺失
    initial_state = {
        "job_id": "test-003",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
            }
        ]
    }
    
    result_state = await orchestrator._stage_check_params(initial_state)
    assert len(result_state["missing_params"]) == 2
    
    # 用户补充参数
    result_state["user_input"] = {
        "UP01": {
            "thickness_mm": 30,
            "material": "P20"
        }
    }
    
    # 第二次检查：参数完整
    result_state = await orchestrator._stage_check_params(result_state)
    assert result_state["missing_params"] == []
    
    # 验证参数已更新
    updated_feature = result_state["features"][0]
    assert updated_feature["thickness_mm"] == 30
    assert updated_feature["material"] == "P20"


@pytest.mark.asyncio
async def test_orchestrator_should_wait_for_input():
    """测试条件分支判断"""
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    # 有缺失参数
    state_with_missing = {
        "missing_params": [{"param_name": "thickness_mm"}]
    }
    assert orchestrator._should_wait_for_input(state_with_missing) == "wait"
    
    # 无缺失参数
    state_complete = {
        "missing_params": []
    }
    assert orchestrator._should_wait_for_input(state_complete) == "continue"


@pytest.mark.asyncio
async def test_orchestrator_waiting_input_stage():
    """测试等待用户输入阶段"""
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    state = {
        "job_id": "test-004",
        "missing_params": [
            {
                "subgraph_id": "UP01",
                "param_name": "thickness_mm",
                "param_label": "厚度(mm)"
            }
        ],
        "interaction_prompt": "请补充参数"
    }
    
    # 执行 waiting_input 阶段
    result_state = await orchestrator._stage_waiting_input(state)
    
    # 验证结果
    assert result_state["stage"] == "waiting_input"
    assert result_state["job_id"] == "test-004"


@pytest.mark.asyncio
async def test_orchestrator_multiple_features():
    """测试多个特征的参数检查"""
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    initial_state = {
        "job_id": "test-005",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                # 缺失 2 个参数
            },
            {
                "subgraph_id": "UP02",
                "volume_mm3": 2000,
                "thickness_mm": 50,
                # 缺失 1 个参数
            },
            {
                "subgraph_id": "CORE01",
                "volume_mm3": 1500,
                "material": "718"
                # 缺失 1 个参数
            }
        ]
    }
    
    result_state = await orchestrator._stage_check_params(initial_state)
    
    # 验证结果
    assert len(result_state["missing_params"]) == 4
    
    # 验证子图分组
    subgraph_ids = [p["subgraph_id"] for p in result_state["missing_params"]]
    assert "UP01" in subgraph_ids
    assert "UP02" in subgraph_ids
    assert "CORE01" in subgraph_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
