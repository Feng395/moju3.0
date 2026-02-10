"""
测试子图提取修复
验证 BaseActionHandler._get_all_subgraph_ids 是否正确处理两种数据格式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.action_handlers.base_handler import BaseActionHandler


class TestHandler(BaseActionHandler):
    """测试用的 Handler"""
    
    async def handle(self, intent_result, job_id, context, db_session):
        pass


def test_get_all_subgraph_ids():
    """测试 _get_all_subgraph_ids 方法"""
    handler = TestHandler()
    
    print("=" * 60)
    print("测试子图提取功能")
    print("=" * 60)
    
    # 测试数据
    test_subgraphs = [
        {"subgraph_id": "UP01", "part_name": "上模"},
        {"subgraph_id": "UP02", "part_name": "下模"},
        {"subgraph_id": "UP03", "part_name": "滑块"}
    ]
    
    # 测试场景1: 直接格式（旧格式）
    print("\n【场景1】直接格式: context = {'subgraphs': [...]}")
    context1 = {
        "subgraphs": test_subgraphs
    }
    result1 = handler._get_all_subgraph_ids(context1)
    print(f"✅ 提取结果: {result1}")
    assert result1 == ["UP01", "UP02", "UP03"], "场景1 失败"
    
    # 测试场景2: 嵌套格式（新格式）
    print("\n【场景2】嵌套格式: context = {'raw_data': {'subgraphs': [...]}}")
    context2 = {
        "raw_data": {
            "subgraphs": test_subgraphs,
            "features": [],
            "price_snapshots": [],
            "process_snapshots": []
        },
        "display_view": [],
        "data_version": {}
    }
    result2 = handler._get_all_subgraph_ids(context2)
    print(f"✅ 提取结果: {result2}")
    assert result2 == ["UP01", "UP02", "UP03"], "场景2 失败"
    
    # 测试场景3: 空数据
    print("\n【场景3】空数据: context = {'raw_data': {'subgraphs': []}}")
    context3 = {
        "raw_data": {
            "subgraphs": []
        }
    }
    result3 = handler._get_all_subgraph_ids(context3)
    print(f"✅ 提取结果: {result3}")
    assert result3 == [], "场景3 失败"
    
    # 测试场景4: 缺少 subgraphs 字段
    print("\n【场景4】缺少 subgraphs: context = {'raw_data': {}}")
    context4 = {
        "raw_data": {}
    }
    result4 = handler._get_all_subgraph_ids(context4)
    print(f"✅ 提取结果: {result4}")
    assert result4 == [], "场景4 失败"
    
    # 测试场景5: 包含无效数据
    print("\n【场景5】包含无效数据: 部分 subgraph 缺少 subgraph_id")
    context5 = {
        "raw_data": {
            "subgraphs": [
                {"subgraph_id": "UP01", "part_name": "上模"},
                {"part_name": "下模"},  # 缺少 subgraph_id
                {"subgraph_id": "UP03", "part_name": "滑块"}
            ]
        }
    }
    result5 = handler._get_all_subgraph_ids(context5)
    print(f"✅ 提取结果: {result5}")
    assert result5 == ["UP01", "UP03"], "场景5 失败"
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    test_get_all_subgraph_ids()
