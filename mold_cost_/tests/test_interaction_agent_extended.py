"""
InteractionAgent 扩展测试
负责人：人员B2

测试范围：
1. Redis 状态管理
2. 分布式锁机制
3. WebSocket 推送（Redis Pub/Sub）
4. SSE 聊天功能
5. 错误处理和恢复
6. 边界情况
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

from agents.interaction_agent import InteractionAgent


class TestRedisStateManagement:
    """测试 Redis 状态管理"""
    
    @pytest.mark.asyncio
    async def test_save_and_get_review_state(self):
        """测试保存和获取审核状态"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.set = AsyncMock()
        agent._redis_client.get = AsyncMock()
        
        # 测试数据
        state = {
            "status": "reviewing",
            "data": {"features": [], "subgraphs": []},
            "modifications": [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # 保存状态
        await agent._save_review_state(job_id, state)
        
        # 验证调用
        agent._redis_client.set.assert_called_once()
        call_args = agent._redis_client.set.call_args
        assert f"review:state:{job_id}" in call_args[0]
        
        # 模拟获取状态
        agent._redis_client.get.return_value = json.dumps(state, ensure_ascii=False)
        
        # 获取状态
        retrieved_state = await agent._get_review_state(job_id)
        
        # 验证
        assert retrieved_state is not None
        assert retrieved_state["status"] == "reviewing"
        assert "data" in retrieved_state
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_state(self):
        """测试获取不存在的状态"""
        agent = InteractionAgent()
        job_id = "nonexistent_job"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.get = AsyncMock(return_value=None)
        
        # 获取状态
        state = await agent._get_review_state(job_id)
        
        # 验证
        assert state is None
    
    @pytest.mark.asyncio
    async def test_clear_review_state(self):
        """测试清理审核状态"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.delete = AsyncMock()
        
        # 清理状态
        await agent._clear_review_state(job_id)
        
        # 验证调用
        agent._redis_client.delete.assert_called_once()
        call_args = agent._redis_client.delete.call_args
        assert f"review:state:{job_id}" in call_args[0]


class TestDistributedLock:
    """测试分布式锁机制"""
    
    @pytest.mark.asyncio
    async def test_acquire_lock_success(self):
        """测试成功获取锁"""
        agent = InteractionAgent()
        lock_key = "review:lock:test_job"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.set = AsyncMock(return_value=True)
        
        # 获取锁
        result = await agent._acquire_lock(lock_key, timeout=300)
        
        # 验证
        assert result is True
        agent._redis_client.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_acquire_lock_failure(self):
        """测试获取锁失败（已被占用）"""
        agent = InteractionAgent()
        lock_key = "review:lock:test_job"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.set = AsyncMock(return_value=False)
        
        # 获取锁
        result = await agent._acquire_lock(lock_key, timeout=300)
        
        # 验证
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_lock_exists(self):
        """测试检查锁是否存在"""
        agent = InteractionAgent()
        lock_key = "review:lock:test_job"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.exists = AsyncMock(return_value=1)
        
        # 检查锁
        result = await agent._check_lock(lock_key)
        
        # 验证
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_lock_not_exists(self):
        """测试检查锁不存在"""
        agent = InteractionAgent()
        lock_key = "review:lock:test_job"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.exists = AsyncMock(return_value=0)
        
        # 检查锁
        result = await agent._check_lock(lock_key)
        
        # 验证
        assert result is False
    
    @pytest.mark.asyncio
    async def test_release_lock(self):
        """测试释放锁"""
        agent = InteractionAgent()
        lock_key = "review:lock:test_job"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.delete = AsyncMock()
        
        # 释放锁
        await agent._release_lock(lock_key)
        
        # 验证
        agent._redis_client.delete.assert_called_once_with(lock_key)


class TestWebSocketPush:
    """测试 WebSocket 推送（Redis Pub/Sub）"""
    
    @pytest.mark.asyncio
    async def test_push_review_data(self):
        """测试推送审核数据"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        data = {
            "features": [{"feature_id": "F1"}],
            "subgraphs": [{"subgraph_id": "UP01"}]
        }
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.publish = AsyncMock()
        
        # 推送数据
        await agent._push_review_data(job_id, data)
        
        # 验证
        agent._redis_client.publish.assert_called_once()
        call_args = agent._redis_client.publish.call_args
        
        # 验证频道
        channel = call_args[0][0]
        assert channel == f"job:{job_id}:review"
        
        # 验证消息
        message = json.loads(call_args[0][1])
        assert message["type"] == "review_data"
        assert message["job_id"] == job_id
        assert "data" in message
    
    @pytest.mark.asyncio
    async def test_push_modification_confirmation(self):
        """测试推送修改确认"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        modification = {
            "id": "mod_123",
            "text": "将 UP01 的材质改为 718"
        }
        modified_data = {"subgraphs": []}
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.publish = AsyncMock()
        
        # 推送确认
        await agent._push_modification_confirmation(job_id, modification, modified_data)
        
        # 验证
        agent._redis_client.publish.assert_called_once()
        call_args = agent._redis_client.publish.call_args
        
        # 验证消息
        message = json.loads(call_args[0][1])
        assert message["type"] == "modification_confirmation"
        assert message["action_required"] == "confirm"
    
    @pytest.mark.asyncio
    async def test_push_completion_message(self):
        """测试推送完成消息"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        modifications = [{"id": "mod_1"}, {"id": "mod_2"}]
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.publish = AsyncMock()
        
        # 推送完成消息
        await agent._push_completion_message(job_id, modifications)
        
        # 验证
        agent._redis_client.publish.assert_called_once()
        call_args = agent._redis_client.publish.call_args
        
        # 验证消息
        message = json.loads(call_args[0][1])
        assert message["type"] == "review_completed"
        assert message["modifications_count"] == 2


class TestSSEChat:
    """测试 SSE 流式聊天"""
    
    @pytest.mark.asyncio
    async def test_build_context_info(self):
        """测试构建上下文信息"""
        agent = InteractionAgent()
        data = {
            "features": [{"feature_id": "F1"}],
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
            ]
        }
        
        # 构建上下文
        context = agent._build_context_info(data)
        
        # 验证
        assert "features: 1" in context
        assert "subgraphs: 1" in context
        assert "UP01" in context
        assert "P20" in context
    
    @pytest.mark.asyncio
    async def test_build_context_info_empty(self):
        """测试构建空数据的上下文"""
        agent = InteractionAgent()
        data = {}
        
        # 构建上下文
        context = agent._build_context_info(data)
        
        # 验证
        assert context == "暂无数据"
    
    @pytest.mark.asyncio
    async def test_chat_stream_basic(self):
        """测试基本流式聊天"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        message = "你好"
        history = []
        current_data = {"features": []}
        
        # 模拟 LLM 流式响应
        async def mock_llm_stream(messages):
            yield "你"
            yield "好"
            yield "！"
        
        agent._call_llm_stream = mock_llm_stream
        
        # 收集响应
        response_chunks = []
        async for chunk in agent.chat_stream(job_id, message, history, current_data):
            response_chunks.append(chunk)
        
        # 验证
        assert len(response_chunks) == 3
        assert "".join(response_chunks) == "你好！"
    
    @pytest.mark.asyncio
    async def test_chat_non_stream(self):
        """测试非流式聊天"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        message = "你好"
        history = []
        current_data = {"features": []}
        
        # 模拟 LLM 流式响应
        async def mock_llm_stream(messages):
            yield "你"
            yield "好"
            yield "！"
        
        agent._call_llm_stream = mock_llm_stream
        
        # 获取完整响应
        response = await agent.chat(job_id, message, history, current_data)
        
        # 验证
        assert response == "你好！"


class TestErrorHandling:
    """测试错误处理和恢复"""
    
    @pytest.mark.asyncio
    async def test_start_review_lock_failure(self):
        """测试启动审核时锁获取失败"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.set = AsyncMock(return_value=False)  # 锁获取失败
        
        # 模拟数据库会话
        db_session = AsyncMock()
        
        # 启动审核
        result = await agent.start_review(job_id, db_session)
        
        # 验证
        assert result.status == "error"
        assert "正在被其他用户审核" in result.message
    
    @pytest.mark.asyncio
    async def test_handle_modification_no_state(self):
        """测试处理修改时状态不存在"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.exists = AsyncMock(return_value=1)  # 锁存在
        agent._redis_client.get = AsyncMock(return_value=None)  # 状态不存在
        
        # 处理修改
        result = await agent.handle_modification(job_id, "修改内容", "user_123")
        
        # 验证
        assert result.status == "error"
        assert "未找到审核会话" in result.message
    
    @pytest.mark.asyncio
    async def test_confirm_changes_lock_expired(self):
        """测试确认修改时锁已过期"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.exists = AsyncMock(return_value=0)  # 锁不存在
        
        # 模拟数据库会话
        db_session = AsyncMock()
        
        # 确认修改
        result = await agent.confirm_changes(job_id, "user_123", db_session)
        
        # 验证
        assert result.status == "error"
        assert "已过期或被释放" in result.message
    
    @pytest.mark.asyncio
    async def test_handle_modification_validation_failure(self):
        """测试修改验证失败"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.exists = AsyncMock(return_value=1)
        
        # 模拟状态
        state = {
            "status": "reviewing",
            "data": {"subgraphs": []},
            "modifications": []
        }
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        # 模拟 NLP 解析器
        agent._nlp_parser = AsyncMock()
        agent._nlp_parser.parse = AsyncMock(return_value=[
            {
                "table": "subgraphs",
                "id": "NOT_EXIST",  # 不存在的记录
                "field": "material",
                "value": "P20"
            }
        ])
        
        # 处理修改
        result = await agent.handle_modification(job_id, "修改内容", "user_123")
        
        # 验证
        assert result.status == "error"
        assert "验证失败" in result.message


class TestBoundaryConditions:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_empty_modification_text(self):
        """测试空修改文本"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.exists = AsyncMock(return_value=1)
        
        # 模拟状态
        state = {
            "status": "reviewing",
            "data": {"subgraphs": []},
            "modifications": []
        }
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        # 模拟 NLP 解析器返回空列表
        agent._nlp_parser = AsyncMock()
        agent._nlp_parser.parse = AsyncMock(return_value=[])
        
        # 处理修改
        result = await agent.handle_modification(job_id, "", "user_123")
        
        # 验证
        assert result.status == "error"
    
    @pytest.mark.asyncio
    async def test_large_data_set(self):
        """测试大数据集"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 创建大数据集（1000条记录）
        large_data = {
            "subgraphs": [
                {"subgraph_id": f"SG{i}", "material": "P20", "weight": 5.5}
                for i in range(1000)
            ]
        }
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.set = AsyncMock()
        
        # 保存状态
        state = {
            "status": "reviewing",
            "data": large_data,
            "modifications": []
        }
        
        # 测试保存（不应该抛出异常）
        await agent._save_review_state(job_id, state)
        
        # 验证调用
        agent._redis_client.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_modifications(self):
        """测试多次修改"""
        agent = InteractionAgent()
        job_id = "test_job_123"
        
        # 模拟 Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.exists = AsyncMock(return_value=1)
        agent._redis_client.set = AsyncMock()
        agent._redis_client.publish = AsyncMock()
        
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
        agent._nlp_parser = AsyncMock()
        agent._nlp_parser.parse = AsyncMock(return_value=[
            {
                "table": "subgraphs",
                "id": "UP01",
                "field": "material",
                "value": "718"
            }
        ])
        
        # 第一次修改
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        result1 = await agent.handle_modification(job_id, "修改1", "user_123")
        assert result1.status == "ok"
        
        # 更新状态（添加第一次修改）
        state["modifications"].append({"id": "mod_1"})
        
        # 第二次修改
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        result2 = await agent.handle_modification(job_id, "修改2", "user_123")
        assert result2.status == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
