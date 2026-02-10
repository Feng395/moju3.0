"""
阶段2测试：锁自动续期 + 状态保留
负责人：人员B2

测试内容：
1. 锁自动续期功能
2. COMPLETED 状态保留
3. COMPLETED 状态权限控制

注意：需要 Redis 服务运行
"""
import pytest
import asyncio
from datetime import datetime
from agents.interaction_agent import InteractionAgent
from agents.review_status import ReviewStatus


@pytest.fixture(scope="module")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def setup_redis():
    """设置 Redis 连接（模块级别）"""
    from api_gateway.utils.redis_client import redis_client
    
    # 连接 Redis
    await redis_client.connect()
    
    yield redis_client
    
    # 清理测试数据
    test_keys = [
        "review:lock:test-*",
        "review:state:test-*"
    ]
    
    for pattern in test_keys:
        keys = await redis_client.client.keys(pattern)
        if keys:
            await redis_client.client.delete(*keys)
    
    # 关闭连接
    await redis_client.close()


class TestLockRenewal:
    """测试锁自动续期"""
    
    @pytest.mark.asyncio
    async def test_lock_renewal_on_modification(self):
        """测试修改时自动续期锁"""
        agent = InteractionAgent()
        job_id = "test-lock-renewal-001"
        lock_key = f"review:lock:{job_id}"
        
        # 1. 获取锁
        acquired = await agent._acquire_lock(lock_key, timeout=5)
        assert acquired, "应该成功获取锁"
        
        # 2. 等待 3 秒
        await asyncio.sleep(3)
        
        # 3. 续期锁
        renewed = await agent._renew_lock(lock_key, timeout=10)
        assert renewed, "应该成功续期锁"
        
        # 4. 检查锁仍然存在
        exists = await agent._check_lock(lock_key)
        assert exists, "锁应该仍然存在"
        
        # 5. 清理
        await agent._release_lock(lock_key)
    
    @pytest.mark.asyncio
    async def test_lock_renewal_after_expiry(self):
        """测试锁过期后无法续期"""
        agent = InteractionAgent()
        job_id = "test-lock-expiry-001"
        lock_key = f"review:lock:{job_id}"
        
        # 1. 获取锁（1秒超时）
        acquired = await agent._acquire_lock(lock_key, timeout=1)
        assert acquired, "应该成功获取锁"
        
        # 2. 等待锁过期
        await asyncio.sleep(2)
        
        # 3. 尝试续期（应该失败）
        renewed = await agent._renew_lock(lock_key, timeout=10)
        assert not renewed, "锁已过期，不应该续期成功"
        
        # 4. 清理
        await agent.redis_client.delete(lock_key)
    
    @pytest.mark.asyncio
    async def test_lock_renewal_extends_timeout(self):
        """测试续期确实延长了超时时间"""
        agent = InteractionAgent()
        job_id = "test-lock-extend-001"
        lock_key = f"review:lock:{job_id}"
        
        # 1. 获取锁（2秒超时）
        acquired = await agent._acquire_lock(lock_key, timeout=2)
        assert acquired, "应该成功获取锁"
        
        # 2. 等待 1 秒
        await asyncio.sleep(1)
        
        # 3. 续期到 5 秒
        renewed = await agent._renew_lock(lock_key, timeout=5)
        assert renewed, "应该成功续期"
        
        # 4. 再等待 2 秒（原本应该过期）
        await asyncio.sleep(2)
        
        # 5. 锁应该仍然存在（因为续期了）
        exists = await agent._check_lock(lock_key)
        assert exists, "锁应该仍然存在（已续期）"
        
        # 6. 清理
        await agent._release_lock(lock_key)


class TestStatusRetention:
    """测试状态保留"""
    
    @pytest.mark.asyncio
    async def test_completed_status_retention(self):
        """测试 COMPLETED 状态保留"""
        agent = InteractionAgent()
        job_id = "test-status-retention-001"
        
        # 1. 保存 COMPLETED 状态
        state = {
            "status": ReviewStatus.COMPLETED,
            "data": {"test": "data"},
            "modifications": [],
            "completed_at": datetime.utcnow().isoformat()
        }
        
        await agent._save_review_state(job_id, state, ex=3600)
        
        # 2. 读取状态
        retrieved_state = await agent._get_review_state(job_id)
        
        assert retrieved_state is not None, "状态应该存在"
        assert retrieved_state["status"] == ReviewStatus.COMPLETED
        assert "completed_at" in retrieved_state
        
        # 3. 清理
        await agent._clear_review_state(job_id)
    
    @pytest.mark.asyncio
    async def test_completed_status_prevents_modification(self):
        """测试 COMPLETED 状态阻止修改"""
        agent = InteractionAgent()
        job_id = "test-status-prevent-001"
        
        # 1. 保存 COMPLETED 状态
        state = {
            "status": ReviewStatus.COMPLETED,
            "data": {"subgraphs": []},
            "modifications": [],
            "completed_at": datetime.utcnow().isoformat()
        }
        
        await agent._save_review_state(job_id, state)
        
        # 2. 尝试修改（应该被拒绝）
        result = await agent.handle_modification(
            job_id=job_id,
            modification_text="将 UP01 的材质改为 718",
            user_id="test-user"
        )
        
        assert result.status == "error", "应该返回错误"
        assert "已完成" in result.message, "错误消息应该提示已完成"
        
        # 3. 清理
        await agent._clear_review_state(job_id)
    
    @pytest.mark.asyncio
    async def test_completed_status_allows_query(self):
        """测试 COMPLETED 状态允许查询"""
        agent = InteractionAgent()
        job_id = "test-status-query-001"
        
        # 1. 保存 COMPLETED 状态
        state = {
            "status": ReviewStatus.COMPLETED,
            "data": {"subgraphs": [{"subgraph_id": "UP01"}]},
            "modifications": [{"text": "修改1"}],
            "completed_at": datetime.utcnow().isoformat()
        }
        
        await agent._save_review_state(job_id, state)
        
        # 2. 查询状态（应该成功）
        retrieved_state = await agent.get_review_state(job_id)
        
        assert retrieved_state is not None, "应该能查询到状态"
        assert retrieved_state["status"] == ReviewStatus.COMPLETED
        assert len(retrieved_state["modifications"]) == 1
        
        # 3. 清理
        await agent._clear_review_state(job_id)


class TestStatusTransitions:
    """测试状态转换"""
    
    @pytest.mark.asyncio
    async def test_reviewing_to_completed(self):
        """测试从 REVIEWING 到 COMPLETED 的转换"""
        agent = InteractionAgent()
        job_id = "test-transition-001"
        
        # 1. 初始状态：REVIEWING
        state = {
            "status": ReviewStatus.REVIEWING,
            "data": {"subgraphs": []},
            "modifications": []
        }
        
        await agent._save_review_state(job_id, state)
        
        # 2. 模拟 confirm（状态应该变为 COMPLETED）
        state["status"] = ReviewStatus.COMPLETED
        state["completed_at"] = datetime.utcnow().isoformat()
        
        await agent._save_review_state(job_id, state, ex=3600)
        
        # 3. 验证状态
        retrieved_state = await agent._get_review_state(job_id)
        
        assert retrieved_state["status"] == ReviewStatus.COMPLETED
        assert "completed_at" in retrieved_state
        
        # 4. 清理
        await agent._clear_review_state(job_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
