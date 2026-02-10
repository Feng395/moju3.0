"""
测试 datetime 序列化修复
"""
import json
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_gateway.repositories.chat_history_repository import json_serializer


def test_json_serializer_with_datetime():
    """测试 datetime 对象序列化"""
    now = datetime.now()
    
    # 测试单个 datetime 对象
    result = json_serializer(now)
    assert isinstance(result, str)
    assert 'T' in result  # ISO format 包含 T
    print(f"✅ datetime 序列化成功: {result}")


def test_json_dumps_with_datetime():
    """测试 json.dumps 使用自定义序列化器"""
    metadata = {
        'message_type': 'progress',
        'timestamp': datetime.now(),
        'original_ws_message': {
            'type': 'progress',
            'timestamp': datetime.now(),
            'data': {
                'stage': 'processing',
                'created_at': datetime.now()
            }
        }
    }
    
    # 使用自定义序列化器
    result = json.dumps(metadata, default=json_serializer)
    assert isinstance(result, str)
    
    # 验证可以反序列化
    parsed = json.loads(result)
    assert parsed['message_type'] == 'progress'
    assert isinstance(parsed['timestamp'], str)
    print(f"✅ 复杂对象序列化成功")
    print(f"   原始 timestamp 类型: {type(metadata['timestamp'])}")
    print(f"   序列化后 timestamp: {parsed['timestamp']}")


def test_json_serializer_with_unsupported_type():
    """测试不支持的类型"""
    class CustomObject:
        pass
    
    obj = CustomObject()
    
    try:
        json_serializer(obj)
        assert False, "应该抛出 TypeError"
    except TypeError as e:
        assert "CustomObject" in str(e)
        print(f"✅ 不支持的类型正确抛出异常: {e}")


if __name__ == '__main__':
    print("🧪 测试 datetime 序列化修复\n")
    
    test_json_serializer_with_datetime()
    test_json_dumps_with_datetime()
    test_json_serializer_with_unsupported_type()
    
    print("\n✅ 所有测试通过！")
