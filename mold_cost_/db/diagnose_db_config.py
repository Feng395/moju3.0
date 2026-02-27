#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库配置诊断脚本
用于检查当前实际使用的数据库配置
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import os

print("=" * 70)
print("数据库配置诊断")
print("=" * 70)

# 1. 检查 .env 文件是否存在
env_file = project_root / ".env"
print(f"\n1. .env 文件检查:")
print(f"   路径: {env_file}")
print(f"   存在: {'✅ 是' if env_file.exists() else '❌ 否'}")

# 2. 加载环境变量
print(f"\n2. 加载环境变量...")
load_dotenv()
print(f"   ✅ 已加载")

# 3. 读取环境变量
print(f"\n3. 环境变量值:")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

print(f"   DB_HOST: {db_host}")
print(f"   DB_PORT: {db_port}")
print(f"   DB_NAME: {db_name}")
print(f"   DB_USER: {db_user}")
print(f"   DB_PASSWORD: {'*' * len(db_password) if db_password else None}")

# 4. 加载配置类
print(f"\n4. 配置类加载:")
try:
    from api_gateway.config import settings
    print(f"   ✅ 配置类加载成功")
    print(f"\n5. 配置类实际值:")
    print(f"   DB_HOST: {settings.DB_HOST}")
    print(f"   DB_PORT: {settings.DB_PORT}")
    print(f"   DB_NAME: {settings.DB_NAME}")
    print(f"   DB_USER: {settings.DB_USER}")
    print(f"   DB_PASSWORD: {'*' * len(settings.DB_PASSWORD)}")
    print(f"\n6. 数据库连接URL:")
    print(f"   {settings.DATABASE_URL}")
except Exception as e:
    print(f"   ❌ 配置类加载失败: {e}")

# 7. 判断使用的是哪个数据库
print(f"\n7. 数据库判断:")
if settings.DB_HOST == "localhost" and settings.DB_NAME == "mold_cost":
    print(f"   ✅ 使用本地数据库 (localhost:5432/mold_cost)")
elif settings.DB_HOST == "192.168.1.54" and settings.DB_NAME == "mold_cost_db":
    print(f"   ⚠️  使用远程数据库 (192.168.1.54:5432/mold_cost_db)")
else:
    print(f"   ❓ 使用未知配置 ({settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME})")

print("\n" + "=" * 70)
