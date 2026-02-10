"""
端到端审核流程测试
负责人：人员B2

测试场景：
1. 完整审核流程（启动→修改→确认）
2. 多轮修改流程
3. 错误恢复流程
4. WebSocket 推送验证
5. 数据库一致性验证
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json
from datetime import datetime

from agents.interaction_agent import InteractionAgent


class TestCompleteReviewFlow:
    """测试完整审核流程"""
    
    @pytest.mark.asyncio
    async def test_full_review_cycle(self):
        """
        测试完整的审核周期
        
        流程：
        1. 启动审核
        2. 提交修改
        3. 确认修改
        4. 验证数据库更新
        """
        agent = InteractionAgent()
        job_id = "test_job_e2e_001"
        user_id = "user_123"
        
        # 模拟依赖
        agent._redis_client = AsyncMock()
        agent._review_repo = AsyncMock()
        agent._nlp_parser = AsyncMock()
        
        # 模拟数据库会话
        db_session = AsyncMock()
        db_session.commit = AsyncMock()
        db_session.rollback = AsyncMock()
        
        # === 步骤1：启动审核 ===
        
        # 模拟锁获取成功
        agent._redis_client.set = AsyncMock(return_value=True)
        
        # 模拟数据库查询（完整的4个表）
        mock_data = {
            "features": [{"feature_id": "F1", "feature_type": "hole"}],
            "price_snapshots": [{"snapshot_id": "PS1", "total_price": 1000}],
            "process_snapshots": [{"snapshot_id": "PRS1", "process_type": "milling"}],
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
            ]
        }
        agent._review_repo.get_all_review_data = AsyncMock(return_value=mock_data)
        
        # 模拟 Redis 操作
        agent._redis_client.publish = AsyncMock()
        
        # 启动审核
        result = await agent.start_review(job_id, db_session)
        
        # 验证结果
        assert result.status == "ok"
        assert "审核流程已启动" in result.message
        assert result.data["subgraphs_count"] == 1
        
        # 验证 Redis 推送
        agent._redis_client.publish.assert_called()
        
        # === 步骤2：提交修改 ===
        
        # 模拟锁检查
        agent._redis_client.exists = AsyncMock(return_value=1)
        
        # 模拟状态获取
        state = {
            "status": "reviewing",
            "data": mock_data,
            "modifications": [],
            "created_at": datetime.utcnow().isoformat()
        }
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        # 模拟 NLP 解析
        parsed_changes = [
            {
                "table": "subgraphs",
                "id": "UP01",
                "field": "material",
                "value": "718"
            }
        ]
        agent._nlp_parser.parse = AsyncMock(return_value=parsed_changes)
        
        # 提交修改
        modification_text = "将 UP01 的材质改为 718"
        result = await agent.handle_modification(job_id, modification_text, user_id)
        
        # 验证结果
        assert result.status == "ok"
        assert "修改已应用" in result.message
        assert "parsed_changes" in result.data
        
        # === 步骤3：确认修改 ===
        
        # 模拟更新后的状态
        modified_state = state.copy()
        modified_state["modifications"].append({
            "id": "mod_123",
            "text": modification_text,
            "parsed": parsed_changes
        })
        modified_state["data"]["subgraphs"][0]["material"] = "718"
        
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(modified_state, ensure_ascii=False)
        )
        
        # 模拟数据库更新
        agent._review_repo.update_all_review_data = AsyncMock()
        
        # 模拟锁释放
        agent._redis_client.delete = AsyncMock()
        
        # 确认修改
        result = await agent.confirm_changes(job_id, user_id, db_session)
        
        # 验证结果
        assert result.status == "ok"
        assert "修改已确认并保存" in result.message
        assert result.data["modifications_count"] == 1
        
        # 验证数据库更新被调用
        agent._review_repo.update_all_review_data.assert_called_once()
        
        # 验证事务提交
        db_session.commit.assert_called_once()
        
        # 验证锁释放
        agent._redis_client.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_review_with_validation_error(self):
        """
        测试带验证错误的审核流程
        
        流程：
        1. 启动审核
        2. 提交无效修改
        3. 验证错误处理
        """
        agent = InteractionAgent()
        job_id = "test_job_e2e_002"
        user_id = "user_123"
        
        # 模拟依赖
        agent._redis_client = AsyncMock()
        agent._review_repo = AsyncMock()
        agent._nlp_parser = AsyncMock()
        
        # 模拟数据库会话
        db_session = AsyncMock()
        
        # 启动审核
        agent._redis_client.set = AsyncMock(return_value=True)
        mock_data = {
            "features": [],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5}
            ]
        }
        agent._review_repo.get_all_review_data = AsyncMock(return_value=mock_data)
        agent._redis_client.publish = AsyncMock()
        
        result = await agent.start_review(job_id, db_session)
        assert result.status == "ok"
        
        # 提交无效修改（记录不存在）
        agent._redis_client.exists = AsyncMock(return_value=1)
        state = {
            "status": "reviewing",
            "data": mock_data,
            "modifications": []
        }
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        # 解析为不存在的记录
        agent._nlp_parser.parse = AsyncMock(return_value=[
            {
                "table": "subgraphs",
                "id": "NOT_EXIST",  # 不存在的记录
                "field": "material",
                "value": "718"
            }
        ])
        
        # 提交修改
        result = await agent.handle_modification(
            job_id,
            "将 NOT_EXIST 的材质改为 718",
            user_id
        )
        
        # 验证错误处理
        assert result.status == "error"
        assert "验证失败" in result.message


class TestMultiRoundModification:
    """测试多轮修改流程"""
    
    @pytest.mark.asyncio
    async def test_multiple_modifications(self):
        """
        测试多轮修改
        
        流程：
        1. 启动审核
        2. 第一次修改
        3. 第二次修改
        4. 第三次修改
        5. 确认所有修改
        """
        agent = InteractionAgent()
        job_id = "test_job_multi_001"
        user_id = "user_123"
        
        # 模拟依赖
        agent._redis_client = AsyncMock()
        agent._review_repo = AsyncMock()
        agent._nlp_parser = AsyncMock()
        
        # 模拟数据库会话
        db_session = AsyncMock()
        db_session.commit = AsyncMock()
        
        # 启动审核
        agent._redis_client.set = AsyncMock(return_value=True)
        mock_data = {
            "features": [],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5},
                {"subgraph_id": "DOWN01", "material": "718", "weight": 6.0}
            ]
        }
        agent._review_repo.get_all_review_data = AsyncMock(return_value=mock_data)
        agent._redis_client.publish = AsyncMock()
        
        result = await agent.start_review(job_id, db_session)
        assert result.status == "ok"
        
        # 初始状态
        state = {
            "status": "reviewing",
            "data": mock_data,
            "modifications": []
        }
        
        # === 第一次修改 ===
        agent._redis_client.exists = AsyncMock(return_value=1)
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        agent._redis_client.set = AsyncMock()
        
        agent._nlp_parser.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "UP01", "field": "material", "value": "NAK80"}
        ])
        
        result1 = await agent.handle_modification(
            job_id,
            "将 UP01 的材质改为 NAK80",
            user_id
        )
        assert result1.status == "ok"
        
        # 更新状态
        state["modifications"].append({"id": "mod_1", "text": "修改1"})
        state["data"]["subgraphs"][0]["material"] = "NAK80"
        
        # === 第二次修改 ===
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        agent._nlp_parser.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "UP01", "field": "weight", "value": 7.0}
        ])
        
        result2 = await agent.handle_modification(
            job_id,
            "将 UP01 的重量改为 7.0kg",
            user_id
        )
        assert result2.status == "ok"
        
        # 更新状态
        state["modifications"].append({"id": "mod_2", "text": "修改2"})
        state["data"]["subgraphs"][0]["weight"] = 7.0
        
        # === 第三次修改 ===
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        agent._nlp_parser.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "DOWN01", "field": "weight", "value": 8.0}
        ])
        
        result3 = await agent.handle_modification(
            job_id,
            "将 DOWN01 的重量改为 8.0kg",
            user_id
        )
        assert result3.status == "ok"
        
        # 更新状态
        state["modifications"].append({"id": "mod_3", "text": "修改3"})
        state["data"]["subgraphs"][1]["weight"] = 8.0
        
        # === 确认所有修改 ===
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        agent._review_repo.update_all_review_data = AsyncMock()
        agent._redis_client.delete = AsyncMock()
        
        result = await agent.confirm_changes(job_id, user_id, db_session)
        
        # 验证
        assert result.status == "ok"
        assert result.data["modifications_count"] == 3
        
        # 验证数据库更新
        agent._review_repo.update_all_review_data.assert_called_once()
        call_args = agent._review_repo.update_all_review_data.call_args
        updated_data = call_args[0][2]
        
        # 验证数据正确性
        assert updated_data["subgraphs"][0]["material"] == "NAK80"
        assert updated_data["subgraphs"][0]["weight"] == 7.0
        assert updated_data["subgraphs"][1]["weight"] == 8.0


class TestErrorRecovery:
    """测试错误恢复流程"""
    
    @pytest.mark.asyncio
    async def test_database_rollback_on_error(self):
        """
        测试数据库错误时的回滚
        
        流程：
        1. 启动审核
        2. 提交修改
        3. 确认修改（数据库更新失败）
        4. 验证回滚
        """
        agent = InteractionAgent()
        job_id = "test_job_rollback_001"
        user_id = "user_123"
        
        # 模拟依赖
        agent._redis_client = AsyncMock()
        agent._review_repo = AsyncMock()
        agent._nlp_parser = AsyncMock()
        
        # 模拟数据库会话
        db_session = AsyncMock()
        db_session.commit = AsyncMock()
        db_session.rollback = AsyncMock()
        
        # 启动审核
        agent._redis_client.set = AsyncMock(return_value=True)
        mock_data = {
            "features": [],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": [{"subgraph_id": "UP01", "material": "P20", "weight": 5.5}]
        }
        agent._review_repo.get_all_review_data = AsyncMock(return_value=mock_data)
        agent._redis_client.publish = AsyncMock()
        
        await agent.start_review(job_id, db_session)
        
        # 提交修改
        agent._redis_client.exists = AsyncMock(return_value=1)
        state = {
            "status": "reviewing",
            "data": mock_data,
            "modifications": [{"id": "mod_1"}]
        }
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        
        # 模拟数据库更新失败
        agent._review_repo.update_all_review_data = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        # 确认修改
        result = await agent.confirm_changes(job_id, user_id, db_session)
        
        # 验证错误处理
        assert result.status == "error"
        assert "确认修改失败" in result.message
        
        # 验证回滚被调用
        db_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lock_timeout_recovery(self):
        """
        测试锁超时恢复
        
        流程：
        1. 启动审核（获取锁）
        2. 等待锁超时
        3. 尝试操作（应该失败）
        """
        agent = InteractionAgent()
        job_id = "test_job_timeout_001"
        user_id = "user_123"
        
        # 模拟依赖
        agent._redis_client = AsyncMock()
        
        # 启动审核时锁存在
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
        
        # 第一次检查锁（存在）
        result = await agent.check_lock(job_id)
        assert result is True
        
        # 模拟锁超时（不存在）
        agent._redis_client.exists = AsyncMock(return_value=0)
        
        # 第二次检查锁（不存在）
        result = await agent.check_lock(job_id)
        assert result is False
        
        # 尝试提交修改（应该失败）
        result = await agent.handle_modification(job_id, "修改内容", user_id)
        assert result.status == "error"
        assert "已过期" in result.message


class TestWebSocketIntegration:
    """测试 WebSocket 集成"""
    
    @pytest.mark.asyncio
    async def test_websocket_message_flow(self):
        """
        测试 WebSocket 消息流
        
        验证：
        1. 启动审核时推送数据
        2. 修改时推送确认
        3. 完成时推送完成消息
        """
        agent = InteractionAgent()
        job_id = "test_job_ws_001"
        user_id = "user_123"
        
        # 模拟依赖
        agent._redis_client = AsyncMock()
        agent._review_repo = AsyncMock()
        agent._nlp_parser = AsyncMock()
        
        # 记录所有推送的消息
        published_messages = []
        
        async def mock_publish(channel, message):
            published_messages.append({
                "channel": channel,
                "message": json.loads(message)
            })
        
        agent._redis_client.publish = mock_publish
        
        # 模拟数据库会话
        db_session = AsyncMock()
        db_session.commit = AsyncMock()
        
        # === 启动审核 ===
        agent._redis_client.set = AsyncMock(return_value=True)
        mock_data = {
            "features": [],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": [{"subgraph_id": "UP01", "material": "P20", "weight": 5.5}]
        }
        agent._review_repo.get_all_review_data = AsyncMock(return_value=mock_data)
        
        await agent.start_review(job_id, db_session)
        
        # 验证推送了审核数据
        assert len(published_messages) == 1
        assert published_messages[0]["message"]["type"] == "review_data"
        
        # === 提交修改 ===
        agent._redis_client.exists = AsyncMock(return_value=1)
        state = {
            "status": "reviewing",
            "data": mock_data,
            "modifications": []
        }
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        agent._redis_client.set = AsyncMock()
        
        agent._nlp_parser.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "UP01", "field": "material", "value": "718"}
        ])
        
        await agent.handle_modification(job_id, "修改内容", user_id)
        
        # 验证推送了修改确认
        assert len(published_messages) == 2
        assert published_messages[1]["message"]["type"] == "modification_confirmation"
        
        # === 确认修改 ===
        state["modifications"].append({"id": "mod_1"})
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        agent._review_repo.update_all_review_data = AsyncMock()
        agent._redis_client.delete = AsyncMock()
        
        await agent.confirm_changes(job_id, user_id, db_session)
        
        # 验证推送了完成消息
        assert len(published_messages) == 3
        assert published_messages[2]["message"]["type"] == "review_completed"


class TestDataConsistency:
    """测试数据一致性"""
    
    @pytest.mark.asyncio
    async def test_data_consistency_after_modifications(self):
        """
        测试修改后的数据一致性
        
        验证：
        1. 修改正确应用到数据
        2. 历史记录正确保存
        3. 数据库更新数据正确
        """
        agent = InteractionAgent()
        job_id = "test_job_consistency_001"
        user_id = "user_123"
        
        # 模拟依赖
        agent._redis_client = AsyncMock()
        agent._review_repo = AsyncMock()
        agent._nlp_parser = AsyncMock()
        
        # 模拟数据库会话
        db_session = AsyncMock()
        db_session.commit = AsyncMock()
        
        # 初始数据
        original_data = {
            "features": [],
            "price_snapshots": [],
            "process_snapshots": [],
            "subgraphs": [
                {"subgraph_id": "UP01", "material": "P20", "weight": 5.5},
                {"subgraph_id": "DOWN01", "material": "718", "weight": 6.0}
            ]
        }
        
        # 启动审核
        agent._redis_client.set = AsyncMock(return_value=True)
        agent._review_repo.get_all_review_data = AsyncMock(
            return_value=original_data.copy()
        )
        agent._redis_client.publish = AsyncMock()
        
        await agent.start_review(job_id, db_session)
        
        # 提交修改
        agent._redis_client.exists = AsyncMock(return_value=1)
        state = {
            "status": "reviewing",
            "data": original_data.copy(),
            "modifications": []
        }
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        agent._redis_client.set = AsyncMock()
        
        # 修改 UP01 的材质
        agent._nlp_parser.parse = AsyncMock(return_value=[
            {"table": "subgraphs", "id": "UP01", "field": "material", "value": "NAK80"}
        ])
        
        result = await agent.handle_modification(
            job_id,
            "将 UP01 的材质改为 NAK80",
            user_id
        )
        
        # 验证修改应用正确
        modified_data = result.data["modified_data"]
        assert modified_data["subgraphs"][0]["material"] == "NAK80"
        assert modified_data["subgraphs"][1]["material"] == "718"  # 未修改的保持不变
        
        # 确认修改
        state["modifications"].append({"id": "mod_1"})
        state["data"] = modified_data
        agent._redis_client.get = AsyncMock(
            return_value=json.dumps(state, ensure_ascii=False)
        )
        agent._review_repo.update_all_review_data = AsyncMock()
        agent._redis_client.delete = AsyncMock()
        
        await agent.confirm_changes(job_id, user_id, db_session)
        
        # 验证数据库更新的数据
        call_args = agent._review_repo.update_all_review_data.call_args
        updated_data = call_args[0][2]
        
        assert updated_data["subgraphs"][0]["material"] == "NAK80"
        assert updated_data["subgraphs"][1]["material"] == "718"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
