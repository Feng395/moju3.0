"""
日志系统迁移脚本

功能：
1. 扫描所有 Python 文件
2. 检查日志使用情况
3. 生成迁移报告

使用方法：
    cd moldCost
    python scripts/migrate_logging.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import os
import re
from typing import List, Dict


def scan_python_files(root_dir: str = ".") -> List[Path]:
    """扫描所有 Python 文件"""
    python_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # 跳过特定目录
        if any(skip in root for skip in [".git", "__pycache__", ".pytest_cache", "venv"]):
            continue
        
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    
    return python_files


def analyze_file(file_path: Path) -> Dict:
    """分析单个文件的日志使用情况"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    result = {
        "file": str(file_path),
        "has_logging_import": False,
        "has_basicConfig": False,
        "has_getLogger": False,
        "logger_count": 0,
        "needs_migration": False
    }
    
    # 检查 import logging
    if re.search(r"import logging", content):
        result["has_logging_import"] = True
    
    # 检查 basicConfig
    if re.search(r"logging\.basicConfig", content):
        result["has_basicConfig"] = True
        result["needs_migration"] = True
    
    # 检查 getLogger
    if re.search(r"logging\.getLogger", content):
        result["has_getLogger"] = True
    
    # 统计 logger 使用次数
    result["logger_count"] = len(re.findall(r"logger\.(debug|info|warning|error|critical)", content))
    
    return result


def generate_report(results: List[Dict]):
    """生成迁移报告"""
    print("\n" + "=" * 80)
    print("日志系统迁移报告")
    print("=" * 80)
    
    # 统计
    total_files = len(results)
    files_with_logging = sum(1 for r in results if r["has_logging_import"])
    files_need_migration = sum(1 for r in results if r["needs_migration"])
    total_logger_calls = sum(r["logger_count"] for r in results)
    
    print(f"\n📊 统计信息:")
    print(f"  - 总文件数: {total_files}")
    print(f"  - 使用日志的文件: {files_with_logging}")
    print(f"  - 需要迁移的文件: {files_need_migration}")
    print(f"  - 日志调用总数: {total_logger_calls}")
    
    # 需要迁移的文件
    if files_need_migration > 0:
        print(f"\n⚠️  需要迁移的文件 ({files_need_migration}):")
        for r in results:
            if r["needs_migration"]:
                print(f"  - {r['file']}")
    
    # 迁移建议
    print("\n📝 迁移步骤:")
    print("  1. 在 main.py 中初始化日志系统:")
    print("     from shared.logging_config import setup_logging")
    print("     setup_logging(level='INFO')")
    print()
    print("  2. 在各模块中替换 logger 获取方式:")
    print("     # 旧代码")
    print("     import logging")
    print("     logger = logging.getLogger(__name__)")
    print()
    print("     # 新代码")
    print("     from shared.logging_config import get_logger")
    print("     logger = get_logger(__name__)")
    print()
    print("  3. 删除 logging.basicConfig() 调用")
    print()
    print("  4. 添加日志上下文（可选）:")
    print("     from shared.logging_config import LogContext")
    print("     with LogContext(trace_id=request_id):")
    print("         logger.info('处理请求')")
    
    print("\n" + "=" * 80)
    print("详细文档: docs/LOGGING_GUIDE.md")
    print("=" * 80)


def main():
    """主函数"""
    print("🔍 扫描 Python 文件...")
    
    # 扫描文件
    files = scan_python_files()
    print(f"✅ 找到 {len(files)} 个 Python 文件")
    
    # 分析文件
    print("🔍 分析日志使用情况...")
    results = []
    for file in files:
        try:
            result = analyze_file(file)
            results.append(result)
        except Exception as e:
            print(f"⚠️  分析失败: {file} - {e}")
    
    # 生成报告
    generate_report(results)


if __name__ == "__main__":
    main()
