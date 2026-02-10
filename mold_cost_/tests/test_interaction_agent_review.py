"""
InteractionAgent (审核模式) 单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agents.interaction_agent import InteractionAgent
import uuid


@pytest.fixture
def interaction_agent():
    """创建 InteractionAgent 实例"""
    return InteractionAgent()


@pytest.fixture
def sample_job_id():
    """示例任务ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_review_data():
    """示例审核数据"""
    return {
        "features": [
            {
                "feature_id": 1,
                "subgraph_id": "UP01",
                "thickness_mm": 10.0,
                "material": "P20"
            }
        ],
        "price_snapshots": [
            {
                "snapshot_id": 1,
                "name": "材料费",
                "unit_price": 50.0
            }
        ],
        "process_snapshots": [
            {
                "snapshot_id": 1,
                "name": "粗加工",
                "conditions": {}
            }
        ],
        "subgraphs": [
            {
                "subgraph_id": "UP01",
                "part_name": "上模",
                "material": "P20",
                "total_cost": 1000.0
            }
        ]
    }


class TestInteractionAgentReview:
    """InteractionAgent 审核模式测试"""
    
    @pytest.mark.asyncio
    async def test_start_review_success(self, interaction_agent, sample_job_id, sample_review_data):
        """测试启动审核流程（成功）"""
        # 模拟依赖
        mock_db = AsyncMock()
        
        # Mock 私有属性而不是 property
        mock_repo = AsyncMock()
        mock_repo.get_all_review_data.return_value = sample_review_data
        interaction_agent._review_repo = mock_repo
        
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True  # 模拟获取锁成功
        interaction_agent._redis_client = mock_redis
        
        mock_ws = AsyncMock()
        interaction_agent._ws_manager = mock_ws
        
        # 执行启动审核
        result = await interaction_agent.start_review(sample_job_id, mock_db)
        
        # 验证结果
        assert result.status == "ok"
        assert result.message == "审核流程已启动"
        assert result.data["job_id"] == sample_job_id
        assert result.data["features_count"] == 1
        
        # 验证调用了必要的方法
        mock_repo.get_all_review_data.assert_called_once()
        mock_redis.set.assert_called()  # 保存状态
        mock_ws.broadcast.assert_called()  # 推送消息
    
    @pytest.mark.asyncio
    async def test_start_review_lock_failed(self, interaction_agent, sample_job_id):
        """测试启动审核流程（锁被占用）"""
        mock_db = AsyncMock()
        
        # Mock 私有属性
        mock_redis = AsyncMock()
        mock_redis.set.return_value = False  # 模拟获取锁失败
        interaction_agent._redis_client = mock_redis
        
        # 执行启动审核
        result = await interaction_agent.start_review(sample_job_id, mock_db)
        
        # 验证结果
        assert result.status == "error"
        assert "正在被其他用户审核" in result.message
    
    @pytest.mark.asyncio
    async def test_handle_modification(self, interaction_agent, sample_job_id, sample_review_data):
        """测试处理修改请求"""
        modification_text = "将 UP01 的材质改为 718"
        user_id = "test_user"
        
        # Mock 私有属性
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1  # 模拟锁存在
        
        # 模拟获取状态
        import json
        state = {
            "status": "reviewing",
            "data": sample_review_data,
            "modifications": []
        }
        mock_redis.get.return_value = json.dumps(state)
        interaction_agent._redis_client = mock_redis
        
        mock_ws = AsyncMock()
        interaction_agent._ws_manager = mock_ws
        
        # 执行处理修改
        result = await interaction_agent.handle_modification(
            sample_job_id,
            modification_text,
            user_id
        )
        
        # 验证结果
        assert result.status == "ok"
        assert "修改已应用" in result.message
        assert "modification_id" in result.data
        
        # 验证推送了确认消息
        mock_ws.broadcast.assert_called()
    
    @pytest.mark.asyncio
    async def test_confirm_changes(self, interaction_agent, sample_job_id, sample_review_data):
        """测试确认修改"""
        user_id = "test_user"
        mock_db = AsyncMock()
        
        # Mock 私有属性
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1  # 模拟锁存在
        
        # 模拟获取状态
        import json
        state = {
            "status": "reviewing",
            "data": sample_review_data,
            "modifications": [
                {
                    "id": "mod-1",
                    "text": "测试修改"
                }
            ]
        }
        mock_redis.get.return_value = json.dumps(state)
        interaction_agent._redis_client = mock_redis
        
        mock_repo = AsyncMock()
        interaction_agent._review_repo = mock_repo
        
        mock_ws = AsyncMock()
        interaction_agent._ws_manager = mock_ws
        
        # 执行确认修改
        result = await interaction_agent.confirm_changes(
            sample_job_id,
            user_id,
            mock_db
        )
        
        # 验证结果
        assert result.status == "ok"
        assert "修改已确认并保存" in result.message
        assert result.data["modifications_count"] == 1
        
        # 验证更新了数据库
        mock_repo.update_all_review_data.assert_called_once()
        
        # 验证提交了事务
        mock_db.commit.assert_called_once()
        
        # 验证释放了锁
        mock_redis.delete.assert_called()
        
        # 验证推送了完成消息
        mock_ws.broadcast.assert_called()
    
    def test_simple_parse(self, interaction_agent, sample_review_data):
        """测试简单解析"""
        text = "将 UP01 的材质改为 718"
        
        changes = interaction_agent._simple_parse(text, sample_review_data)
        
        # 验证解析结果
        assert len(changes) > 0
        assert changes[0]["original_text"] == text
    
    def test_apply_changes(self, interaction_agent, sample_review_data):
        """测试应用修改"""
        changes = [
            {
                "table": "subgraphs",
                "id": "UP01",
                "field": "material",
                "value": "718"
            }
        ]
        
        modified_data = interaction_agent._apply_changes(sample_review_data, changes)
        
        # 验证修改已应用
        assert modified_data["subgraphs"][0]["material"] == "718"
    
    def test_get_id_field(self, interaction_agent):
        """测试获取 ID 字段名"""
        assert interaction_agent._get_id_field("features") == "feature_id"
        assert interaction_agent._get_id_field("price_snapshots") == "snapshot_id"
        assert interaction_agent._get_id_field("process_snapshots") == "snapshot_id"
        assert interaction_agent._get_id_field("subgraphs") == "subgraph_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
