#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""板料线集成验证工具。"""

from __future__ import annotations

import os
import py_compile
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def check_file_exists(file_path: Path, description: str) -> bool:
    """检查文件是否存在。"""
    exists = file_path.exists()
    status = "OK" if exists else "FAIL"
    print(f"{status} {description}: {file_path}")
    return exists


def check_env_variable(var_name: str, description: str) -> bool:
    """检查环境变量。"""
    value = os.getenv(var_name)
    if value is not None:
        print(f"OK {description}: {var_name}={value}")
        return True
    print(f"WARN {description}: {var_name} 未设置（将使用默认值）")
    return False


def verify_integration() -> bool:
    """验证板料线集成。"""
    print("=" * 80)
    print("板料线集成验证")
    print("=" * 80)

    all_checks: list[bool] = []

    print("\n【1】检查新增文件")
    print("-" * 80)
    all_checks.append(check_file_exists(SCRIPTS_ROOT / "cad_chaitu" / "material_line_integrator.py", "板料线集成器"))
    all_checks.append(check_file_exists(SCRIPTS_ROOT / "cad_chaitu" / "README_MATERIAL_LINE.md", "板料线功能说明"))
    all_checks.append(check_file_exists(SCRIPTS_ROOT / "test_material_line_integration.py", "测试脚本"))
    all_checks.append(check_file_exists(PROJECT_ROOT / ".env.example", "环境变量示例"))

    print("\n【2】检查修改文件")
    print("-" * 80)
    all_checks.append(check_file_exists(SCRIPTS_ROOT / "cad_chaitu" / "main.py", "拆图主模块"))
    all_checks.append(check_file_exists(SCRIPTS_ROOT / "cad_chaitu" / "__init__.py", "模块初始化文件"))

    print("\n【3】检查代码集成")
    print("-" * 80)
    main_py = SCRIPTS_ROOT / "cad_chaitu" / "main.py"
    try:
        content = main_py.read_text(encoding="utf-8")
        checks = [
            ("MaterialLineIntegrator导入", "MaterialLineIntegrator" in content),
            ("板料线添加逻辑", "add_material_lines_to_subgraph" in content),
            ("material_line_time变量", "material_line_time" in content),
            ("ENABLE_MATERIAL_LINES检查", "ENABLE_MATERIAL_LINES" in content),
        ]
        for description, result in checks:
            status = "OK" if result else "FAIL"
            print(f"{status} {description}")
            all_checks.append(result)
    except Exception as exc:
        print(f"FAIL 读取 main.py 失败: {exc}")
        all_checks.append(False)

    print("\n【4】检查模块语法")
    print("-" * 80)
    try:
        py_compile.compile(str(SCRIPTS_ROOT / "cad_chaitu" / "material_line_integrator.py"), doraise=True)
        print("OK 板料线集成器模块: 语法检查通过")
        all_checks.append(True)
    except Exception as exc:
        print(f"FAIL 板料线集成器模块: 语法错误 - {exc}")
        all_checks.append(False)

    print("\n【5】检查环境变量")
    print("-" * 80)
    try:
        from scripts.config_loader import load_config

        load_config()
        print("OK 已加载配置文件（主配置 + scripts 专用配置）")
    except Exception as exc:
        print(f"WARN 加载配置失败: {exc}")

    check_env_variable("ENABLE_MATERIAL_LINES", "板料线功能开关")
    check_env_variable("DB_HOST", "数据库主机")
    check_env_variable("ODA_FILE_CONVERTER_PATH", "ODA转换器路径")

    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)

    passed = sum(all_checks)
    total = len(all_checks)
    success_rate = (passed / total * 100) if total else 0.0
    print(f"通过: {passed}/{total} ({success_rate:.1f}%)")

    if passed == total:
        print("\nOK 所有检查通过，集成成功")
        print("\n下一步：")
        print("  1. 配置 .env 文件")
        print("  2. 重启服务")
        print("  3. 运行测试: python scripts/test_material_line_integration.py")
        return True

    print(f"\nWARN 仍有 {total - passed} 项检查未通过")
    return False


def print_quick_start() -> None:
    """打印快速开始说明。"""
    print("\n" + "=" * 80)
    print("快速开始")
    print("=" * 80)
    print(
        """
1. 配置环境变量:
   cp .env.example .env

2. 启用板料线功能:
   ENABLE_MATERIAL_LINES=true

3. 重启服务:
   python scripts/unified_api.py

4. 调用拆图接口:
   curl -X POST http://localhost:8200/api/chaitu -H "Content-Type: application/json" -d "{\"job_id\": \"YOUR_JOB_ID\"}"
"""
    )


def main() -> int:
    """命令行入口。"""
    success = verify_integration()
    if success:
        print_quick_start()
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
