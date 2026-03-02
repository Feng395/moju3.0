"""
批量更新日志配置脚本

功能：
1. 扫描所有使用 logging.basicConfig 的文件
2. 替换为统一的日志初始化方式
3. 生成更新报告

使用方法：
    python scripts/update_logging.py
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


# 需要更新的文件模式
PATTERNS_TO_REPLACE = [
    # 模式1：logging.basicConfig(...)
    (
        r'logging\.basicConfig\([^)]*\)',
        '# 日志已统一配置，无需重复初始化'
    ),
    # 模式2：logger = logging.getLogger(__name__)
    (
        r'logger = logging\.getLogger\(__name__\)',
        'logger = get_logger(__name__)'
    ),
]

# 需要添加的导入语句
IMPORT_STATEMENT = "from shared.unified_logging import get_logger"


def should_skip_file(file_path: Path) -> bool:
    """判断是否应该跳过该文件"""
    skip_patterns = [
        'unified_logging.py',
        'logging_config.py',
        'update_logging.py',
        '__pycache__',
        '.git',
        'venv',
        'node_modules',
    ]
    
    return any(pattern in str(file_path) for pattern in skip_patterns)


def find_python_files(root_dir: str) -> List[Path]:
    """查找所有Python文件"""
    python_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # 跳过特定目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                if not should_skip_file(file_path):
                    python_files.append(file_path)
    
    return python_files


def check_file_needs_update(file_path: Path) -> Tuple[bool, List[str]]:
    """检查文件是否需要更新"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # 检查是否使用了 logging.basicConfig
        if 'logging.basicConfig' in content:
            issues.append('使用了 logging.basicConfig')
        
        # 检查是否使用了 logging.getLogger(__name__)
        if 'logging.getLogger(__name__)' in content and 'from shared.unified_logging' not in content:
            issues.append('使用了 logging.getLogger 但未导入统一日志模块')
        
        return len(issues) > 0, issues
    
    except Exception as e:
        print(f"❌ 读取文件失败: {file_path}, 错误: {e}")
        return False, []


def update_file(file_path: Path, dry_run: bool = False) -> bool:
    """更新单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated = False
        
        # 1. 检查是否需要添加导入语句
        if 'logging.getLogger' in content and 'from shared.unified_logging' not in content:
            # 找到第一个 import 语句的位置
            import_match = re.search(r'^import |^from ', content, re.MULTILINE)
            if import_match:
                # 在第一个 import 之前添加
                insert_pos = import_match.start()
                content = content[:insert_pos] + IMPORT_STATEMENT + '\n' + content[insert_pos:]
                updated = True
        
        # 2. 替换 logging.basicConfig
        if 'logging.basicConfig' in content:
            # 注释掉 logging.basicConfig
            content = re.sub(
                r'logging\.basicConfig\([^)]*\)',
                '# 日志已统一配置，无需重复初始化\n# logging.basicConfig(...)',
                content
            )
            updated = True
        
        # 3. 替换 logging.getLogger(__name__)
        if 'logging.getLogger(__name__)' in content and 'from shared.unified_logging' in content:
            content = re.sub(
                r'logging\.getLogger\(__name__\)',
                'get_logger(__name__)',
                content
            )
            updated = True
        
        # 如果有更新且不是演练模式，写入文件
        if updated and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return updated
    
    except Exception as e:
        print(f"❌ 更新文件失败: {file_path}, 错误: {e}")
        return False


def generate_report(files_to_update: List[Tuple[Path, List[str]]]):
    """生成更新报告"""
    print("\n" + "=" * 80)
    print("日志配置更新报告")
    print("=" * 80)
    
    if not files_to_update:
        print("\n✅ 所有文件的日志配置都已是最新的！")
        return
    
    print(f"\n📊 需要更新的文件数量: {len(files_to_update)}")
    print("\n详细列表：")
    print("-" * 80)
    
    for i, (file_path, issues) in enumerate(files_to_update, 1):
        print(f"\n{i}. {file_path}")
        for issue in issues:
            print(f"   - {issue}")
    
    print("\n" + "=" * 80)


def main():
    """主函数"""
    print("🔍 扫描项目中的日志配置...")
    
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # 查找所有Python文件
    python_files = find_python_files(project_root)
    print(f"✅ 找到 {len(python_files)} 个Python文件")
    
    # 检查哪些文件需要更新
    files_to_update = []
    for file_path in python_files:
        needs_update, issues = check_file_needs_update(file_path)
        if needs_update:
            files_to_update.append((file_path, issues))
    
    # 生成报告
    generate_report(files_to_update)
    
    if not files_to_update:
        return
    
    # 询问是否执行更新
    print("\n" + "=" * 80)
    response = input("\n是否执行更新？(y/n): ").strip().lower()
    
    if response != 'y':
        print("❌ 取消更新")
        return
    
    # 执行更新
    print("\n🔄 开始更新文件...")
    updated_count = 0
    
    for file_path, _ in files_to_update:
        if update_file(file_path, dry_run=False):
            print(f"✅ 已更新: {file_path}")
            updated_count += 1
        else:
            print(f"⚠️  跳过: {file_path}")
    
    print(f"\n✅ 更新完成！共更新 {updated_count} 个文件")
    print("\n" + "=" * 80)
    print("📝 后续步骤：")
    print("1. 在应用启动时调用 init_logging() 初始化日志系统")
    print("2. 测试日志输出是否正常")
    print("3. 检查日志文件: logs/app.log 和 logs/error.log")
    print("=" * 80)


if __name__ == "__main__":
    main()
