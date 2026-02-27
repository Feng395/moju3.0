#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实际数据库连接测试
测试运行时真正连接的是哪个数据库
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("实际数据库连接测试")
print("=" * 70)

# 1. 测试环境变量加载
print("\n1. 环境变量检查:")
from dotenv import load_dotenv
import os

# 清除可能存在的环境变量
for key in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']:
    if key in os.environ:
        print(f"   清除已存在的环境变量: {key}")
        del os.environ[key]

# 重新加载 .env
load_dotenv(override=True)
print(f"   DB_HOST: {os.getenv('DB_HOST')}")
print(f"   DB_NAME: {os.getenv('DB_NAME')}")

# 2. 测试 shared/database.py 实际连接
print("\n2. 测试 shared/database.py:")
try:
    from shared.database import engine, DATABASE_URL
    print(f"   DATABASE_URL: {DATABASE_URL}")
    
    # 尝试实际连接
    async def test_connection():
        try:
            async with engine.connect() as conn:
                result = await conn.execute("SELECT current_database(), inet_server_addr(), inet_server_port()")
                row = result.fetchone()
                return row
        except Exception as e:
            return f"连接失败: {e}"
    
    result = asyncio.run(test_connection())
    if isinstance(result, str):
        print(f"   ❌ {result}")
    else:
        print(f"   ✅ 连接成功")
        print(f"   数据库名: {result[0]}")
        print(f"   服务器IP: {result[1]}")
        print(f"   服务器端口: {result[2]}")
        
        if result[0] == "mold_cost" and (result[1] is None or result[1] == "127.0.0.1"):
            print(f"   ✅ 确认使用本地数据库")
        elif result[0] == "mold_cost_db":
            print(f"   ❌ 错误：使用了远程数据库！")
        
except Exception as e:
    print(f"   ❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 测试 api_gateway/database.py
print("\n3. 测试 api_gateway/database.py:")
try:
    from api_gateway.database import db, DB_CONFIG
    print(f"   配置: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    # 尝试实际连接
    async def test_db_wrapper():
        try:
            result = await db.fetch_one("SELECT current_database(), inet_server_addr(), inet_server_port()")
            return result
        except Exception as e:
            return f"连接失败: {e}"
    
    result = asyncio.run(test_db_wrapper())
    if isinstance(result, dict):
        print(f"   ✅ 连接成功")
        print(f"   数据库名: {result.get('current_database')}")
        print(f"   服务器IP: {result.get('inet_server_addr')}")
        print(f"   服务器端口: {result.get('inet_server_port')}")
        
        if result.get('current_database') == "mold_cost":
            print(f"   ✅ 确认使用本地数据库")
        elif result.get('current_database') == "mold_cost_db":
            print(f"   ❌ 错误：使用了远程数据库！")
    else:
        print(f"   ❌ {result}")
        
except Exception as e:
    print(f"   ❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
