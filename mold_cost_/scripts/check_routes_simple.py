#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单路由检查
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量避免日志emoji问题
import os
os.environ['LOG_LEVEL'] = 'ERROR'

from api_gateway.main import app

print("=" * 70)
print("Registered Routes")
print("=" * 70)

# 账户相关路由
account_routes = []
for route in app.routes:
    if hasattr(route, 'path'):
        path = route.path
        if any(keyword in path for keyword in ['/login', '/verify-token', '/chat-sessions', '/process-rules', '/price-items']):
            methods = ', '.join(route.methods) if hasattr(route, 'methods') else 'N/A'
            account_routes.append((methods, path))

print("\nAccount System Routes:")
print("-" * 70)
for methods, path in sorted(account_routes, key=lambda x: x[1]):
    print(f"{methods:15} {path}")

print("\n" + "=" * 70)
print(f"Total account routes: {len(account_routes)}")
print("=" * 70)

# 检查关键路由
critical_routes = [
    '/api/login',
    '/api/verify-token',
    '/api/chat-sessions/',
    '/api/process-rules',
    '/api/price-items'
]

print("\nCritical Routes Check:")
print("-" * 70)
all_paths = [route.path for route in app.routes if hasattr(route, 'path')]
for route_path in critical_routes:
    exists = route_path in all_paths or route_path.rstrip('/') in all_paths
    status = "OK" if exists else "MISSING"
    print(f"{status:10} {route_path}")

print("=" * 70)
