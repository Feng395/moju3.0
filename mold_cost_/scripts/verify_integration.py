#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
板料线集成验证脚本
快速检查集成是否成功
"""

import os
import sys
from pathlib import Path


def check_file_exists(file_path: str, description: str) -> bool:
    """检查文件是否存在"""
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {file_path}")
    return exists


def check_import(module_name: str, description: str) -> bool:
    """检查模块是否可导入"""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_name} - {e}")
        return False


def check_env_variable(var_name: str, description: str) -> bool:
    """检查环境变量"""
    value = os.getenv(var_name)
    if value is not None:
        print(f"✅ {description}: {var_name}={value}")
        return True
    else:
        print(f"⚠️ {description}: {var_name} 未设置（将使用默认值）")
        return False


def verify_integration():
    """验证集成"""
    print("=" * 80)
    print("板料线集成验证")
    print("=" * 80)
    
    all_checks = []
    
    # 1. 检查新增文件
    print("\n【1】检查新增文件")
    print("-" * 80)
    all_checks.append(check_file_exists(
        "cad_chaitu/material_line_integrator.py",
        "板料线集成器"
    ))
    all_checks.append(check_file_exists(
        "cad_chaitu/README_MATERIAL_LINE.md",
        "板料线功能说明"
    ))
    all_checks.append(check_file_exists(
        "test_material_line_integration.py",
        "测试脚本"
    ))
    all_checks.append(check_file_exists(
        "INTEGRATION_GUIDE.md",
        "集成指南"
    ))
    all_checks.append(check_file_exists(
        ".env.example",
        "环境变量示例"
    ))
    
    # 2. 检查修改的文件
    print("\n【2】检查修改的文件")
    print("-" * 80)
    all_checks.append(check_file_exists(
        "cad_chaitu/main.py",
        "拆图主模块"
    ))
    all_checks.append(check_file_exists(
        "cad_chaitu/__init__.py",
        "模块初始化文件"
    ))
    
    # 3. 检查代码集成
    print("\n【3】检查代码集成")
    print("-" * 80)
    
    # 检查main.py中是否包含板料线相关代码
    try:
        with open("cad_chaitu/main.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        checks = [
            ("MaterialLineIntegrator导入", "from .material_line_integrator import MaterialLineIntegrator" in content or "from material_line_integrator import MaterialLineIntegrator" in content),
            ("步骤3.5注释", "步骤3.5" in content),
            ("板料线添加逻辑", "add_material_lines_to_subgraph" in content),
            ("material_line_time变量", "material_line_time" in content),
            ("ENABLE_MATERIAL_LINES检查", "ENABLE_MATERIAL_LINES" in content)
        ]
        
        for desc, result in checks:
            status = "✅" if result else "❌"
            print(f"{status} {desc}")
            all_checks.append(result)
            
    except Exception as e:
        print(f"❌ 读取main.py失败: {e}")
        all_checks.append(False)
    
    # 4. 检查模块导入
    print("\n【4】检查模块导入")
    print("-" * 80)
    
    # 直接检查文件语法，不导入（避免触发main.py的执行）
    try:
        import py_compile
        py_compile.compile("cad_chaitu/material_line_integrator.py", doraise=True)
        print("✅ 板料线集成器模块: 语法检查通过")
        all_checks.append(True)
    except Exception as e:
        print(f"❌ 板料线集成器模块: 语法错误 - {e}")
        all_checks.append(False)

    # 5. 检查环境变量
    print("\n【5】检查环境变量")
    print("-" * 80)

    # 使用统一的配置加载模块
    try:
        from scripts.config_loader import load_config
        load_config()
        print("✅ 已加载配置文件（主配置 + scripts 专用配置）")
    except ImportError:
        print("⚠️ config_loader 模块未找到，跳过配置加载")
    except Exception as e:
        print(f"⚠️ 加载配置失败: {e}")

    check_env_variable("ENABLE_MATERIAL_LINES", "板料线功能开关")
    check_env_variable("DB_HOST", "数据库主机")
    check_env_variable("ODA_FILE_CONVERTER_PATH", "ODA转换器路径")

    # 6. 统计结果
    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)
    
    passed = sum(all_checks)
    total = len(all_checks)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"通过: {passed}/{total} ({success_rate:.1f}%)")
    
    if passed == total:
        print("\n✅ 所有检查通过！集成成功！")
        print("\n下一步:")
        print("  1. 配置 .env 文件（参考 .env.example）")
        print("  2. 重启服务")
        print("  3. 运行测试: python test_material_line_integration.py")
        return True
    else:
        print(f"\n⚠️ 有 {total - passed} 项检查未通过")
        print("\n请检查:")
        print("  1. 文件是否完整")
        print("  2. 代码是否正确集成")
        print("  3. 依赖是否安装")
        return False


def print_quick_start():
    """打印快速开始指南"""
    print("\n" + "=" * 80)
    print("快速开始")
    print("=" * 80)
    print("""
1. 配置环境变量:
   cp .env.example .env
   # 编辑 .env 文件，填入实际配置

2. 启用板料线功能:
   # 在 .env 中确保
   ENABLE_MATERIAL_LINES=true

3. 重启服务:
   python unified_api.py

4. 测试功能:
   # 调用拆图API
   curl -X POST http://localhost:8000/api/chaitu \\
     -H "Content-Type: application/json" \\
     -d '{"job_id": "YOUR_JOB_ID"}'

5. 查看日志:
   # 搜索板料线相关日志
   grep "板料线" logs/*.log

6. 禁用功能（如需要）:
   # 在 .env 中设置
   ENABLE_MATERIAL_LINES=false
""")


if __name__ == "__main__":
    success = verify_integration()
    
    if success:
        print_quick_start()
    
    sys.exit(0 if success else 1)
