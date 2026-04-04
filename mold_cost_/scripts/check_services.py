#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
服务诊断脚本 - 检查服务模块是否可以正常导入
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from refactor_bootstrap import ensure_src_path

ensure_src_path()

print("=" * 80)
print("服务诊断工具")
print("=" * 80)
print()

# 检查当前工作目录
print(f"当前工作目录: {os.getcwd()}")
print(f"脚本所在目录: {Path(__file__).parent}")
print()

# 检查 Python 路径
print("Python 搜索路径:")
for i, path in enumerate(sys.path, 1):
    print(f"  {i}. {path}")
print()

# 检查环境变量
print("环境变量检查:")
env_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 
            'MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY']
for var in env_vars:
    value = os.getenv(var)
    if value:
        # 隐藏敏感信息
        if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
            display_value = '*' * 8
        else:
            display_value = value
        print(f"  ✅ {var} = {display_value}")
    else:
        print(f"  ❌ {var} = (未设置)")
print()

# 尝试导入拆图服务
print("-" * 80)
print("【拆图服务】模块导入测试")
print("-" * 80)
try:
    from cad_chaitu import chaitu_process
    print("✅ 拆图服务模块导入成功")
    print(f"   chaitu_process 函数: {chaitu_process}")
except Exception as e:
    print(f"❌ 拆图服务模块导入失败")
    print(f"   错误类型: {type(e).__name__}")
    print(f"   错误信息: {e}")
    import traceback
    print("\n详细错误堆栈:")
    traceback.print_exc()
print()

# 尝试导入特征识别服务
print("-" * 80)
print("【特征识别服务】模块导入测试")
print("-" * 80)
try:
    from mold_cost.domain.features.services import feature_recognition_service

    batch_feature_recognition_process = feature_recognition_service.batch_recognize
    print("✅ 特征识别服务模块导入成功")
    print(f"   batch_feature_recognition_process 函数: {batch_feature_recognition_process}")
except Exception as e:
    print(f"❌ 特征识别服务模块导入失败")
    print(f"   错误类型: {type(e).__name__}")
    print(f"   错误信息: {e}")
    import traceback
    print("\n详细错误堆栈:")
    traceback.print_exc()
print()

# 检查关键依赖
print("-" * 80)
print("【依赖包】检查")
print("-" * 80)
dependencies = [
    'ezdxf',
    'psycopg2',
    'minio',
    'fastapi',
    'uvicorn',
    'pydantic',
    'python-dotenv',
    'loguru'
]

for dep in dependencies:
    try:
        __import__(dep.replace('-', '_'))
        print(f"  ✅ {dep}")
    except ImportError:
        print(f"  ❌ {dep} (未安装)")
print()

print("=" * 80)
print("诊断完成")
print("=" * 80)
