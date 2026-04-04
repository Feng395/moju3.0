#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""服务诊断工具。"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def _print_header(title: str) -> None:
    print("-" * 80)
    print(title)
    print("-" * 80)


def run_diagnostics() -> int:
    """执行服务诊断。"""
    print("=" * 80)
    print("服务诊断工具")
    print("=" * 80)
    print()

    print(f"当前工作目录: {os.getcwd()}")
    print(f"项目根目录: {PROJECT_ROOT}")
    print()

    print("Python 搜索路径:")
    for index, path in enumerate(sys.path, 1):
        print(f"  {index}. {path}")
    print()

    print("环境变量检查:")
    for var_name in [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
    ]:
        value = os.getenv(var_name)
        if value:
            if "PASSWORD" in var_name or "SECRET" in var_name or "KEY" in var_name:
                value = "*" * 8
            print(f"  OK {var_name} = {value}")
        else:
            print(f"  FAIL {var_name} = (未设置)")
    print()

    _print_header("【拆图服务】模块导入测试")
    try:
        from mold_cost.domain.cad.services.split_service import cad_split_service

        print("OK 拆图服务模块导入成功")
        print(f"   cad_split_service: {cad_split_service}")
    except Exception as exc:
        print("FAIL 拆图服务模块导入失败")
        print(f"   错误类型: {type(exc).__name__}")
        print(f"   错误信息: {exc}")
        print("\n详细错误堆栈:")
        traceback.print_exc()
    print()

    _print_header("【特征识别服务】模块导入测试")
    try:
        from mold_cost.domain.features.services import feature_recognition_service

        print("OK 特征识别服务模块导入成功")
        print(f"   feature_recognition_service: {feature_recognition_service}")
    except Exception as exc:
        print("FAIL 特征识别服务模块导入失败")
        print(f"   错误类型: {type(exc).__name__}")
        print(f"   错误信息: {exc}")
        print("\n详细错误堆栈:")
        traceback.print_exc()
    print()

    _print_header("【依赖包】检查")
    dependencies = [
        "ezdxf",
        "psycopg2",
        "minio",
        "fastapi",
        "uvicorn",
        "pydantic",
        "python-dotenv",
        "loguru",
    ]
    for dependency in dependencies:
        try:
            __import__(dependency.replace("-", "_"))
            print(f"  OK {dependency}")
        except ImportError:
            print(f"  FAIL {dependency} (未安装)")
    print()

    print("=" * 80)
    print("诊断完成")
    print("=" * 80)
    return 0


def main() -> int:
    """命令行入口。"""
    return run_diagnostics()


if __name__ == "__main__":
    raise SystemExit(main())
