"""
测试 NC Agent 是否正确注册到 Orchestrator
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.orchestrator_agent import OrchestratorAgent
from agents.cad_agent import CADAgent
from agents.nc_time_agent import NCTimeAgent
from agents.pricing_agent import PricingAgent
from shared.progress_publisher import ProgressPublisher
from shared.mcp_client import MCPClient


async def test_nc_agent_registration():
    """测试 NC Agent 注册"""
    print("=" * 80)
    print("测试 NC Agent 注册")
    print("=" * 80)
    
    # 1. 创建进度发布器
    print("\n1. 创建进度发布器...")
    progress_publisher = ProgressPublisher()
    print("✅ 进度发布器创建成功")
    
    # 2. 创建编排器
    print("\n2. 创建编排器...")
    orchestrator = OrchestratorAgent(progress_publisher=progress_publisher)
    print(f"✅ 编排器创建成功")
    print(f"   - nc_time_agent: {orchestrator.nc_time_agent}")
    
    # 3. 创建 MCP 客户端
    print("\n3. 创建 MCP 客户端...")
    mcp_url = os.getenv("CAD_PRICE_SEARCH_MCP_URL", "http://localhost:8200")
    mcp_client = MCPClient(base_url=mcp_url, timeout=7200)
    print(f"✅ MCP 客户端创建成功: {mcp_url}")
    
    # 4. 创建各个 Agent
    print("\n4. 创建各个 Agent...")
    
    print("   - 创建 CADAgent...")
    cad_agent = CADAgent(
        mcp_client=mcp_client,
        progress_publisher=progress_publisher
    )
    print("   ✅ CADAgent 创建成功")
    
    print("   - 创建 NCTimeAgent...")
    nc_time_agent = NCTimeAgent(
        progress_publisher=progress_publisher
    )
    print(f"   ✅ NCTimeAgent 创建成功")
    print(f"      - nc_agent_url: {nc_time_agent.nc_agent_url}")
    print(f"      - timeout: {nc_time_agent.timeout}秒")
    
    print("   - 创建 PricingAgent...")
    pricing_agent = PricingAgent(
        price_search_mcp_client=mcp_client,
        progress_publisher=progress_publisher
    )
    print("   ✅ PricingAgent 创建成功")
    
    # 5. 注册 Agent 到编排器
    print("\n5. 注册 Agent 到编排器...")
    orchestrator.register_agents(
        cad_agent=cad_agent,
        nc_time_agent=nc_time_agent,
        pricing_agent=pricing_agent
    )
    print("✅ Agent 注册成功")
    
    # 6. 验证注册结果
    print("\n6. 验证注册结果...")
    print(f"   - cad_agent: {orchestrator.cad_agent is not None} ({'✅' if orchestrator.cad_agent else '❌'})")
    print(f"   - nc_time_agent: {orchestrator.nc_time_agent is not None} ({'✅' if orchestrator.nc_time_agent else '❌'})")
    print(f"   - pricing_agent: {orchestrator.pricing_agent is not None} ({'✅' if orchestrator.pricing_agent else '❌'})")
    
    # 7. 检查 NC Agent 配置
    print("\n7. 检查 NC Agent 配置...")
    if orchestrator.nc_time_agent:
        print(f"   ✅ NC Agent 已注册")
        print(f"      - URL: {orchestrator.nc_time_agent.nc_agent_url}")
        print(f"      - 超时: {orchestrator.nc_time_agent.timeout}秒")
        print(f"      - 进度发布器: {orchestrator.nc_time_agent.progress_publisher is not None}")
    else:
        print(f"   ❌ NC Agent 未注册")
    
    # 8. 总结
    print("\n" + "=" * 80)
    print("测试总结:")
    print("=" * 80)
    
    all_registered = (
        orchestrator.cad_agent is not None and
        orchestrator.nc_time_agent is not None and
        orchestrator.pricing_agent is not None
    )
    
    if all_registered:
        print("✅ 所有 Agent 都已正确注册！")
        print("\n下一步：")
        print("1. 启动 orchestrator_worker")
        print("2. 提交一个新任务")
        print("3. 观察日志，确认 NC Agent 被调用")
        print("4. 运行 verify_nc_data.py 验证数据写入")
    else:
        print("❌ 部分 Agent 未注册，请检查代码")
    
    # 关闭进度发布器
    progress_publisher.close()


if __name__ == "__main__":
    asyncio.run(test_nc_agent_registration())
