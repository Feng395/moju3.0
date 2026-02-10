#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试工艺规则description字段
"""

import requests
import json
import time

base_url = "http://192.168.0.14:8000/api/process-rules"

print("=" * 70)
print("测试工艺规则description字段")
print("=" * 70)

# 步骤1: 删除测试数据
print("\n步骤1: 清理旧的测试数据...")
test_id = "R888"
try:
    response = requests.delete(f"{base_url}/{test_id}")
    if response.status_code == 200:
        print(f"  ✓ 删除 {test_id}")
    else:
        print(f"  - {test_id} 不存在或已删除")
except Exception as e:
    print(f"  - 删除 {test_id} 失败: {e}")

time.sleep(1)

# 步骤2: 创建带description的工艺规则
print("\n步骤2: 创建带description的工艺规则...")
create_data = {
    "id": "R888",
    "version_id": "v1.0",
    "feature_type": "WIRE",
    "name": "测试规则",
    "description": "这是一个测试规则的描述信息",
    "priority": 10,
    "is_active": True,
    "conditions": "test_condition",
    "output_params": "test_output"
}

try:
    response = requests.post(base_url, json=create_data)
    print(f"  状态码: {response.status_code}")
    result = response.json()
    print(f"  响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get('success'):
        print("  ✓ 创建成功")
        if result.get('data', {}).get('description'):
            print(f"  ✓ description字段存在: {result['data']['description']}")
        else:
            print("  ✗ description字段缺失")
    else:
        print(f"  ✗ 创建失败: {result.get('message')}")
except Exception as e:
    print(f"  ✗ 创建请求失败: {e}")

time.sleep(1)

# 步骤3: 查询单个规则
print("\n步骤3: 查询单个规则...")
try:
    response = requests.get(f"{base_url}/{test_id}")
    print(f"  状态码: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        print("  ✓ 查询成功")
        data = result.get('data', {})
        if 'description' in data:
            print(f"  ✓ description字段存在: {data['description']}")
        else:
            print("  ✗ description字段缺失")
        print(f"  完整数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
    else:
        print(f"  ✗ 查询失败: {result.get('message')}")
except Exception as e:
    print(f"  ✗ 查询请求失败: {e}")

# 步骤4: 查询列表
print("\n步骤4: 查询规则列表...")
try:
    response = requests.get(f"{base_url}?page=1&page_size=20")
    print(f"  状态码: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        print("  ✓ 查询成功")
        items = result.get('data', {}).get('data', [])
        found = False
        for item in items:
            if item['id'] == test_id:
                found = True
                if 'description' in item:
                    print(f"  ✓ 列表中R888的description字段存在: {item['description']}")
                else:
                    print("  ✗ 列表中R888的description字段缺失")
                break
        if not found:
            print(f"  - 列表中未找到{test_id}")
    else:
        print(f"  ✗ 查询失败: {result.get('message')}")
except Exception as e:
    print(f"  ✗ 查询请求失败: {e}")

# 步骤5: 更新description
print("\n步骤5: 更新description字段...")
update_data = {
    "description": "更新后的描述信息"
}

try:
    response = requests.put(f"{base_url}/{test_id}", json=update_data)
    print(f"  状态码: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        print("  ✓ 更新成功")
        data = result.get('data', {})
        if data.get('description') == "更新后的描述信息":
            print(f"  ✓ description已更新: {data['description']}")
        else:
            print(f"  ✗ description未正确更新: {data.get('description')}")
    else:
        print(f"  ✗ 更新失败: {result.get('message')}")
except Exception as e:
    print(f"  ✗ 更新请求失败: {e}")

# 步骤6: 清理测试数据
print("\n步骤6: 清理测试数据...")
try:
    response = requests.delete(f"{base_url}/{test_id}")
    if response.status_code == 200:
        print("  ✓ 清理完成")
    else:
        print("  - 清理失败")
except:
    pass

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
