"""
并发审核测试
负责人：人员B2

测试场景：
1. 多用户同时启动审核
2. 同一任务的并发修改
3. 分布式锁竞争
4. Redis 并发访问
5. 数据库并发更新
"""
import pytest
import asyncio
from unittest.mock import AsyncMock
import json
from datetime import datetime

from agents.interaction_agent import InteractionAgent


class TestConcurrentReviewStart:
    """测试并发启动审核"""
    
    @pytest.mark.asyncio
    async def test_concurrent_start_same_job(self):
        """
        测试多个用户同时启动同一任务的审核
        
        预期：只有一个用户能成功获取锁
        """
        job_id = "test_job_concurrent_001"
        
        # 创建两个 Agent 实例（模拟两个用户）
        agent1 = InteractionAgent()
        agent2 = InteractionAgent()
        
        # 共享的 Redis 客户端（模拟真实场景）
        redis_client = AsyncMock()
        
        # 模拟锁竞争：第一次成功，第二次失败
        lock_results = [True, False]
        redis_client.set = AsyncMock(side_effect=lock_results)
        
        agent1._redis_client = redis_client
        agent2._redis_client = redis_client
        
        # 模拟其他依赖
        mock_repo = AsyncMock()
        mock_repo.get_all_review_data = AsyncMock(return_value={
            "features": [],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": []
        })
        
        agent1._review_repo = mock_repo
        agent2._review_repo = mock_repo
        
        redis_client.publish = AsyncMock()
        
        # 模拟数据库会话
        db_session1 = AsyncMock()
        db_session2 = AsyncMock()
        
        # 并发启动审核
        results = await asyncio.gather(
            agent1.start_review(job_id, db_session1),
            agent2.start_review(job_id, db_session2),
            return_exceptions=True
        )
        
        # 验证：一个成功，一个失败
        success_count = sum(1 for r in results if r.status == "ok")
        error_count = sum(1 for r in results if r.status == "error")
        
        assert success_count == 1
        assert error_count == 1
        
        # 验证错误消息
        error_result = next(r for r in results if r.status == "error")
        assert "正在被其他用户审核" in error_result.message
    
    @pytest.mark.asyncio
    async def test_concurrent_start_different_jobs(self):
        """
        测试多个用户同时启动不同任务的审核
        
        预期：所有用户都能成功
        """
        # 创建三个 Agent 实例
        agents = [InteractionAgent() for _ in range(3)]
        job_ids = [f"test_job_{i}" for i in range(3)]
        
        # 为每个 Agent 配置依赖
        for agent in agents:
            redis_client = AsyncMock()
            redis_client.set = AsyncMock(return_value=True)  # 都能获取锁
            redis_client.publish = AsyncMock()
            
            mock_repo = AsyncMock()
            mock_repo.get_all_review_data = AsyncMock(return_value={
                "features": [],
                "price_snapshots": [],
                "process_snapshots": [],
                "subgraphs": []
            })
            
            agent._redis_client = redis_client
            agent._review_repo = mock_repo
        
        # 并发启动审核
        db_sessions = [AsyncMock() for _ in range(3)]
        
        results = await asyncio.gather(
            *[
                agents[i].start_review(job_ids[i], db_sessions[i])
                for i in range(3)
            ],
            return_exceptions=True
        )
        
        # 验证：所有都成功
        assert all(r.status == "ok" for r in results)


class TestConcurrentModification:
    """测试并发修改"""
    
    @pytest.mark.asyncio
    async def test_concurrent_modify_same_job(self):
        """
        测试多个用户同时修改同一任务
        
        预期：所有修改都能成功（因为有锁保护）
        """
        job_id = "test_job_modify_001"
        
        # 创建两个 Agent 实例
        agent1 = InteractionAgent()
        agent2 = InteractionAgent()
        
        # 共享的 Redis 客户端
        redis_client = AsyncMock()
        redis_client.exists = AsyncMock(return_value=1)  # 锁存在
        redis_client.set = AsyncMock()
        redis_client.publish = AsyncMock()
        
        # 初始状态
        initial_state = {
            "status": "reviewing",
            "data": {
                "subgraphs": [
                    {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
                ]
            },
            "modifications": []
        }
        
        redis_client.get = AsyncMock(
            return_value=json.dumps(initial_state, ensure_ascii=False)
        )
        
        agent1._redis_client = redis_client
        agent2._redis_client = redis_client
        
        # 模拟 NLP 解析器
        nlp_parser1 = AsyncMock()
        nlp_parser1.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "UP01", "field": "material", "value": "718"}
        ])
        
        nlp_parser2 = AsyncMock()
        nlp_parser2.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "UP01", "field": "weight", "value": 7.0}
        ])
        
        agent1._nlp_parser = nlp_parser1
        agent2._nlp_parser = nlp_parser2
        
        # 并发修改
        results = await asyncio.gather(
            agent1.handle_modification(job_id, "修改材质", "user_1"),
            agent2.handle_modification(job_id, "修改重量", "user_2"),
            return_exceptions=True
        )
        
        # 验证：所有修改都成功
        assert all(r.status == "ok" for r in results)
    
    @pytest.mark.asyncio
    async def test_sequential_modifications_with_state_update(self):
        """
        测试顺序修改（模拟真实场景）
        
        流程：
        1. 用户1修改
        2. 状态更新
        3. 用户2修改
        4. 状态更新
        """
        job_id = "test_job_sequential_001"
        agent = InteractionAgent()
        
        # 模拟 Redis 客户端
        redis_client = AsyncMock()
        redis_client.exists = AsyncMock(return_value=1)
        redis_client.set = AsyncMock()
        redis_client.publish = AsyncMock()
        
        agent._redis_client = redis_client
        
        # 初始状态
        state = {
            "status": "reviewing",
            "data": {
                "subgraphs": [
                    {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
                ]
            },
            "modifications": []
        }
        
        # 模拟 NLP 解析器
        nlp_parser = AsyncMock()
        agent._nlp_parser = nlp_parser
        
        # === 第一次修改 ===
        redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        nlp_parser.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "UP01", "field": "material", "value": "718"}
        ])
        
        result1 = await agent.handle_modification(job_id, "修改材质", "user_1")
        assert result1.status == "ok"
        
        # 更新状态
        state["modifications"].append({"id": "mod_1"})
        state["data"]["subgraphs"][0]["material"] = "718"
        
        # === 第二次修改 ===
        redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        nlp_parser.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "UP01", "field": "weight", "value": 7.0}
        ])
        
        result2 = await agent.handle_modification(job_id, "修改重量", "user_2")
        assert result2.status == "ok"
        
        # 验证最终数据
        final_data = result2.data["modified_data"]
        assert final_data["subgraphs"][0]["material"] == "718"
        assert final_data["subgraphs"][0]["weight"] == 7.0


class TestDistributedLockCompetition:
    """测试分布式锁竞争"""
    
    @pytest.mark.asyncio
    async def test_lock_acquisition_race(self):
        """
        测试锁获取竞争
        
        场景：10个用户同时尝试获取同一个锁
        预期：只有一个成功
        """
        lock_key = "review:lock:test_job"
        
        # 创建10个 Agent 实例
        agents = [InteractionAgent() for _ in range(10)]
        
        # 共享的 Redis 客户端
        redis_client = AsyncMock()
        
        # 模拟锁竞争：只有第一个成功
        lock_results = [True] + [False] * 9
        redis_client.set = AsyncMock(side_effect=lock_results)
        
        # 配置所有 Agent
        for agent in agents:
            agent._redis_client = redis_client
        
        # 并发获取锁
        results = await asyncio.gather(
            *[agent._acquire_lock(lock_key) for agent in agents],
            return_exceptions=True
        )
        
        # 验证：只有一个成功
        success_count = sum(1 for r in results if r is True)
        assert success_count == 1
    
    @pytest.mark.asyncio
    async def test_lock_timeout_and_reacquisition(self):
        """
        测试锁超时和重新获取
        
        流程：
        1. 用户1获取锁
        2. 锁超时
        3. 用户2获取锁
        """
        lock_key = "review:lock:test_job"
        
        agent1 = InteractionAgent()
        agent2 = InteractionAgent()
        
        redis_client = AsyncMock()
        
        agent1._redis_client = redis_client
        agent2._redis_client = redis_client
        
        # 用户1获取锁（成功）
        redis_client.set = AsyncMock(return_value=True)
        result1 = await agent1._acquire_lock(lock_key)
        assert result1 is True
        
        # 模拟锁超时（用户2尝试获取）
        redis_client.set = AsyncMock(return_value=True)
        result2 = await agent2._acquire_lock(lock_key)
        assert result2 is True


class TestRedisConcurrentAccess:
    """测试 Redis 并发访问"""
    
    @pytest.mark.asyncio
    async def test_concurrent_state_read(self):
        """
        测试并发读取状态
        
        场景：多个用户同时读取同一个状态
        预期：所有读取都成功
        """
        job_id = "test_job_read_001"
        
        # 创建5个 Agent 实例
        agents = [InteractionAgent() for _ in range(5)]
        
        # 共享的 Redis 客户端
        redis_client = AsyncMock()
        
        state = {
            "status": "reviewing",
            "data": {"subgraphs": []},
            "modifications": []
        }
        
        redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        # 配置所有 Agent
        for agent in agents:
            agent._redis_client = redis_client
        
        # 并发读取
        results = await asyncio.gather(
            *[agent._get_review_state(job_id) for agent in agents],
            return_exceptions=True
        )
        
        # 验证：所有读取都成功
        assert all(r is not None for r in results)
        assert all(r["status"] == "reviewing" for r in results)
    
    @pytest.mark.asyncio
    async def test_concurrent_state_write(self):
        """
        测试并发写入状态
        
        场景：多个用户同时写入状态
        预期：所有写入都成功（Redis 保证原子性）
        """
        job_id = "test_job_write_001"
        
        # 创建5个 Agent 实例
        agents = [InteractionAgent() for _ in range(5)]
        
        # 共享的 Redis 客户端
        redis_client = AsyncMock()
        redis_client.set = AsyncMock()
        
        # 配置所有 Agent
        for agent in agents:
            agent._redis_client = redis_client
        
        # 不同的状态
        states = [
            {"status": "reviewing", "data": {}, "modifications": [{"id": f"mod_{i}"}]}
            for i in range(5)
        ]
        
        # 并发写入
        await asyncio.gather(
            *[
                agents[i]._save_review_state(job_id, states[i])
                for i in range(5)
            ],
            return_exceptions=True
        )
        
        # 验证：所有写入都被调用
        assert redis_client.set.call_count == 5


class TestDatabaseConcurrentUpdate:
    """测试数据库并发更新"""
    
    @pytest.mark.asyncio
    async def test_concurrent_confirm_different_jobs(self):
        """
        测试并发确认不同任务
        
        场景：多个用户同时确认不同任务
        预期：所有确认都成功
        """
        # 创建3个 Agent 实例
        agents = [InteractionAgent() for _ in range(3)]
        job_ids = [f"test_job_{i}" for i in range(3)]
        
        # 为每个 Agent 配置依赖
        for i, agent in enumerate(agents):
            redis_client = AsyncMock()
            redis_client.exists = AsyncMock(return_value=1)
            redis_client.get = AsyncMock(return_value=json.dumps({
                "status": "reviewing",
                "data": {"subgraphs": []},
                "modifications": [{"id": "mod_1"}]
            }, ensure_ascii=False))
            redis_client.delete = AsyncMock()
            redis_client.publish = AsyncMock()
            
            mock_repo = AsyncMock()
            mock_repo.update_all_review_data = AsyncMock()
            
            agent._redis_client = redis_client
            agent._review_repo = mock_repo
        
        # 并发确认
        db_sessions = [AsyncMock() for _ in range(3)]
        for session in db_sessions:
            session.commit = AsyncMock()
        
        results = await asyncio.gather(
            *[
                agents[i].confirm_changes(job_ids[i], f"user_{i}", db_sessions[i])
                for i in range(3)
            ],
            return_exceptions=True
        )
        
        # 验证：所有确认都成功
        assert all(r.status == "ok" for r in results)
        
        # 验证：所有数据库更新都被调用
        for agent in agents:
            agent._review_repo.update_all_review_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_isolation(self):
        """
        测试事务隔离
        
        场景：一个事务失败不影响其他事务
        """
        # 创建2个 Agent 实例
        agent1 = InteractionAgent()
        agent2 = InteractionAgent()
        
        # Agent1 配置（会失败）
        redis_client1 = AsyncMock()
        redis_client1.exists = AsyncMock(return_value=1)
        redis_client1.get = AsyncMock(return_value=json.dumps({
            "status": "reviewing",
            "data": {"subgraphs": []},
            "modifications": []
        }, ensure_ascii=False))
        
        mock_repo1 = AsyncMock()
        mock_repo1.update_all_review_data = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        agent1._redis_client = redis_client1
        agent1._review_repo = mock_repo1
        
        # Agent2 配置（会成功）
        redis_client2 = AsyncMock()
        redis_client2.exists = AsyncMock(return_value=1)
        redis_client2.get = AsyncMock(return_value=json.dumps({
            "status": "reviewing",
            "data": {"subgraphs": []},
            "modifications": []
        }, ensure_ascii=False))
        redis_client2.delete = AsyncMock()
        redis_client2.publish = AsyncMock()
        
        mock_repo2 = AsyncMock()
        mock_repo2.update_all_review_data = AsyncMock()
        
        agent2._redis_client = redis_client2
        agent2._review_repo = mock_repo2
        
        # 并发确认
        db_session1 = AsyncMock()
        db_session1.commit = AsyncMock()
        db_session1.rollback = AsyncMock()
        
        db_session2 = AsyncMock()
        db_session2.commit = AsyncMock()
        
        results = await asyncio.gather(
            agent1.confirm_changes("job_1", "user_1", db_session1),
            agent2.confirm_changes("job_2", "user_2", db_session2),
            return_exceptions=True
        )
        
        # 验证：一个失败，一个成功
        assert results[0].status == "error"
        assert results[1].status == "ok"
        
        # 验证：失败的事务回滚
        db_session1.rollback.assert_called_once()
        
        # 验证：成功的事务提交
        db_session2.commit.assert_called_once()


class TestStressTest:
    """压力测试"""
    
    @pytest.mark.asyncio
    async def test_high_concurrency_review_start(self):
        """
        测试高并发启动审核
        
        场景：50个用户同时启动不同任务
        """
        num_users = 50
        
        # 创建50个 Agent 实例
        agents = [InteractionAgent() for _ in range(num_users)]
        job_ids = [f"test_job_{i}" for i in range(num_users)]
        
        # 为每个 Agent 配置依赖
        for agent in agents:
            redis_client = AsyncMock()
            redis_client.set = AsyncMock(return_value=True)
            redis_client.publish = AsyncMock()
            
            mock_repo = AsyncMock()
            mock_repo.get_all_review_data = AsyncMock(return_value={
                "features": [],
                "price_snapshots": [],
                "process_snapshots": [],
                "subgraphs": []
            })
            
            agent._redis_client = redis_client
            agent._review_repo = mock_repo
        
        # 并发启动
        db_sessions = [AsyncMock() for _ in range(num_users)]
        
        start_time = asyncio.get_event_loop().time()
        
        results = await asyncio.gather(
            *[
                agents[i].start_review(job_ids[i], db_sessions[i])
                for i in range(num_users)
            ],
            return_exceptions=True
        )
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # 验证：所有都成功
        success_count = sum(1 for r in results if r.status == "ok")
        assert success_count == num_users
        
        # 性能验证：平均每个请求 < 100ms
        avg_time = duration / num_users
        print(f"\n高并发测试：{num_users}个用户，总耗时{duration:.2f}秒，平均{avg_time*1000:.2f}ms/请求")
        assert avg_time < 0.1  # 100ms


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
