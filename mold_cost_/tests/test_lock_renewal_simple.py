"""
阶段2简化测试：锁自动续期 + 状态保留（使用 Mock）
负责人：人员B2

测试内容：
1. 锁续期逻辑测试
2. 状态保留逻辑测试
3. 状态权限检查测试

注意：使用 Mock，不需要真实 Redis
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from agents.interaction_agent import InteractionAgent
from agents.review_status import ReviewStatus


class TestLockRenewalLogic:
    """测试锁续期逻辑（使用 Mock）"""
    
    @pytest.mark.asyncio
    async def test_renew_lock_success(self):
        """测试成功续期锁"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        agent._redis_client = MagicMock()
        agent._redis_client.exists = AsyncMock(return_value=1)  # 锁存在
        agent._redis_client.expire = AsyncMock(return_value=True)
        
        # 测试续期
        result = await agent._renew_lock("test-lock", timeout=300)
        
        assert result is True, "应该成功续期"
        agent._redis_client.exists.assert_called_once_with("test-lock")
        agent._redis_client.expire.assert_called_once_with("test-lock", 300)
    
    @pytest.mark.asyncio
    async def test_renew_lock_not_exists(self):
        """测试锁不存在时无法续期"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        agent._redis_client = MagicMock()
        agent._redis_client.exists = AsyncMock(return_value=0)  # 锁不存在
        
        # 测试续期
        result = await agent._renew_lock("test-lock", timeout=300)
        
        assert result is False, "锁不存在，不应该续期成功"
        agent._redis_client.exists.assert_called_once_with("test-lock")
    
    @pytest.mark.asyncio
    async def test_acquire_lock_success(self):
        """测试成功获取锁"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        agent._redis_client = MagicMock()
        agent._redis_client.set = AsyncMock(return_value=True)
        
        # 测试获取锁
        result = await agent._acquire_lock("test-lock", timeout=300)
        
        assert result is True, "应该成功获取锁"
        agent._redis_client.set.assert_called_once_with(
            "test-lock", "locked", ex=300, nx=True
        )
    
    @pytest.mark.asyncio
    async def test_acquire_lock_already_locked(self):
        """测试锁已被占用"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        agent._redis_client = MagicMock()
        agent._redis_client.set = AsyncMock(return_value=False)  # 锁已存在
        
        # 测试获取锁
        result = await agent._acquire_lock("test-lock", timeout=300)
        
        assert result is False, "锁已被占用，不应该获取成功"


class TestStatusRetentionLogic:
    """测试状态保留逻辑（使用 Mock）"""
    
    @pytest.mark.asyncio
    async def test_save_completed_status(self):
        """测试保存 COMPLETED 状态"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        agent._redis_client = MagicMock()
        agent._redis_client.set = AsyncMock(return_value=True)
        
        # 测试保存状态
        state = {
            "status": ReviewStatus.COMPLETED,
            "data": {"test": "data"},
            "completed_at": datetime.utcnow().isoformat()
        }
        
        await agent._save_review_state("test-job", state, ex=3600)
        
        # 验证调用
        agent._redis_client.set.assert_called_once()
        call_args = agent._redis_client.set.call_args
        
        assert call_args[0][0] == "review:state:test-job"
        assert call_args[1]["ex"] == 3600
    
    @pytest.mark.asyncio
    async def test_get_completed_status(self):
        """测试获取 COMPLETED 状态"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        import json
        state_data = {
            "status": ReviewStatus.COMPLETED,
            "data": {"test": "data"}
        }
        
        agent._redis_client = MagicMock()
        agent._redis_client.get = AsyncMock(return_value=json.dumps(state_data))
        
        # 测试获取状态
        result = await agent._get_review_state("test-job")
        
        assert result is not None
        assert result["status"] == ReviewStatus.COMPLETED
        agent._redis_client.get.assert_called_once_with("review:state:test-job")
    
    @pytest.mark.asyncio
    async def test_completed_status_prevents_modification(self):
        """测试 COMPLETED 状态阻止修改"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端和状态
        import json
        state_data = {
            "status": ReviewStatus.COMPLETED,
            "data": {"subgraphs": []},
            "modifications": []
        }
        
        agent._redis_client = MagicMock()
        agent._redis_client.exists = AsyncMock(return_value=1)
        agent._redis_client.get = AsyncMock(return_value=json.dumps(state_data))
        
        # 测试修改（应该被拒绝）
        result = await agent.handle_modification(
            job_id="test-job",
            modification_text="将 UP01 的材质改为 718",
            user_id="test-user"
        )
        
        assert result.status == "error"
        assert "已完成" in result.message


class TestDataVersionCalculation:
    """测试数据版本计算"""
    
    def test_calculate_data_version(self):
        """测试计算数据版本哈希"""
        agent = InteractionAgent()
        
        # 测试数据
        data = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 10.5},
                {"subgraph_id": "UP02", "material": "718", "weight": 8.3}
            ],
            "features": [
                {"feature_id": "F001", "name": "特征1"}
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
    
    def test_version_hash_consistency(self):
        """测试相同数据生成相同哈希"""
        agent = InteractionAgent()
        
        data = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20"}
            ]
        }
        
        # 计算两次
        version1 = agent._calculate_data_version(data)
        version2 = agent._calculate_data_version(data)
        
        # 应该相同
        assert version1 == version2
    
    def test_version_hash_change_detection(self):
        """测试数据变化时哈希改变"""
        agent = InteractionAgent()
        
        data1 = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20"}
            ]
        }
        
        data2 = {
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "718"}  # 材质改变
            ]
        }
        
        # 计算版本
        version1 = agent._calculate_data_version(data1)
        version2 = agent._calculate_data_version(data2)
        
        # 哈希应该不同
        assert version1["subgraphs:UP01"] != version2["subgraphs:UP01"]


class TestStatusEnum:
    """测试状态枚举"""
    
    def test_review_status_values(self):
        """测试状态枚举值"""
        assert ReviewStatus.REVIEWING == "reviewing"
        assert ReviewStatus.COMPLETED == "completed"
        assert ReviewStatus.EXPIRED == "expired"
        assert ReviewStatus.CANCELLED == "cancelled"
    
    def test_review_status_string(self):
        """测试状态转字符串"""
        assert str(ReviewStatus.REVIEWING) == "reviewing"
        assert str(ReviewStatus.COMPLETED) == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
