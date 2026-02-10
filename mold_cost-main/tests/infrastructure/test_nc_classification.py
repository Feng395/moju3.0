"""
测试 NC 时间数据分类逻辑
验证新的操作名称解析规则
"""
import json
from decimal import Decimal
from pathlib import Path

# 模拟 NCTimeAgent 的分类方法
def parse_operations_test(operations):
    """
    测试版本的操作解析方法
    """
    import re
    
    nc_roughing_time = Decimal("0")
    nc_milling_time = Decimal("0")
    drilling_time = Decimal("0")
    code_totals = {}
    
    for operation in operations:
        operation_name = operation.get("operation_name", "")
        
        # 提取第一个参数的 value
        parameters = operation.get("parameters", [])
        if not parameters or len(parameters) == 0:
            continue
        
        time_value = Decimal(str(parameters[0].get("value", 0)))
        
        # 分类判断
        code = None
        
        # 1. 检查是否包含"粗"字（开粗）
        if "粗" in operation_name:
            nc_roughing_time += time_value
            code = "开粗"
        
        # 2. 检查是否包含"精"字（半精、全精）
        elif "精" in operation_name:
            nc_milling_time += time_value
            if operation_name.startswith("半精"):
                code = "半精"
            elif operation_name.startswith("全精"):
                code = "全精"
            else:
                code = "精铣"
        
        # 3. 检查是否为钻孔操作
        elif is_drilling_operation(operation_name):
            drilling_time += time_value
            code = extract_operation_code(operation_name)
        
        if code is None:
            print(f"⚠️  无法分类: {operation_name}")
            continue
        
        # 汇总
        if code not in code_totals:
            code_totals[code] = Decimal("0")
        code_totals[code] += time_value
    
    # 构建 nc_details
    nc_details = []
    
    # 钻孔类型
    drilling_codes = sorted([c for c in code_totals.keys() if c not in ["开粗", "半精", "全精", "精铣"]])
    for code in drilling_codes:
        nc_details.append({
            "code": code,
            "value": str(round(code_totals[code], 2))
        })
    
    # 加工类型
    for code in ["开粗", "半精", "全精", "精铣"]:
        if code in code_totals:
            nc_details.append({
                "code": code,
                "value": str(round(code_totals[code], 2))
            })
    
    return {
        "nc_roughing_time": round(nc_roughing_time, 2),
        "nc_milling_time": round(nc_milling_time, 2),
        "drilling_time": round(drilling_time, 2),
        "nc_details": nc_details
    }

def is_drilling_operation(operation_name):
    """判断是否为钻孔操作"""
    import re
    
    # XX_ZXZ 格式
    if re.match(r"^[A-Z]+_ZXZ$", operation_name):
        return True
    
    # XX_XX_XX 格式
    if re.match(r"^[A-Z]+_[A-Z]\d*_[A-Z]\d+", operation_name):
        return True
    
    return False

def extract_operation_code(operation_name):
    """提取操作代码"""
    import re
    
    # XX_ZXZ 格式
    if re.match(r"^[A-Z]+_ZXZ$", operation_name):
        return "ZXZ"
    
    # XX_XX_XX 格式
    match = re.search(r"^[A-Z]+_([A-Z]\d*)_", operation_name)
    if match:
        return match.group(1)
    
    return operation_name

def test_with_real_data():
    """使用真实的 NC 响应数据进行测试"""
    
    # 读取真实数据
    log_file = Path("logs/nc_responses/987b7efa-e924-4dc0-9fb4-567a75db717a_20260129_124833.json")
    
    if not log_file.exists():
        print(f"❌ 测试数据文件不存在: {log_file}")
        return
    
    with open(log_file, 'r', encoding='utf-8') as f:
        nc_result = json.load(f)
    
    json_output = nc_result.get("data", {}).get("json_output", {})
    
    print("=" * 80)
    print("NC 时间数据分类测试")
    print("=" * 80)
    print()
    
    for subgraph_name, subgraph_data in json_output.items():
        print(f"📦 子图: {subgraph_name}")
        print("-" * 80)
        
        operations = subgraph_data.get("operations", [])
        
        # 显示原始操作
        print(f"原始操作 ({len(operations)} 个):")
        for op in operations:
            op_name = op.get("operation_name", "")
            params = op.get("parameters", [])
            if params:
                time_value = params[0].get("value", 0)
                print(f"  • {op_name:20s} → {time_value:.4f} 分钟")
        
        print()
        
        # 解析并分类
        result = parse_operations_test(operations)
        
        print("分类结果:")
        print(f"  开粗时间 (nc_roughing_time): {result['nc_roughing_time']} 分钟")
        print(f"  精铣时间 (nc_milling_time):  {result['nc_milling_time']} 分钟")
        print(f"  钻孔时间 (drilling_time):    {result['drilling_time']} 分钟")
        print()
        
        print("详细数据 (nc_details):")
        for detail in result['nc_details']:
            print(f"  • {detail['code']:10s} → {detail['value']:>8s} 分钟")
        
        print()
        print()

def test_operation_name_patterns():
    """测试各种操作名称格式"""
    
    test_cases = [
        # 钻孔操作
        ("Z_M_A14", True, "M"),
        ("Z_L_A3", True, "L"),
        ("B_M1_A9", True, "M1"),
        ("Z_M1_A18", True, "M1"),
        ("Z_C_A18", True, "C"),
        ("Z_ZXZ", True, "ZXZ"),
        ("B_ZXZ", True, "ZXZ"),
        
        # 加工操作（不是钻孔）
        ("开粗_160_行腔_SIMPLE_D4", False, None),
        ("半精_170_往复等高_SIMPLE_D14", False, None),
        ("全精_170_MIAN1_SIMPLE_D10", False, None),
    ]
    
    print("=" * 80)
    print("操作名称格式测试")
    print("=" * 80)
    print()
    
    all_passed = True
    
    for op_name, expected_is_drilling, expected_code in test_cases:
        is_drilling = is_drilling_operation(op_name)
        code = extract_operation_code(op_name) if is_drilling else None
        
        passed = (is_drilling == expected_is_drilling) and (code == expected_code)
        status = "✅" if passed else "❌"
        
        print(f"{status} {op_name:40s} | 钻孔: {is_drilling:5} | 代码: {code}")
        
        if not passed:
            all_passed = False
            print(f"   期望: 钻孔={expected_is_drilling}, 代码={expected_code}")
    
    print()
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败！")
    print()

if __name__ == "__main__":
    # 测试操作名称格式
    test_operation_name_patterns()
    
    # 测试真实数据
    test_with_real_data()
