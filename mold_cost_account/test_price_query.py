#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试价格项查询
"""

import requests
import json

base_url = "http://192.168.0.14:8000/api/price-items"

print("=" * 60)
print("测试价格项查询")
print("=" * 60)

# 1. 查询单个价格项
print("\n1. 查询单个价格项 P044")
try:
    response = requests.get(f"{base_url}/P044")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")

# 2. 查询所有价格项（无筛选）
print("\n2. 查询所有价格项（无筛选）")
try:
    response = requests.get(base_url)
    result = response.json()
    print(f"状态码: {response.status_code}")
    print(f"总数: {result['data']['total']}")
    print(f"当前页数据量: {len(result['data']['data'])}")
    
    # 查找P044
    found = False
    for item in result['data']['data']:
        if item['id'] == 'P044':
            print(f"\n✅ 找到P044:")
            print(json.dumps(item, indent=2, ensure_ascii=False))
            found = True
            break
    
    if not found:
        print("\n❌ 未找到P044")
        print(f"返回的数据: {json.dumps(result['data']['data'][:3], indent=2, ensure_ascii=False)}")
        
except Exception as e:
    print(f"错误: {e}")

# 3. 按category筛选
print("\n3. 按category=wire筛选")
try:
    response = requests.get(f"{base_url}?category=wire")
    result = response.json()
    print(f"状态码: {response.status_code}")
    print(f"总数: {result['data']['total']}")
    
    # 查找P044
    found = False
    for item in result['data']['data']:
        if item['id'] == 'P044':
            print(f"\n✅ 找到P044:")
            print(json.dumps(item, indent=2, ensure_ascii=False))
            found = True
            break
    
    if not found:
        print("\n❌ 未找到P044")
        
except Exception as e:
    print(f"错误: {e}")

# 4. 按sub_category筛选
print("\n4. 按sub_category=perforation筛选")
try:
    response = requests.get(f"{base_url}?sub_category=perforation")
    result = response.json()
    print(f"状态码: {response.status_code}")
    print(f"总数: {result['data']['total']}")
    
    # 查找P044
    found = False
    for item in result['data']['data']:
        if item['id'] == 'P044':
            print(f"\n✅ 找到P044:")
            print(json.dumps(item, indent=2, ensure_ascii=False))
            found = True
            break
    
    if not found:
        print("\n❌ 未找到P044")
        
except Exception as e:
    print(f"错误: {e}")

# 5. 检查数据库中是否真的存在
print("\n5. 直接查询数据库")
try:
    import sys
    sys.path.insert(0, '.')
    from app.services.database import db_manager
    
    query = "SELECT * FROM price_items WHERE id = %s"
    result = db_manager.execute_query(query, ('P044',), fetch_one=True)
    
    if result:
        print("✅ 数据库中存在P044:")
        print(json.dumps(dict(result), indent=2, ensure_ascii=False, default=str))
    else:
        print("❌ 数据库中不存在P044")
        
except Exception as e:
    print(f"数据库查询错误: {e}")

print("\n" + "=" * 60)
