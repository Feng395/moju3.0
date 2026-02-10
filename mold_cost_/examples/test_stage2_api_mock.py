"""
阶段2 API 测试脚本（Mock 模式）
负责人：人员B2

功能：
使用 Mock 数据测试 API，不依赖真实数据库

使用方法：
    python examples/test_stage2_api_mock.py
"""
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.interaction_agent import InteractionAgent


async def test_complete_workflow():
    """测试完整的审核流程（使用 Mock）"""
    
    print("=" * 60)
    print("阶段2 API 测试（Mock 模式）")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    agent = InteractionAgent()
    job_id = f"test-job-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    user_id = "test_user_001"
    
    # Mock 数据库会话
    mock_db = AsyncMock()
    
    # Mock 依赖
    with patch.object(agent, '_review_repo') as mock_repo, \
         patch.object(agent, '_redis_client') as mock_redis, \
         patch.object(agent, '_ws_manager') as mock_ws:
        
        # ========== Mock ReviewRepository ==========
        mock_repo.get_all_review_data = AsyncMock(return_value={
            "features": [
                {
                    "feature_id": 1,
                    "subgraph_id": "SG001",
                    "job_id": job_id,
                    "name": "UP01",
                    "material": "P20",
                    "thickness_mm": 10.0,
                    "length_mm": 100.0,
                    "width_mm": 50.0
                },
                {
                    "feature_id": 2,
                    "subgraph_id": "SG001",
                    "job_id": job_id,
                    "name": "UP02",
                    "material": "718",
                    "thickness_mm": 15.0,
                    "length_mm": 120.0,
                    "width_mm": 60.0
                }
            ],
            "price_snapshots": [
                {
                    "snapshot_id": 1,
                    "job_id": job_id,
                    "item_name": "材料费",
                    "unit_price": 50.0
                }
            ],
            "process_snapshots": [
                {
                    "snapshot_id": 1,
                    "job_id": job_id,
                    "process_name": "线割",
                    "unit_price": 0.5
                }
            ],
            "subgraphs": [
                {
                    "subgraph_id": "SG001",
                    "job_id": job_id,
                    "part_name": "模具底板",
                    "material": "P20"
                }
            ]
        })
        
        mock_repo.update_all_review_data = AsyncMock()
        
        # ========== Mock Redis ==========
        saved_state = None
        
        async def mock_redis_set(key, value, ex=None, nx=False):
            nonlocal saved_state
            saved_state = value
            return True
        
        async def mock_redis_get(key):
            return saved_state
        
        async def mock_redis_exists(key):
            return 1 if saved_state else 0
        
        mock_redis.set = AsyncMock(side_effect=mock_redis_set)
        mock_redis.get = AsyncMock(side_effect=mock_redis_get)
        mock_redis.delete = AsyncMock()
        mock_redis.exists = AsyncMock(side_effect=mock_redis_exists)
        
        # ========== Mock WebSocket ==========
        mock_ws.broadcast = AsyncMock()
        
        # ========== 测试流程 ==========
        results = []
        
        # 1. 启动审核
        print("\n" + "=" * 60)
        print("测试1: 启动审核")
        print("=" * 60)
        
        result = await agent.start_review(job_id, mock_db)
        
        if result.status == "ok":
            print(f"✅ 启动审核成功")
            print(f"   消息: {result.message}")
            print(f"   Features: {result.data.get('features_count')}")
            print(f"   Subgraphs: {result.data.get('subgraphs_count')}")
            results.append(("启动审核", True))
        else:
            print(f"❌ 启动审核失败: {result.message}")
            results.append(("启动审核", False))
            return
        
        # 2. 第一次修改
        print("\n" + "=" * 60)
        print("测试2: 提交修改（第一次）")
        print("=" * 60)
        
        result = await agent.handle_modification(
            job_id,
            "将 UP01 的材质改为 718",
            user_id
        )
        
        if result.status == "ok":
            print(f"✅ 修改提交成功")
            print(f"   消息: {result.message}")
            print(f"   Modification ID: {result.data.get('modification_id')}")
            results.append(("提交修改1", True))
        else:
            print(f"❌ 修改提交失败: {result.message}")
            results.append(("提交修改1", False))
        
        # 3. 第二次修改
        print("\n" + "=" * 60)
        print("测试3: 提交修改（第二次）")
        print("=" * 60)
        
        result = await agent.handle_modification(
            job_id,
            "将 UP02 的厚度改为 20mm",
            user_id
        )
        
        if result.status == "ok":
            print(f"✅ 修改提交成功")
            print(f"   消息: {result.message}")
            results.append(("提交修改2", True))
        else:
            print(f"❌ 修改提交失败: {result.message}")
            results.append(("提交修改2", False))
        
        # 4. 查询状态
        print("\n" + "=" * 60)
        print("测试4: 查询状态")
        print("=" * 60)
        
        state = await agent._get_review_state(job_id)  # 使用私有方法
        
        if state:
            print(f"✅ 状态查询成功")
            print(f"   状态: {state.get('status')}")
            print(f"   修改次数: {len(state.get('modifications', []))}")
            results.append(("查询状态", True))
        else:
            print(f"❌ 状态查询失败")
            results.append(("查询状态", False))
        
        # 5. 确认修改
        print("\n" + "=" * 60)
        print("测试5: 确认修改")
        print("=" * 60)
        
        result = await agent.confirm_changes(job_id, user_id, mock_db)
        
        if result.status == "ok":
            print(f"✅ 确认修改成功")
            print(f"   消息: {result.message}")
            print(f"   修改次数: {result.data.get('modifications_count')}")
            results.append(("确认修改", True))
        else:
            print(f"❌ 确认修改失败: {result.message}")
            results.append(("确认修改", False))
        
        # ========== 打印测试结果 ==========
        print("\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        
        for name, success in results:
            status = "✅ 通过" if success else "❌ 失败"
            print(f"{name}: {status}")
        
        # 统计
        passed = sum(1 for _, success in results if success)
        total = len(results)
        print(f"\n总计: {passed}/{total} 通过")
        
        if passed == total:
            print("\n🎉 所有测试通过！")
            print("\n💡 提示:")
            print("  - Mock 模式测试成功")
            print("  - 核心逻辑工作正常")
            print("  - 需要修复数据库表结构以支持真实测试")
        else:
            print(f"\n⚠️  {total - passed} 个测试失败")


async def main():
    """主函数"""
    try:
        await test_complete_workflow()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 测试已取消")
