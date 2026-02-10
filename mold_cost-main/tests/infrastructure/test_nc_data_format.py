"""
测试 NC 时间数据格式
验证：
1. 时间单位是分钟（不是小时）
2. nc_time_cost 按类型汇总（不是每个操作一条）
"""
import sys
from pathlib import Path
from decimal import Decimal

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.nc_time_agent import NCTimeAgent


def test_parse_operations():
    """测试操作解析"""
    print("=" * 80)
    print("测试 NC 时间数据格式")
    print("=" * 80)
    
    agent = NCTimeAgent()
    
    # 模拟 NC Agent 返回的数据
    operations = [
        {
            "operation_name": "Z_ZXZ",
            "parameters": [{"id": 124, "value": 0.19}]
        },
        {
            "operation_name": "Z_M_A14",
            "parameters": [{"id": 124, "value": 0.91}]
        },
        {
            "operation_name": "Z_M_A15",
            "parameters": [{"id": 124, "value": 1.20}]
        },
        {
            "operation_name": "Z_L_A3",
            "parameters": [{"id": 124, "value": 2.50}]
        },
        {
            "operation_name": "Z_L_A4",
            "parameters": [{"id": 124, "value": 1.80}]
        },
        {
            "operation_name": "开粗_1",
            "parameters": [{"id": 124, "value": 150.00}]
        },
        {
            "operation_name": "精铣_1",
            "parameters": [{"id": 124, "value": 75.00}]
        }
    ]
    
    print("\n📥 输入数据（模拟 NC Agent 返回）:")
    print("-" * 80)
    for op in operations:
        name = op["operation_name"]
        time = op["parameters"][0]["value"]
        print(f"  {name:<20} {time:>8.2f} 分钟")
    
    # 解析操作
    result = agent._parse_operations(operations)
    
    print("\n📊 解析结果:")
    print("-" * 80)
    print(f"开粗时间: {result['nc_roughing_time']} 分钟")
    print(f"精铣时间: {result['nc_milling_time']} 分钟")
    print(f"钻孔时间: {result['drilling_time']} 分钟")
    print(f"总时间: {result['nc_roughing_time'] + result['nc_milling_time'] + result['drilling_time']} 分钟")
    
    print("\n📋 详细数据（nc_time_cost）:")
    print("-" * 80)
    print("按类型汇总:")
    for detail in result['nc_details']:
        print(f"  {detail['code']:<10} {detail['value']:>10} 分钟")
    
    # 验证
    print("\n✅ 验证:")
    print("-" * 80)
    
    # 1. 验证时间单位是分钟
    total_input = sum(op["parameters"][0]["value"] for op in operations)
    total_output = float(result['nc_roughing_time'] + result['nc_milling_time'] + result['drilling_time'])
    
    if abs(total_input - total_output) < 0.01:
        print("✅ 时间单位正确（分钟）")
        print(f"   输入总和: {total_input:.2f} 分钟")
        print(f"   输出总和: {total_output:.2f} 分钟")
    else:
        print("❌ 时间单位错误")
        print(f"   输入总和: {total_input:.2f}")
        print(f"   输出总和: {total_output:.2f}")
    
    # 2. 验证按类型汇总
    nc_details = result['nc_details']
    
    # 检查 M 类型是否汇总
    m_details = [d for d in nc_details if d['code'] == 'M']
    if len(m_details) == 1:
        m_total = float(m_details[0]['value'])
        expected_m = 0.91 + 1.20
        if abs(m_total - expected_m) < 0.01:
            print(f"✅ M 类型已汇总: {m_total:.2f} 分钟 (0.91 + 1.20)")
        else:
            print(f"❌ M 类型汇总错误: {m_total:.2f} != {expected_m:.2f}")
    else:
        print(f"❌ M 类型未汇总，有 {len(m_details)} 条记录")
    
    # 检查 L 类型是否汇总
    l_details = [d for d in nc_details if d['code'] == 'L']
    if len(l_details) == 1:
        l_total = float(l_details[0]['value'])
        expected_l = 2.50 + 1.80
        if abs(l_total - expected_l) < 0.01:
            print(f"✅ L 类型已汇总: {l_total:.2f} 分钟 (2.50 + 1.80)")
        else:
            print(f"❌ L 类型汇总错误: {l_total:.2f} != {expected_l:.2f}")
    else:
        print(f"❌ L 类型未汇总，有 {len(l_details)} 条记录")
    
    # 检查 ZXZ 类型
    zxz_details = [d for d in nc_details if d['code'] == 'ZXZ']
    if len(zxz_details) == 1:
        zxz_total = float(zxz_details[0]['value'])
        if abs(zxz_total - 0.19) < 0.01:
            print(f"✅ ZXZ 类型正确: {zxz_total:.2f} 分钟")
        else:
            print(f"❌ ZXZ 类型错误: {zxz_total:.2f} != 0.19")
    else:
        print(f"❌ ZXZ 类型错误，有 {len(zxz_details)} 条记录")
    
    # 3. 验证输出格式
    print("\n✅ 输出格式验证:")
    print("-" * 80)
    
    # 检查是否按固定顺序输出
    codes = [d['code'] for d in nc_details]
    expected_order = ['M', 'L', 'ZXZ', '开粗', '精铣']
    actual_order = [c for c in expected_order if c in codes]
    
    if codes[:len(actual_order)] == actual_order:
        print(f"✅ 输出顺序正确: {', '.join(codes)}")
    else:
        print(f"⚠️  输出顺序: {', '.join(codes)}")
        print(f"   期望顺序: {', '.join(actual_order)}")
    
    # 检查每个 code 是否只出现一次
    code_counts = {}
    for detail in nc_details:
        code = detail['code']
        code_counts[code] = code_counts.get(code, 0) + 1
    
    duplicates = [code for code, count in code_counts.items() if count > 1]
    if not duplicates:
        print("✅ 每个类型只出现一次")
    else:
        print(f"❌ 重复的类型: {', '.join(duplicates)}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_parse_operations()
