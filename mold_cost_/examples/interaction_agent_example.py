"""
InteractionAgent 使用示例
展示如何使用基于 LangGraph 的交互Agent
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.interaction_agent import InteractionAgent


async def example_basic():
    """基础示例：检查参数缺失"""
    print("=" * 60)
    print("示例 1: 基础参数检查")
    print("=" * 60)
    
    agent = InteractionAgent(use_llm=False)
    
    # 模拟上下文：缺少厚度和材质
    context = {
        "job_id": "test-001",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                # thickness_mm 缺失
                # material 缺失
            },
            {
                "subgraph_id": "UP02",
                "volume_mm3": 2000,
                "thickness_mm": 50,
                # material 缺失
            }
        ]
    }
    
    result = await agent.process(context)
    
    print(f"\n状态: {result.status}")
    print(f"消息: {result.message}")
    
    if result.status == "need_input":
        print(f"\n缺失参数:")
        for param in result.data["missing_params"]:
            print(f"  • {param['subgraph_id']}: {param['param_label']}")
        
        print(f"\n用户提示:\n{result.data['prompt']}")


async def example_with_user_input():
    """示例 2: 用户补充参数"""
    print("\n" + "=" * 60)
    print("示例 2: 用户补充参数")
    print("=" * 60)
    
    agent = InteractionAgent(use_llm=False)
    
    # 第一次检查
    context = {
        "job_id": "test-002",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
            }
        ]
    }
    
    result1 = await agent.process(context)
    print(f"\n第一次检查: {result1.status}")
    print(f"缺失参数: {len(result1.data['missing_params'])} 个")
    
    # 用户补充参数
    context["user_input"] = {
        "UP01": {
            "thickness_mm": 30,
            "material": "P20"
        }
    }
    
    result2 = await agent.process(context)
    print(f"\n第二次检查: {result2.status}")
    print(f"消息: {result2.message}")
    
    if result2.status == "ok":
        print(f"\n✅ 参数已完整!")
        print(f"更新后的特征: {result2.data['features']}")


async def example_with_llm():
    """示例 3: 使用 LLM 生成友好提示"""
    print("\n" + "=" * 60)
    print("示例 3: 使用 LLM 生成友好提示")
    print("=" * 60)
    
    # 检查是否配置了 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  未配置 OPENAI_API_KEY，跳过此示例")
        return
    
    agent = InteractionAgent(use_llm=True)
    
    context = {
        "job_id": "test-003",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                "needs_wire_cut": True
            }
        ]
    }
    
    result = await agent.process(context)
    
    print(f"\n状态: {result.status}")
    print(f"\nAI 生成的提示:\n{result.data['prompt']}")


async def example_complex_workflow():
    """示例 4: 复杂工作流（多个子图）"""
    print("\n" + "=" * 60)
    print("示例 4: 复杂工作流")
    print("=" * 60)
    
    agent = InteractionAgent(use_llm=False)
    
    context = {
        "job_id": "test-004",
        "features": [
            {
                "subgraph_id": "UP01",
                "volume_mm3": 1000,
                "needs_wire_cut": True
            },
            {
                "subgraph_id": "UP02",
                "volume_mm3": 2000,
                "thickness_mm": 50
            },
            {
                "subgraph_id": "CORE01",
                "volume_mm3": 1500,
                "material": "718"
            }
        ]
    }
    
    result = await agent.process(context)
    
    print(f"\n状态: {result.status}")
    print(f"\n缺失参数统计:")
    
    # 按子图分组显示
    grouped = {}
    for param in result.data["missing_params"]:
        subgraph_id = param["subgraph_id"]
        if subgraph_id not in grouped:
            grouped[subgraph_id] = []
        grouped[subgraph_id].append(param)
    
    for subgraph_id, params in grouped.items():
        print(f"\n  📦 {subgraph_id}:")
        for param in params:
            print(f"    • {param['param_label']} ({param['param_type']})")


async def main():
    """运行所有示例"""
    print("\n🚀 InteractionAgent 示例演示\n")
    
    await example_basic()
    await example_with_user_input()
    await example_with_llm()
    await example_complex_workflow()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
