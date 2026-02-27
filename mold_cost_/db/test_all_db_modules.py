#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试所有数据库模块的配置
确保所有模块都使用正确的数据库配置
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import os

print("=" * 70)
print("测试所有数据库模块配置")
print("=" * 70)

# 加载环境变量
load_dotenv()

# 测试 1: api_gateway/config.py
print("\n1. 测试 api_gateway/config.py:")
try:
    from api_gateway.config import settings
    print(f"   ✅ 加载成功")
    print(f"   DB_HOST: {settings.DB_HOST}")
    print(f"   DB_NAME: {settings.DB_NAME}")
    print(f"   DATABASE_URL: {settings.DATABASE_URL}")
    
    if settings.DB_HOST == "localhost" and settings.DB_NAME == "mold_cost":
        print(f"   ✅ 配置正确 - 使用本地数据库")
    else:
        print(f"   ❌ 配置错误 - 使用了远程数据库")
except Exception as e:
    print(f"   ❌ 加载失败: {e}")

# 测试 2: api_gateway/database.py
print("\n2. 测试 api_gateway/database.py:")
try:
    from api_gateway.database import DB_CONFIG
    print(f"   ✅ 加载成功")
    print(f"   host: {DB_CONFIG['host']}")
    print(f"   database: {DB_CONFIG['database']}")
    
    if DB_CONFIG['host'] == "localhost" and DB_CONFIG['database'] == "mold_cost":
        print(f"   ✅ 配置正确 - 使用本地数据库")
    else:
        print(f"   ❌ 配置错误 - 使用了远程数据库")
except Exception as e:
    print(f"   ❌ 加载失败: {e}")

# 测试 3: shared/database.py
print("\n3. 测试 shared/database.py:")
try:
    # 重新加载以获取最新配置
    import importlib
    import shared.database
    importlib.reload(shared.database)
    
    from shared.database import DATABASE_URL
    print(f"   ✅ 加载成功")
    print(f"   DATABASE_URL: {DATABASE_URL}")
    
    if "localhost" in DATABASE_URL and "mold_cost" in DATABASE_URL and "mold_cost_db" not in DATABASE_URL:
        print(f"   ✅ 配置正确 - 使用本地数据库")
    else:
        print(f"   ❌ 配置错误 - 使用了远程数据库")
except Exception as e:
    print(f"   ❌ 加载失败: {e}")

print("\n" + "=" * 70)
print("总结:")
print("=" * 70)
print("如果所有模块都显示 '✅ 配置正确'，说明问题已解决")
print("如果仍有模块显示 '❌ 配置错误'，请检查对应模块的代码")
print("=" * 70)
