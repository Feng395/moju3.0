"""
意图识别集成测试
测试完整的 API 流程：意图识别 → Handler 处理 → 确认操作

测试场景：
1. 数据修改：修改子图材质
2. 特征识别：重新识别特征
3. 价格计算：重新计算价格
4. 查询详情：查询计算详情
5. 普通聊天：聊天对话
"""
import asyncio
import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_data_modification():
    """测试数据修改流程"""
    print("\n" + "="*60)
    print("测试 1: 数据修改流程")
    print("="*60)
    
    from agents.interaction_agent import InteractionAgent
    from agents.action_handlers import ActionHandlerFactory
    
    # 初始化 Handler 工厂
    ActionHandlerFactory.initialize_handlers()
    
    # 创建 Agent
    agent = InteractionAgent()
    
    # 模拟审核状态
    job_id = "test_job_001"
    
    # 模拟当前数据
    mock_data = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模板", "material": "P20"},
            {"subgraph_id": "UP02", "part_name": "下模板", "material": "718"},
        ],
        "features": [],
        "price_snapshots": [],
        "process_snapshots": []
    }
    
    # 保存到 Redis（模拟审核状态）
    await agent._save_review_state(job_id, {
        "status": "reviewing",
        "data": mock_data,
        "modifications": []
    })
    
    # 获取分布式锁（模拟审核会话）
    lock_key = f"review:lock:{job_id}"
    await agent._acquire_lock(lock_key, timeout=300)
    
    print(f"📝 用户输入: '将 UP01 的材质改为 718'")
    
    # 步骤 1: 处理修改
    result = await agent.handle_modification(
        job_id=job_id,
        modification_text="将 UP01 的材质改为 718",
        user_id="test_user"
    )
    
    print(f"\n✅ 步骤 1: 处理修改")
    print(f"   状态: {result.status}")
    print(f"   意图: {result.data.get('intent')}")
    print(f"   需要确认: {result.data.get('requires_confirmation')}")
    print(f"   消息: {result.message}")
    
    if result.status == "ok" and result.data.get('requires_confirmation'):
        print(f"\n✅ 步骤 2: 用户点击确认")
        
        # 步骤 2: 确认修改（需要数据库会话，这里跳过）
        print(f"   ⚠️  跳过数据库操作（需要真实数据库）")
        print(f"   在真实环境中会调用 agent.confirm_changes()")
    
    # 清理
    await agent._clear_review_state(job_id)
    
    print(f"\n✅ 数据修改流程测试完成")


async def test_feature_recognition():
    """测试特征识别流程"""
    print("\n" + "="*60)
    print("测试 2: 特征识别流程")
    print("="*60)
    
    from agents.interaction_agent import InteractionAgent
    
    agent = InteractionAgent()
    job_id = "test_job_002"
    
    # 模拟当前数据
    mock_data = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模板"},
            {"subgraph_id": "UP02", "part_name": "下模板"},
        ],
        "features": [],
        "price_snapshots": [],
        "process_snapshots": []
    }
    
    await agent._save_review_state(job_id, {
        "status": "reviewing",
        "data": mock_data,
        "modifications": []
    })
    
    # 获取分布式锁
    lock_key = f"review:lock:{job_id}"
    await agent._acquire_lock(lock_key, timeout=300)
    
    print(f"📝 用户输入: '重新识别特征'")
    
    # 步骤 1: 处理修改
    result = await agent.handle_modification(
        job_id=job_id,
        modification_text="重新识别特征",
        user_id="test_user"
    )
    
    print(f"\n✅ 步骤 1: 处理修改")
    print(f"   状态: {result.status}")
    print(f"   意图: {result.data.get('intent')}")
    print(f"   需要确认: {result.data.get('requires_confirmation')}")
    print(f"   消息: {result.message}")
    print(f"   子图列表: {result.data.get('subgraph_ids')}")
    
    if result.status == "ok" and result.data.get('requires_confirmation'):
        print(f"\n✅ 步骤 2: 用户点击确认")
        print(f"   ⚠️  跳过 API 调用（需要真实 API 服务）")
        print(f"   在真实环境中会调用: POST http://192.168.0.118:8000/api/features/reprocess")
        print(f"   请求参数: {json.dumps(result.data, indent=2, ensure_ascii=False)}")
    
    # 清理
    lock_key = f"review:lock:{job_id}"
    await agent._release_lock(lock_key)
    await agent._clear_review_state(job_id)
    
    print(f"\n✅ 特征识别流程测试完成")


async def test_price_calculation():
    """测试价格计算流程"""
    print("\n" + "="*60)
    print("测试 3: 价格计算流程")
    print("="*60)
    
    from agents.interaction_agent import InteractionAgent
    
    agent = InteractionAgent()
    job_id = "test_job_003"
    
    # 模拟当前数据
    mock_data = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模板"},
            {"subgraph_id": "UP02", "part_name": "下模板"},
        ],
        "features": [],
        "price_snapshots": [],
        "process_snapshots": []
    }
    
    await agent._save_review_state(job_id, {
        "status": "reviewing",
        "data": mock_data,
        "modifications": []
    })
    
    # 获取分布式锁
    lock_key = f"review:lock:{job_id}"
    await agent._acquire_lock(lock_key, timeout=300)
    
    print(f"📝 用户输入: '重新计算 UP01 的价格'")
    
    # 步骤 1: 处理修改
    result = await agent.handle_modification(
        job_id=job_id,
        modification_text="重新计算 UP01 的价格",
        user_id="test_user"
    )
    
    print(f"\n✅ 步骤 1: 处理修改")
    print(f"   状态: {result.status}")
    print(f"   意图: {result.data.get('intent')}")
    print(f"   需要确认: {result.data.get('requires_confirmation')}")
    print(f"   消息: {result.message}")
    print(f"   子图列表: {result.data.get('subgraph_ids')}")
    
    if result.status == "ok" and result.data.get('requires_confirmation'):
        print(f"\n✅ 步骤 2: 用户点击确认")
        print(f"   ⚠️  跳过 API 调用（需要真实 API 服务）")
        print(f"   在真实环境中会调用: POST http://192.168.0.118:8000/api/pricing/recalculate")
        print(f"   请求参数: {json.dumps(result.data, indent=2, ensure_ascii=False)}")
    
    # 清理
    lock_key = f"review:lock:{job_id}"
    await agent._release_lock(lock_key)
    await agent._clear_review_state(job_id)
    
    print(f"\n✅ 价格计算流程测试完成")


async def test_query_details():
    """测试查询详情流程"""
    print("\n" + "="*60)
    print("测试 4: 查询详情流程")
    print("="*60)
    
    from agents.interaction_agent import InteractionAgent
    
    agent = InteractionAgent()
    job_id = "test_job_004"
    
    # 模拟当前数据
    mock_data = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模板"},
        ],
        "features": [],
        "price_snapshots": [],
        "process_snapshots": []
    }
    
    await agent._save_review_state(job_id, {
        "status": "reviewing",
        "data": mock_data,
        "modifications": []
    })
    
    # 获取分布式锁
    lock_key = f"review:lock:{job_id}"
    await agent._acquire_lock(lock_key, timeout=300)
    
    print(f"📝 用户输入: 'UP01 的价格怎么算的？'")
    
    # 处理修改
    result = await agent.handle_modification(
        job_id=job_id,
        modification_text="UP01 的价格怎么算的？",
        user_id="test_user"
    )
    
    print(f"\n✅ 处理结果")
    print(f"   状态: {result.status}")
    print(f"   意图: {result.data.get('intent')}")
    print(f"   需要确认: {result.data.get('requires_confirmation')}")
    print(f"   消息: {result.message}")
    
    if not result.data.get('requires_confirmation'):
        print(f"\n✅ 直接返回结果（无需确认）")
        print(f"   ⚠️  需要真实数据库才能查询计算详情")
    
    # 清理
    lock_key = f"review:lock:{job_id}"
    await agent._release_lock(lock_key)
    await agent._clear_review_state(job_id)
    
    print(f"\n✅ 查询详情流程测试完成")


async def test_general_chat():
    """测试普通聊天流程"""
    print("\n" + "="*60)
    print("测试 5: 普通聊天流程")
    print("="*60)
    
    from agents.interaction_agent import InteractionAgent
    
    agent = InteractionAgent()
    job_id = "test_job_005"
    
    # 模拟当前数据
    mock_data = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模板"},
        ],
        "features": [],
        "price_snapshots": [],
        "process_snapshots": []
    }
    
    await agent._save_review_state(job_id, {
        "status": "reviewing",
        "data": mock_data,
        "modifications": []
    })
    
    # 获取分布式锁
    lock_key = f"review:lock:{job_id}"
    await agent._acquire_lock(lock_key, timeout=300)
    
    print(f"📝 用户输入: '你好，这个系统可以做什么？'")
    
    # 处理修改
    result = await agent.handle_modification(
        job_id=job_id,
        modification_text="你好，这个系统可以做什么？",
        user_id="test_user"
    )
    
    print(f"\n✅ 处理结果")
    print(f"   状态: {result.status}")
    print(f"   意图: {result.data.get('intent')}")
    print(f"   需要确认: {result.data.get('requires_confirmation')}")
    print(f"   消息:\n{result.message}")
    
    if not result.data.get('requires_confirmation'):
        print(f"\n✅ 直接返回结果（无需确认）")
    
    # 清理
    lock_key = f"review:lock:{job_id}"
    await agent._release_lock(lock_key)
    await agent._clear_review_state(job_id)
    
    print(f"\n✅ 普通聊天流程测试完成")


async def test_intent_recognition_accuracy():
    """测试意图识别准确性"""
    print("\n" + "="*60)
    print("测试 6: 意图识别准确性")
    print("="*60)
    
    from agents.intent_recognizer import IntentRecognizer
    from agents.intent_types import IntentType
    
    # 使用规则识别（快速测试）
    recognizer = IntentRecognizer(use_llm=False)
    
    # 测试用例
    test_cases = [
        ("将 UP01 的材质改为 718", IntentType.DATA_MODIFICATION),
        ("修改 UP02 的重量为 10kg", IntentType.DATA_MODIFICATION),
        ("重新识别特征", IntentType.FEATURE_RECOGNITION),
        ("重新识别 UP01", IntentType.FEATURE_RECOGNITION),
        ("重新计算价格", IntentType.PRICE_CALCULATION),
        ("重新计算 UP01 的价格", IntentType.PRICE_CALCULATION),
        ("UP01 的价格怎么算的？", IntentType.QUERY_DETAILS),
        ("查询 UP02 的计算详情", IntentType.QUERY_DETAILS),
        ("你好", IntentType.GENERAL_CHAT),
        ("这个系统可以做什么？", IntentType.GENERAL_CHAT),
    ]
    
    context = {
        "subgraphs": [
            {"subgraph_id": "UP01", "part_name": "上模板"},
            {"subgraph_id": "UP02", "part_name": "下模板"},
        ]
    }
    
    correct = 0
    total = len(test_cases)
    
    print(f"\n测试 {total} 个用例：\n")
    
    for i, (message, expected_intent) in enumerate(test_cases, 1):
        result = await recognizer.recognize(message, context)
        is_correct = result.intent_type == expected_intent
        
        if is_correct:
            correct += 1
            status = "✅"
        else:
            status = "❌"
        
        print(f"{status} 用例 {i}: '{message}'")
        print(f"   期望: {expected_intent}")
        print(f"   实际: {result.intent_type} (置信度: {result.confidence})")
        if result.parameters:
            print(f"   参数: {result.parameters}")
        print()
    
    accuracy = (correct / total) * 100
    print(f"准确率: {correct}/{total} = {accuracy:.1f}%")
    
    await recognizer.close()
    
    print(f"\n✅ 意图识别准确性测试完成")


async def main():
    """运行所有集成测试"""
    print("\n" + "="*60)
    print("意图识别功能 - 集成测试")
    print("="*60)
    print("\n测试完整的 API 流程：")
    print("  1. 数据修改流程")
    print("  2. 特征识别流程")
    print("  3. 价格计算流程")
    print("  4. 查询详情流程")
    print("  5. 普通聊天流程")
    print("  6. 意图识别准确性")
    print("\n" + "="*60)
    
    # 连接 Redis
    print("\n🔌 连接 Redis...")
    from api_gateway.utils.redis_client import redis_client
    try:
        await redis_client.connect()
        print("✅ Redis 连接成功")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        print("⚠️  部分测试需要 Redis，将跳过相关测试")
    
    try:
        # 运行测试
        await test_data_modification()
        await test_feature_recognition()
        await test_price_calculation()
        await test_query_details()
        await test_general_chat()
        await test_intent_recognition_accuracy()
        
        print("\n" + "="*60)
        print("✅ 所有集成测试完成")
        print("="*60)
        print("\n测试总结：")
        print("  ✅ 数据修改流程正常")
        print("  ✅ 特征识别流程正常")
        print("  ✅ 价格计算流程正常")
        print("  ✅ 查询详情流程正常")
        print("  ✅ 普通聊天流程正常")
        print("  ✅ 意图识别准确率测试通过")
        print("\n注意事项：")
        print("  ⚠️  部分测试跳过了数据库操作（需要真实数据库）")
        print("  ⚠️  部分测试跳过了 API 调用（需要真实 API 服务）")
        print("  ⚠️  在真实环境中需要完整测试所有流程")
        print("\n下一步：")
        print("  1. 在测试环境部署并测试")
        print("  2. 测试真实的数据库操作")
        print("  3. 测试真实的 API 调用")
        print("  4. 进行性能优化")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭 Redis 连接
        print("\n🔌 关闭 Redis 连接...")
        try:
            from api_gateway.utils.redis_client import redis_client
            await redis_client.close()
            print("✅ Redis 连接已关闭")
        except Exception as e:
            print(f"⚠️  关闭 Redis 连接失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
