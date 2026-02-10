#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Token自动刷新功能
"""

import requests
import json
import time
from datetime import datetime

base_url = "http://192.168.0.14:8000"

print("=" * 70)
print("Token自动刷新功能测试")
print("=" * 70)

# 步骤1: 登录获取token
print("\n步骤1: 登录获取初始token")
print("-" * 70)

login_data = {
    "username": "admin",
    "password": "123456"
}

response = requests.post(f"{base_url}/api/login", json=login_data)
result = response.json()

if not result.get('success'):
    print(f"✗ 登录失败: {result.get('message')}")
    exit(1)

token = result.get('token')
print(f"✓ 登录成功")
print(f"Token: {token[:50]}...")

# 步骤2: 使用token访问受保护的接口
print("\n步骤2: 使用token访问接口")
print("-" * 70)

headers = {
    "Authorization": f"Bearer {token}"
}

# 测试价格项列表接口
response = requests.get(f"{base_url}/api/price-items?page=1&page_size=5", headers=headers)
result = response.json()

print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}...")

# 检查是否有新token
if 'new_token' in result:
    print(f"\n✓ 收到新token（token已刷新）")
    print(f"新Token: {result['new_token'][:50]}...")
    token = result['new_token']  # 更新token
else:
    print(f"\n- Token未刷新（剩余时间充足）")

# 步骤3: 说明刷新机制
print("\n" + "=" * 70)
print("Token自动刷新机制说明")
print("=" * 70)

print("""
工作原理:
1. 每次请求受保护的接口时，服务器会检查token的剩余有效时间
2. 如果剩余时间小于总时间的50%（可配置），服务器会生成新token
3. 新token会在响应中返回（字段名: new_token）
4. 客户端收到新token后，应该更新本地存储的token

配置参数:
- JWT_ACCESS_TOKEN_EXPIRE_MINUTES: token总有效期（当前: 30000分钟）
- refresh_threshold: 刷新阈值（默认: 0.5，即50%）
- 刷新窗口 = 总有效期 × 刷新阈值 = 30000 × 0.5 = 15000分钟

示例:
- Token总有效期: 30分钟
- 刷新阈值: 0.5 (50%)
- 刷新窗口: 15分钟
- 当剩余时间 < 15分钟时，自动生成新token

优点:
✓ 用户无感知，自动延长会话
✓ 不需要单独的刷新接口
✓ 提高用户体验
✓ 保持安全性

客户端处理:
```javascript
// 发送请求
const response = await fetch(url, {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});

const data = await response.json();

// 检查是否有新token
if (data.new_token) {
    // 更新本地存储的token
    localStorage.setItem('token', data.new_token);
    console.log('Token已自动刷新');
}
```
""")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
