"""
消息持久化功能测试
"""
import pytest
from api_gateway.utils.message_formatter import (
    format_websocket_message,
    format_interaction_card,
    format_modifications,
    format_review_completed,
    format_operation_completed,
)
from agents.message_persistence_manager import MessagePersistenceManager


class TestMessageFormatter:
    """测试消息格式化器"""
    
    def test_format_interaction_card(self):
        """测试交互卡片格式化"""
        ws_message = {
            "type": "need_user_input",
            "data": {
                "title": "缺少必要参数",
                "fields": [
                    {
                        "key": "UP01.thickness_mm",
                        "label": "UP01 - 厚度(mm)",
                        "help_text": "单位：毫米"
                    },
                    {
                        "key": "UP01.material",
                        "label": "UP01 - 材质"
                    }
                ]
            }
        }
        
        content, metadata = format_websocket_message(ws_message)
        
        assert "系统请求输入参数" in content
        assert "UP01 - 厚度(mm)" in content
        assert "UP01 - 材质" in content
        assert metadata["message_type"] == "need_user_input"
    
    def test_format_modification_confirmation(self):
        """测试修改确认格式化"""
        ws_message = {
            "type": "modification_confirmation",
            "modifications": [
                {
                    "subgraph_id": "UP01",
                    "field": "material",
                    "old_value": "45#",
                    "new_value": "718"
                },
                {
                    "subgraph_id": "UP02",
                    "field": "thickness_mm",
                    "old_value": 10,
                    "new_value": 15
                }
            ]
        }
        
        content, metadata = format_websocket_message(ws_message)
        
        assert "待确认的修改" in content
        assert "UP01 材质: 45# → 718" in content
        assert "UP02 厚度: 10mm → 15mm" in content
        assert metadata["modifications_count"] == 2
    
    def test_format_review_completed(self):
        """测试审核完成格式化"""
        ws_message = {
            "type": "review_completed",
            "modifications_count": 3
        }
        
        content, metadata = format_websocket_message(ws_message)
        
        assert "审核已完成" in content
        assert "3 处修改" in content
        assert metadata["modifications_count"] == 3
    
    def test_format_operation_completed(self):
        """测试操作完成格式化"""
        ws_message = {
            "type": "operation_completed",
            "action_type": "QUERY_DETAILS"
        }
        
        content, metadata = format_websocket_message(ws_message)
        
        assert "操作已完成" in content
        assert "查询详情" in content
        assert metadata["action_type"] == "QUERY_DETAILS"
    
    def test_format_progress(self):
        """测试进度消息格式化"""
        ws_message = {
            "type": "progress",
            "data": {
                "stage": "cad_parsing",
                "progress": 20,
                "message": "正在解析 CAD 文件..."
            }
        }
        
        content, metadata = format_websocket_message(ws_message)
        
        assert "任务进度" in content
        assert "CAD 解析" in content
        assert "20%" in content
        assert "正在解析 CAD 文件" in content
        assert metadata["stage"] == "cad_parsing"
        assert metadata["progress"] == 20


class TestMessagePersistenceManager:
    """测试持久化管理器"""
    
    def test_should_persist(self):
        """测试消息过滤逻辑"""
        manager = MessagePersistenceManager()
        
        # 需要持久化的消息
        assert manager.should_persist({"type": "need_user_input"})
        assert manager.should_persist({"type": "modification_confirmation"})
        assert manager.should_persist({"type": "review_completed"})
        assert manager.should_persist({"type": "progress"})  # 新增
        
        # 不需要持久化的消息
        assert not manager.should_persist({"type": "ping"})
        assert not manager.should_persist({"type": "echo"})
    
    def test_enable_disable(self):
        """测试启用/禁用功能"""
        manager = MessagePersistenceManager()
        
        # 默认启用
        assert manager.enabled
        
        # 禁用
        manager.disable()
        assert not manager.enabled
        assert not manager.should_persist({"type": "need_user_input"})
        
        # 重新启用
        manager.enable()
        assert manager.enabled
        assert manager.should_persist({"type": "need_user_input"})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
