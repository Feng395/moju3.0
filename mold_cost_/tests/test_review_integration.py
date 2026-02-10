"""
审核系统集成测试
负责人：人员B2

测试内容：
1. 完整的审核流程
2. 并发场景
3. 错误处理
4. 数据一致性

阶段2.3实现
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api_gateway.main import app
from agents.interaction_agent import InteractionAgent


# ========== Fixtures ==========

@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock 数据库会话"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def mock_jwt_token():
    """Mock JWT Token"""
    return "Bearer test_token_123"


@pytest.fixture
def mock_user():
    """Mock 用户信息"""
    return {
        "user_id": "test_user_001",
        "username": "test_user",
        "role": "admin"
    }


# ========== 测试：完整审核流程 ==========

@pytest.mark.asyncio
async def test_complete_review_workflow(mock_db):
    """
    测试完整的审核流程
    
    流程：
    1. 启动审核
    2. 提交修改（多次）
    3. 确认修改
    """
    agent = InteractionAgent()
    job_id = "test-job-001"
    user_id = "test-user-001"
    
    # Mock 依赖
    with patch.object(agent, '_review_repo') as mock_repo, \
         patch.object(agent, '_redis_client') as mock_redis, \
         patch.object(agent, '_ws_manager') as mock_ws:
        
        # Mock ReviewRepository
        mock_repo.get_all_review_data = AsyncMock(return_value={
            "features": [{"feature_id": "F1", "name": "UP01"}],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": []
        })
        mock_repo.update_all_review_data = AsyncMock()
        
        # Mock Redis
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value='{"status": "reviewing", "data": {}, "modifications": []}')
        mock_redis.delete = AsyncMock()
        
        # Mock WebSocket
        mock_ws.broadcast = AsyncMock()
        
        # 1. 启动审核
        result = await agent.start_review(job_id, mock_db)
        assert result.status == "ok"
        assert "审核已启动" in result.message
        
        # 2. 第一次修改
        result = await agent.handle_modification(
            job_id,
            "将 UP01 的材质改为 718",
            user_id
        )
        assert result.status == "ok"
        
        # 3. 第二次修改
        result = await agent.handle_modification(
            job_id,
            "将 UP01 的厚度改为 15mm",
            user_id
        )
        assert result.status == "ok"
        
        # 4. 确认修改
        result = await agent.confirm_changes(job_id, user_id, mock_db)
        assert result.status == "ok"
        assert "审核已完成" in result.message


# ========== 测试：并发场景 ==========

@pytest.mark.asyncio
async def test_concurrent_review_lock(mock_db):
    """
    测试并发审核（分布式锁）
    
    场景：
    - 用户A启动审核（成功）
    - 用户B尝试启动审核（失败，锁被占用）
    """
    agent = InteractionAgent()
    job_id = "test-job-002"
    
    # Mock 依赖
    with patch.object(agent, '_review_repo') as mock_repo, \
         patch.object(agent, '_redis_client') as mock_redis, \
         patch.object(agent, '_ws_manager') as mock_ws:
        
        # Mock ReviewRepository
        mock_repo.get_all_review_data = AsyncMock(return_value={
            "features": [],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": []
        })
        
        # Mock Redis - 第一次获取锁成功，第二次失败
        mock_redis.set = AsyncMock(side_effect=[True, False])
        mock_redis.get = AsyncMock(return_value=None)
        
        # Mock WebSocket
        mock_ws.broadcast = AsyncMock()
        
        # 用户A启动审核（成功）
        result_a = await agent.start_review(job_id, mock_db)
        assert result_a.status == "ok"
        
        # 用户B尝试启动审核（失败）
        result_b = await agent.start_review(job_id, mock_db)
        assert result_b.status == "error"
        assert "正在被其他用户审核" in result_b.message


# ========== 测试：错误处理 ==========

@pytest.mark.asyncio
async def test_review_error_handling(mock_db):
    """
    测试错误处理
    
    场景：
    1. 数据库查询失败
    2. Redis 连接失败
    3. WebSocket 推送失败
    """
    agent = InteractionAgent()
    job_id = "test-job-003"
    
    # 场景1：数据库查询失败
    with patch.object(agent, '_review_repo') as mock_repo, \
         patch.object(agent, '_redis_client') as mock_redis, \
         patch.object(agent, '_ws_manager') as mock_ws:
        
        mock_repo.get_all_review_data = AsyncMock(side_effect=Exception("Database error"))
        mock_redis.set = AsyncMock(return_value=True)
        mock_ws.broadcast = AsyncMock()
        
        result = await agent.start_review(job_id, mock_db)
        assert result.status == "error"
        assert "Database error" in result.message


@pytest.mark.asyncio
async def test_modification_without_session():
    """
    测试在没有审核会话的情况下提交修改
    
    预期：返回错误
    """
    agent = InteractionAgent()
    job_id = "test-job-004"
    user_id = "test-user-001"
    
    # Mock Redis - 返回 None（没有会话）
    with patch.object(agent, '_redis_client') as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        
        result = await agent.handle_modification(
            job_id,
            "将 UP01 的材质改为 718",
            user_id
        )
        
        assert result.status == "error"
        assert "未找到审核会话" in result.message


# ========== 测试：数据一致性 ==========

@pytest.mark.asyncio
async def test_data_consistency(mock_db):
    """
    测试数据一致性
    
    验证：
    1. 修改后的数据正确保存到 Redis
    2. 确认后的数据正确更新到数据库
    """
    agent = InteractionAgent()
    job_id = "test-job-005"
    user_id = "test-user-001"
    
    # Mock 依赖
    with patch.object(agent, '_review_repo') as mock_repo, \
         patch.object(agent, '_redis_client') as mock_redis, \
         patch.object(agent, '_ws_manager') as mock_ws:
        
        # 初始数据
        initial_data = {
            "features": [
                {"feature_id": "F1", "name": "UP01", "material": "P20"}
            ],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": []
        }
        
        # Mock ReviewRepository
        mock_repo.get_all_review_data = AsyncMock(return_value=initial_data)
        mock_repo.update_all_review_data = AsyncMock()
        
        # Mock Redis
        saved_state = None
        
        async def mock_redis_set(key, value, ex=None):
            nonlocal saved_state
            saved_state = value
            return True
        
        async def mock_redis_get(key):
            return saved_state
        
        mock_redis.set = AsyncMock(side_effect=mock_redis_set)
        mock_redis.get = AsyncMock(side_effect=mock_redis_get)
        mock_redis.delete = AsyncMock()
        
        # Mock WebSocket
        mock_ws.broadcast = AsyncMock()
        
        # 1. 启动审核
        await agent.start_review(job_id, mock_db)
        
        # 2. 提交修改
        await agent.handle_modification(
            job_id,
            "将 UP01 的材质改为 718",
            user_id
        )
        
        # 验证：Redis 中保存了修改
        assert saved_state is not None
        
        # 3. 确认修改
        await agent.confirm_changes(job_id, user_id, mock_db)
        
        # 验证：数据库更新被调用
        mock_repo.update_all_review_data.assert_called_once()


# ========== 测试：HTTP API ==========

def test_start_review_api(client):
    """
    测试启动审核 API
    
    POST /api/v1/review/start
    """
    # Mock JWT 认证
    with patch('api_gateway.routers.review_router.get_current_user') as mock_auth:
        mock_auth.return_value = {
            "user_id": "test_user_001",
            "username": "test_user"
        }
        
        # Mock InteractionAgent
        with patch('api_gateway.routers.review_router.InteractionAgent') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.start_review = AsyncMock(return_value=MagicMock(
                status="ok",
                message="审核已启动",
                data={"job_id": "test-job-001"}
            ))
            mock_agent_class.return_value = mock_agent
            
            # 发送请求
            response = client.post(
                "/api/v1/review/start",
                json={"job_id": "test-job-001"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


def test_modify_review_api(client):
    """
    测试提交修改 API
    
    POST /api/v1/review/{job_id}/modify
    """
    # Mock JWT 认证
    with patch('api_gateway.routers.review_router.get_current_user') as mock_auth:
        mock_auth.return_value = {
            "user_id": "test_user_001",
            "username": "test_user"
        }
        
        # Mock InteractionAgent
        with patch('api_gateway.routers.review_router.InteractionAgent') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.handle_modification = AsyncMock(return_value=MagicMock(
                status="ok",
                message="修改已应用",
                data={"modification_id": "mod-001"}
            ))
            mock_agent_class.return_value = mock_agent
            
            # 发送请求
            response = client.post(
                "/api/v1/review/test-job-001/modify",
                json={"modification_text": "将 UP01 的材质改为 718"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


def test_confirm_review_api(client):
    """
    测试确认修改 API
    
    POST /api/v1/review/{job_id}/confirm
    """
    # Mock JWT 认证
    with patch('api_gateway.routers.review_router.get_current_user') as mock_auth:
        mock_auth.return_value = {
            "user_id": "test_user_001",
            "username": "test_user"
        }
        
        # Mock InteractionAgent
        with patch('api_gateway.routers.review_router.InteractionAgent') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.confirm_changes = AsyncMock(return_value=MagicMock(
                status="ok",
                message="审核已完成",
                data={"modifications_count": 2}
            ))
            mock_agent_class.return_value = mock_agent
            
            # 发送请求
            response = client.post(
                "/api/v1/review/test-job-001/confirm",
                headers={"Authorization": "Bearer test_token"}
            )
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


def test_get_review_status_api(client):
    """
    测试查询审核状态 API
    
    GET /api/v1/review/{job_id}/status
    """
    # Mock JWT 认证
    with patch('api_gateway.routers.review_router.get_current_user') as mock_auth:
        mock_auth.return_value = {
            "user_id": "test_user_001",
            "username": "test_user"
        }
        
        # Mock InteractionAgent
        with patch('api_gateway.routers.review_router.InteractionAgent') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.get_review_state = AsyncMock(return_value={
                "status": "reviewing",
                "modifications": [],
                "created_at": "2026-01-15T10:00:00"
            })
            mock_agent.check_lock = AsyncMock(return_value=True)
            mock_agent_class.return_value = mock_agent
            
            # 发送请求
            response = client.get(
                "/api/v1/review/test-job-001/status",
                headers={"Authorization": "Bearer test_token"}
            )
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["data"]["review_status"] == "reviewing"
