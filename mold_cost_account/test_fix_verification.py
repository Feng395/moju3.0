#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证数据库事务提交修复
"""

import requests
import json
import time
import sys

base_url = "http://192.168.0.14:8000/api"

print("=" * 70)
print("验证数据库事务提交修复")
print("=" * 70)

# 步骤1: 删除旧的测试数据
print("\n步骤1: 清理旧的测试数据...")
test_ids = ["P044", "P999"]
for test_id in test_ids:
    try:
        response = requests.delete(f"{base_url}/price-items/{test_id}")
        if response.status_code == 200:
            print(f"  ✓ 删除 {test_id}")
        else:
            print(f"  - {test_id} 不存在或已删除")
    except Exception as e:
        print(f"  - 删除 {test_id} 失败: {e}")

time.sleep(1)

# 步骤2: 创建新的价格项
print("\n步骤2: 创建新的价格项 P999...")
create_data = {
    "id": "P999",
    "category": "wire",
    "sub_category": "perforation",
    "price": "9.99",
    "unit": "元/mm",
    "note": "测试事务提交修复",
    "is_active": True
}

try:
    response = requests.post(f"{base_url}/price-items", json=create_data)
    print(f"  状态码: {response.status_code}")
    result = response.json()
    print(f"  响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get('success'):
        print("  ✓ 创建成功")
    else:
        print(f"  ✗ 创建失败: {result.get('message')}")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ 创建请求失败: {e}")
    sys.exit(1)

time.sleep(1)

# 步骤3: 通过API查询
print("\n步骤3: 通过API查询 P999...")
try:
    response = requests.get(f"{base_url}/price-items/P999")
    print(f"  状态码: {response.status_code}")
    result = response.json()
    
    if result.get('success') and result.get('data'):
        print("  ✓ API查询成功")
        print(f"  数据: {json.dumps(result['data'], indent=2, ensure_ascii=False)}")
    else:
        print(f"  ✗ API查询失败: {result.get('message')}")
except Exception as e:
    print(f"  ✗ 查询请求失败: {e}")

# 步骤4: 直接查询数据库
print("\n步骤4: 直接查询数据库...")
try:
    sys.path.insert(0, '.')
    from app.services.database import db_manager
    
    query = "SELECT * FROM price_items WHERE id = %s"
    db_result = db_manager.execute_query(query, ('P999',), fetch_one=True)
    
    if db_result:
        print("  ✓ 数据库中存在 P999")
        print(f"  数据: {json.dumps(db_result, indent=2, ensure_ascii=False, default=str)}")
    else:
        print("  ✗ 数据库中不存在 P999 - 事务未提交！")
except Exception as e:
    print(f"  ✗ 数据库查询失败: {e}")

# 步骤5: 测试工艺规则
print("\n步骤5: 测试工艺规则创建...")
rule_data = {
    "id": "R999",
    "version_id": "v1.0",
    "feature_type": "WIRE",
    "name": "测试规则",
    "conditions": "test_condition",
    "output_params": "test_output",
    "priority": 1,
    "is_active": True
}

try:
    response = requests.post(f"{base_url}/process-rules", json=rule_data)
    print(f"  状态码: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        print("  ✓ 工艺规则创建成功")
        
        # 查询验证
        time.sleep(1)
        response = requests.get(f"{base_url}/process-rules/R999")
        if response.status_code == 200 and response.json().get('success'):
            print("  ✓ 工艺规则查询成功")
        else:
            print("  ✗ 工艺规则查询失败")
    else:
        print(f"  ✗ 工艺规则创建失败: {result.get('message')}")
except Exception as e:
    print(f"  ✗ 工艺规则测试失败: {e}")

# 步骤6: 清理测试数据
print("\n步骤6: 清理测试数据...")
try:
    requests.delete(f"{base_url}/price-items/P999")
    requests.delete(f"{base_url}/process-rules/R999")
    print("  ✓ 清理完成")
except:
    pass

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
