"""
测试 NC 时间解析逻辑
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from decimal import Decimal
from agents.nc_time_agent import NCTimeAgent

def test_parse_operations():
    """测试操作解析"""
    agent = NCTimeAgent()
    
    # 测试数据（从 data.json 提取）
    operations = [
        {
            "operation_name": "Z_ZXZ",
            "parameters": [
                {"id": 124, "display_name": "Toolpath Time", "value": 0.3202303106282315}
            ]
        },
        {
            "operation_name": "Z_L_A3",
            "parameters": [
                {"id": 124, "display_name": "Toolpath Time", "value": 5.970809138936588}
            ]
        },
        {
            "operation_name": "Z_M1_A9",
            "parameters": [
                {"id": 124, "display_name": "Toolpath Time", "value": 1.8709515170039352}
            ]
        },
        {
            "operation_name": "开粗_110_行腔_SIMPLE_17R0.8",
            "parameters": [
                {"id": 124, "display_name": "Toolpath Time", "value": 14.82447987555903}
            ]
        },
        {
            "operation_name": "半精_170_往复等高_SIMPLE_D14",
            "parameters": [
                {"id": 124, "display_name": "Toolpath Time", "value": 13.114826443442015}
            ]
        },
        {
            "operation_name": "全精_170_MIAN1_SIMPLE_D10",
            "parameters": [
                {"id": 124, "display_name": "Toolpath Time", "value": 0.16396633788283482}
            ]
        }
    ]
    
    # 解析
    result = agent._parse_operations(operations)
    
    print("=" * 80)
    print("NC 时间解析测试结果")
    print("=" * 80)
    print(f"开粗时间 (nc_roughing_time): {result['nc_roughing_time']} 分钟")
    print(f"精铣时间 (nc_milling_time): {result['nc_milling_time']} 分钟")
    print(f"钻孔时间 (drilling_time): {result['drilling_time']} 分钟")
    print("\n详细数据 (nc_details):")
    print(json.dumps(result['nc_details'], indent=2, ensure_ascii=False))
    print("=" * 80)
    
    # 验证
    assert result['drilling_time'] > 0, "钻孔时间应该大于0"
    assert result['nc_roughing_time'] > 0, "开粗时间应该大于0"
    assert result['nc_milling_time'] > 0, "精铣时间应该大于0"
    
    print("✓ 测试通过！")

def test_extract_subgraph_id():
    """测试子图ID提取"""
    agent = NCTimeAgent()
    
    test_cases = [
        ("PH-01-M250297-P5.json", "PH-01"),
        ("PH-02-M250297-P5.json", "PH-02"),
        ("PU-06-M250297-P5.json", "PU-06"),
    ]
    
    print("\n" + "=" * 80)
    print("子图ID提取测试")
    print("=" * 80)
    
    for input_name, expected_id in test_cases:
        result = agent._extract_subgraph_id(input_name)
        print(f"{input_name} -> {result}")
        assert result == expected_id, f"期望 {expected_id}，实际 {result}"
    
    print("✓ 测试通过！")

def test_is_drilling_operation():
    """测试钻孔操作判断"""
    agent = NCTimeAgent()
    
    drilling_ops = [
        "Z_ZXZ",
        "B_ZXZ",
        "Z_L_A3",
        "Z_M1_A9",
        "B_M_A9",
        "Z_L1_A3",
    ]
    
    non_drilling_ops = [
        "开粗_110_行腔_SIMPLE_17R0.8",
        "半精_170_往复等高_SIMPLE_D14",
        "全精_170_MIAN1_SIMPLE_D10",
    ]
    
    print("\n" + "=" * 80)
    print("钻孔操作判断测试")
    print("=" * 80)
    
    print("应该识别为钻孔操作:")
    for op in drilling_ops:
        result = agent._is_drilling_operation(op)
        print(f"  {op}: {result}")
        assert result, f"{op} 应该被识别为钻孔操作"
    
    print("\n应该识别为非钻孔操作:")
    for op in non_drilling_ops:
        result = agent._is_drilling_operation(op)
        print(f"  {op}: {result}")
        assert not result, f"{op} 不应该被识别为钻孔操作"
    
    print("✓ 测试通过！")

def test_extract_operation_code():
    """测试操作代码提取"""
    agent = NCTimeAgent()
    
    test_cases = [
        ("Z_ZXZ", "ZXZ"),
        ("B_ZXZ", "ZXZ"),
        ("Z_L_A3", "L"),
        ("Z_M1_A9", "M1"),
        ("B_M_A9", "M"),
    ]
    
    print("\n" + "=" * 80)
    print("操作代码提取测试")
    print("=" * 80)
    
    for input_name, expected_code in test_cases:
        result = agent._extract_operation_code(input_name)
        print(f"{input_name} -> {result}")
        assert result == expected_code, f"期望 {expected_code}，实际 {result}"
    
    print("✓ 测试通过！")

if __name__ == "__main__":
    test_extract_subgraph_id()
    test_is_drilling_operation()
    test_extract_operation_code()
    test_parse_operations()
    
    print("\n" + "=" * 80)
    print("所有测试通过！✓")
    print("=" * 80)
