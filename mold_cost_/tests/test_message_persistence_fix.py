"""
测试消息持久化修复
验证 review_display_view 和 completion_request 消息是否正确持久化
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agents.interaction_agent import InteractionAgent
from agents.message_persistence_manager import MessagePersistenceManager


class TestMessagePersistenceFix:
    """测试消息持久化修复"""
    
    def test_persistable_messages_updated(self):
        """测试 PERSISTABLE_MESSAGES 是否包含新的消息类型"""
        manager = MessagePersistenceManager()
        
        # 验证新增的消息类型
        assert 'review_display_view' in manager.PERSISTABLE_MESSAGES, \
            "review_display_view 应该在持久化列表中"
        assert 'completion_request' in manager.PERSISTABLE_MESSAGES, \
            "completion_request 应该在持久化列表中"
        
        # 验证原有的消息类型仍然存在
        assert 'modification_confirmation' in manager.PERSISTABLE_MESSAGES
        assert 'review_data' in manager.PERSISTABLE_MESSAGES
        assert 'review_completed' in manager.PERSISTABLE_MESSAGES
        assert 'operation_completed' in manager.PERSISTABLE_MESSAGES
        assert 'progress' in manager.PERSISTABLE_MESSAGES
    
    def test_should_persist_new_message_types(self):
        """测试新消息类型是否会被持久化"""
        manager = MessagePersistenceManager()
        
        # 测试 review_display_view
        display_view_msg = {
            "type": "review_display_view",
            "job_id": "test-job",
            "data": [{"subgraph_id": "UP01"}]
        }
        assert manager.should_persist(display_view_msg) is True, \
            "review_display_view 消息应该被持久化"
        
        # 测试 completion_request
        completion_msg = {
            "type": "completion_request",
            "job_id": "test-job",
            "data": {"missing_fields": []}
        }
        assert manager.should_persist(completion_msg) is True, \
            "completion_request 消息应该被持久化"
    
    @pytest.mark.asyncio
    async def test_push_display_view_with_persistence(self):
        """测试 _push_display_view 是否调用持久化"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.publish = AsyncMock()
        
        # Mock 持久化管理器
        agent._persistence_manager = AsyncMock()
        agent._persistence_manager.push_and_persist = AsyncMock()
        
        # Mock 数据库会话
        db_session = AsyncMock()
        
        # 调用方法
        display_view = [{"subgraph_id": "UP01", "material": "P20"}]
        await agent._push_display_view("test-job", display_view, db_session=db_session)
        
        # 验证 Redis 推送被调用
        agent._redis_client.publish.assert_called_once()
        
        # 验证持久化被调用
        agent._persistence_manager.push_and_persist.assert_called_once()
        call_args = agent._persistence_manager.push_and_persist.call_args
        
        assert call_args.kwargs['job_id'] == "test-job"
        assert call_args.kwargs['db_session'] == db_session
        assert call_args.kwargs['ws_message']['type'] == "review_display_view"
    
    @pytest.mark.asyncio
    async def test_push_completion_request_with_persistence(self):
        """测试 _push_completion_request 是否调用持久化"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.publish = AsyncMock()
        
        # Mock 持久化管理器
        agent._persistence_manager = AsyncMock()
        agent._persistence_manager.push_and_persist = AsyncMock()
        
        # Mock 数据库会话
        db_session = AsyncMock()
        
        # 调用方法
        completion_data = {
            "missing_fields": [{"subgraph_id": "UP01", "field": "material"}],
            "suggestion": "请补全材质字段"
        }
        await agent._push_completion_request("test-job", completion_data, db_session=db_session)
        
        # 验证 Redis 推送被调用
        agent._redis_client.publish.assert_called_once()
        
        # 验证持久化被调用
        agent._persistence_manager.push_and_persist.assert_called_once()
        call_args = agent._persistence_manager.push_and_persist.call_args
        
        assert call_args.kwargs['job_id'] == "test-job"
        assert call_args.kwargs['db_session'] == db_session
        assert call_args.kwargs['ws_message']['type'] == "completion_request"
    
    @pytest.mark.asyncio
    async def test_push_without_db_session(self):
        """测试没有 db_session 时不会持久化"""
        agent = InteractionAgent()
        
        # Mock Redis 客户端
        agent._redis_client = AsyncMock()
        agent._redis_client.publish = AsyncMock()
        
        # Mock 持久化管理器
        agent._persistence_manager = AsyncMock()
        agent._persistence_manager.push_and_persist = AsyncMock()
        
        # 调用方法（不传 db_session）
        display_view = [{"subgraph_id": "UP01"}]
        await agent._push_display_view("test-job", display_view)
        
        # 验证 Redis 推送被调用
        agent._redis_client.publish.assert_called_once()
        
        # 验证持久化未被调用
        agent._persistence_manager.push_and_persist.assert_not_called()


class TestMessageFormatters:
    """测试新增的消息格式化器"""
    
    def test_format_review_display_view(self):
        """测试展示视图消息格式化"""
        from api_gateway.utils.message_formatter import format_websocket_message
        
        ws_message = {
            "type": "review_display_view",
            "job_id": "test-job",
            "data": [
                {"subgraph_id": "UP01", "material": "P20"},
                {"subgraph_id": "UP02", "material": "718"}
            ]
        }
        
        content, metadata = format_websocket_message(ws_message)
        
        assert "展示视图已加载" in content
        assert "2 条记录" in content
        assert metadata['message_type'] == "review_display_view"
        assert metadata['records_count'] == 2
    
    def test_format_completion_request(self):
        """测试补全请求消息格式化"""
        from api_gateway.utils.message_formatter import format_websocket_message
        
        ws_message = {
            "type": "completion_request",
            "job_id": "test-job",
            "data": {
                "missing_fields": [
                    {"subgraph_id": "UP01", "field": "material"},
                    {"subgraph_id": "UP02", "field": "thickness_mm"}
                ],
                "suggestion": "根据零件编号推测材质",
                "message": "发现缺失字段"
            }
        }
        
        content, metadata = format_websocket_message(ws_message)
        
        assert "发现缺失字段" in content
        assert "UP01" in content
        assert "材质" in content
        assert "根据零件编号推测材质" in content
        assert metadata['message_type'] == "completion_request"
        assert metadata['missing_fields_count'] == 2
    
    def test_format_completion_request_many_fields(self):
        """测试补全请求消息格式化（大量字段）"""
        from api_gateway.utils.message_formatter import format_websocket_message
        
        # 创建15个缺失字段
        missing_fields = [
            {"subgraph_id": f"UP{i:02d}", "field": "material"}
            for i in range(1, 16)
        ]
        
        ws_message = {
            "type": "completion_request",
            "job_id": "test-job",
            "data": {
                "missing_fields": missing_fields,
                "message": "发现大量缺失字段"
            }
        }
        
        content, metadata = format_websocket_message(ws_message)
        
        # 应该只显示前10个
        assert "UP01" in content
        assert "UP10" in content
        # 应该显示"还有 5 个字段"
        assert "还有 5 个字段" in content
        assert metadata['missing_fields_count'] == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
