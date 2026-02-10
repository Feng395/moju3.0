"""
Orchestrator 与 InteractionAgent 集成示例
展示完整的参数检查和用户交互流程
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.orchestrator_agent import OrchestratorAgent


async def example_complete_workflow():
    """示例 1: 完整的工作流（参数完整）"""
    print("=" * 60)
    print("示例 1: 参数完整的工作流")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    # 模拟完整参数
    state = {
        "job_id": "demo-001",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                "thickness_mm": 30,
                "material": "P20"
            }
        ]
    }
    
    print(f"\n初始状态:")
    print(f"  Job ID: {state['job_id']}")
    print(f"  特征数: {len(state['features'])}")
    
    # 执行参数检查
    result = await orchestrator._stage_check_params(state)
    
    print(f"\n检查结果:")
    print(f"  阶段: {result['stage']}")
    print(f"  缺失参数: {len(result['missing_params'])}")
    
    # 判断是否需要等待
    decision = orchestrator._should_wait_for_input(result)
    print(f"  决策: {decision}")
    
    if decision == "continue":
        print(f"\n✅ 参数完整，继续执行工作流")
    else:
        print(f"\n⏸️  需要等待用户输入")


async def example_missing_params_workflow():
    """示例 2: 参数缺失的工作流"""
    print("\n" + "=" * 60)
    print("示例 2: 参数缺失的工作流")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    # 模拟缺失参数
    state = {
        "job_id": "demo-002",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                # thickness_mm 和 material 缺失
            }
        ]
    }
    
    print(f"\n初始状态:")
    print(f"  Job ID: {state['job_id']}")
    print(f"  特征数: {len(state['features'])}")
    
    # 执行参数检查
    result = await orchestrator._stage_check_params(state)
    
    print(f"\n检查结果:")
    print(f"  阶段: {result['stage']}")
    print(f"  缺失参数: {len(result['missing_params'])}")
    
    print(f"\n缺失参数详情:")
    for param in result["missing_params"]:
        print(f"  • {param['subgraph_id']}: {param['param_label']} ({param['param_name']})")
    
    print(f"\n用户提示:")
    print(f"{result['interaction_prompt']}")
    
    # 判断是否需要等待
    decision = orchestrator._should_wait_for_input(result)
    print(f"\n决策: {decision}")
    
    if decision == "wait":
        print(f"\n⏸️  进入等待用户输入阶段")
        result = await orchestrator._stage_waiting_input(result)
        print(f"  当前阶段: {result['stage']}")


async def example_user_input_workflow():
    """示例 3: 用户补充参数的完整流程"""
    print("\n" + "=" * 60)
    print("示例 3: 用户补充参数的完整流程")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    # 第一次检查：参数缺失
    state = {
        "job_id": "demo-003",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
            }
        ]
    }
    
    print(f"\n【第一次检查】")
    print(f"  Job ID: {state['job_id']}")
    
    result = await orchestrator._stage_check_params(state)
    
    print(f"  缺失参数: {len(result['missing_params'])}")
    for param in result["missing_params"]:
        print(f"    • {param['param_label']}")
    
    # 模拟用户输入
    print(f"\n【用户输入】")
    user_input = {
        "UP01": {
            "thickness_mm": 30,
            "material": "P20"
        }
    }
    print(f"  UP01.thickness_mm = 30")
    print(f"  UP01.material = P20")
    
    result["user_input"] = user_input
    
    # 第二次检查：参数完整
    print(f"\n【第二次检查】")
    result = await orchestrator._stage_check_params(result)
    
    print(f"  缺失参数: {len(result['missing_params'])}")
    
    decision = orchestrator._should_wait_for_input(result)
    print(f"  决策: {decision}")
    
    if decision == "continue":
        print(f"\n✅ 参数已完整，继续执行工作流")
        print(f"\n更新后的特征:")
        for feature in result["features"]:
            print(f"  {feature['subgraph_id']}:")
            print(f"    - 厚度: {feature.get('thickness_mm')} mm")
            print(f"    - 材质: {feature.get('material')}")


async def example_multiple_features():
    """示例 4: 多个特征的参数检查"""
    print("\n" + "=" * 60)
    print("示例 4: 多个特征的参数检查")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent(use_llm_for_interaction=False)
    
    state = {
        "job_id": "demo-004",
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
    
    print(f"\n初始状态:")
    print(f"  Job ID: {state['job_id']}")
    print(f"  特征数: {len(state['features'])}")
    
    result = await orchestrator._stage_check_params(state)
    
    print(f"\n检查结果:")
    print(f"  总缺失参数: {len(result['missing_params'])}")
    
    # 按子图分组显示
    grouped = {}
    for param in result["missing_params"]:
        subgraph_id = param["subgraph_id"]
        if subgraph_id not in grouped:
            grouped[subgraph_id] = []
        grouped[subgraph_id].append(param)
    
    print(f"\n按子图分组:")
    for subgraph_id, params in grouped.items():
        print(f"  📦 {subgraph_id}:")
        for param in params:
            print(f"    • {param['param_label']}")


async def main():
    """运行所有示例"""
    print("\n🚀 Orchestrator 与 InteractionAgent 集成示例\n")
    
    await example_complete_workflow()
    await example_missing_params_workflow()
    await example_user_input_workflow()
    await example_multiple_features()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
