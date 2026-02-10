"""
验证 3 表迁移 - 检查代码修改是否正确

验证内容：
1. 检查修改的文件是否存在
2. 验证关键代码片段
3. 检查是否还有遗留的 process_snapshots 引用
"""
import os
import re
from pathlib import Path

# 颜色输出
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def check_file_exists(filepath):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print_success(f"文件存在: {filepath}")
        return True
    else:
        print_error(f"文件不存在: {filepath}")
        return False

def check_code_pattern(filepath, pattern, should_exist=True, description=""):
    """检查代码模式"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        if should_exist:
            if matches:
                print_success(f"{description}: 找到 {len(matches)} 处")
                return True
            else:
                print_error(f"{description}: 未找到")
                return False
        else:
            if matches:
                print_warning(f"{description}: 仍然存在 {len(matches)} 处")
                for i, match in enumerate(matches[:3], 1):  # 只显示前3个
                    print(f"   {i}. {match[:100]}...")
                return False
            else:
                print_success(f"{description}: 已移除")
                return True
    except Exception as e:
        print_error(f"检查失败: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("🔍 验证 3 表迁移修改")
    print("="*60 + "\n")
    
    base_path = Path(__file__).parent.parent
    results = []
    
    # ========== 1. 检查文件存在性 ==========
    print("\n📁 1. 检查修改的文件")
    print("-" * 60)
    
    files_to_check = [
        "api_gateway/services/job_service.py",
        "api_gateway/repositories/review_repository.py",
        "agents/data_view_builder.py",
        "agents/interaction_agent.py",
        "api_gateway/routers/review_router.py"
    ]
    
    for file in files_to_check:
        filepath = base_path / file
        results.append(check_file_exists(filepath))
    
    # ========== 2. 验证 job_service.py ==========
    print("\n🔧 2. 验证 job_service.py")
    print("-" * 60)
    
    filepath = base_path / "api_gateway/services/job_service.py"
    
    # 应该移除 create_process_snapshots
    results.append(check_code_pattern(
        filepath,
        r'create_process_snapshots',
        should_exist=False,
        description="create_process_snapshots 调用"
    ))
    
    # 应该只有 create_price_snapshots
    results.append(check_code_pattern(
        filepath,
        r'create_price_snapshots',
        should_exist=True,
        description="create_price_snapshots 调用"
    ))
    
    # ========== 3. 验证 review_repository.py ==========
    print("\n🔧 3. 验证 review_repository.py")
    print("-" * 60)
    
    filepath = base_path / "api_gateway/repositories/review_repository.py"
    
    # 检查 get_all_review_data 返回 3 个表
    results.append(check_code_pattern(
        filepath,
        r'"features".*"price_snapshots".*"subgraphs"',
        should_exist=True,
        description="get_all_review_data 返回 3 个表"
    ))
    
    # 不应该有未注释的 get_process_snapshots 调用
    # 注意：注释掉的代码是可以接受的
    content = filepath.read_text(encoding='utf-8')
    has_active_call = False
    for line in content.split('\n'):
        if 'get_process_snapshots' in line and not line.strip().startswith('#'):
            has_active_call = True
            print(f"⚠️  发现未注释的 get_process_snapshots: {line.strip()}")
    
    if has_active_call:
        results.append(False)
        print(f"❌ get_process_snapshots 调用: 仍然存在活跃调用")
    else:
        results.append(True)
        print(f"✅ get_process_snapshots 调用: 已移除或已注释")

    
    # ========== 4. 验证 data_view_builder.py ==========
    print("\n🔧 4. 验证 data_view_builder.py")
    print("-" * 60)
    
    filepath = base_path / "agents/data_view_builder.py"
    
    # 应该使用 wire_process
    results.append(check_code_pattern(
        filepath,
        r'wire_process',
        should_exist=True,
        description="使用 wire_process 字段"
    ))
    
    # 不应该有 _find_process_snapshot
    results.append(check_code_pattern(
        filepath,
        r'def _find_process_snapshot',
        should_exist=False,
        description="_find_process_snapshot 方法"
    ))
    
    # 不应该有 process_snapshot_id
    results.append(check_code_pattern(
        filepath,
        r'process_snapshot_id',
        should_exist=False,
        description="process_snapshot_id 引用"
    ))
    
    # ========== 5. 验证 interaction_agent.py ==========
    print("\n🔧 5. 验证 interaction_agent.py")
    print("-" * 60)
    
    filepath = base_path / "agents/interaction_agent.py"
    
    # 日志应该只显示 3 个表
    results.append(check_code_pattern(
        filepath,
        r'features.*?subgraphs.*?price_snapshots',
        should_exist=True,
        description="日志显示 3 个表"
    ))
    
    # 不应该有 process_snapshots_count
    results.append(check_code_pattern(
        filepath,
        r'process_snapshots_count',
        should_exist=False,
        description="process_snapshots_count 引用"
    ))
    
    # ========== 6. 验证 review_router.py ==========
    print("\n🔧 6. 验证 review_router.py")
    print("-" * 60)
    
    filepath = base_path / "api_gateway/routers/review_router.py"
    
    # 文档注释应该说 3 个表
    results.append(check_code_pattern(
        filepath,
        r'查询 3 个表',
        should_exist=True,
        description="文档注释提到 3 个表"
    ))
    
    # ========== 7. 全局检查 ==========
    print("\n🔍 7. 全局检查遗留引用")
    print("-" * 60)
    
    # 检查所有修改的文件中是否还有未注释的 process_snapshots 引用
    for file in files_to_check:
        filepath = base_path / file
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 查找未注释的 process_snapshots 引用
            active_refs = []
            for i, line in enumerate(lines, 1):
                # 跳过注释行
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                    
                # 检查是否包含 process_snapshots
                if 'process_snapshots' in line:
                    active_refs.append((i, line.strip()))
            
            if active_refs:
                print_warning(f"{file}: 发现 {len(active_refs)} 处未注释的 process_snapshots 引用")
                for line_num, line_content in active_refs[:3]:  # 只显示前3个
                    print(f"  行 {line_num}: {line_content[:80]}")
                results.append(False)
            else:
                print_success(f"{file}: 无未注释的 process_snapshots 引用")
                results.append(True)
    
    # ========== 8. 总结 ==========
    print("\n" + "="*60)
    print("📊 验证结果总结")
    print("="*60)
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"\n总计: {total} 项检查")
    print(f"{GREEN}通过: {passed}{RESET}")
    print(f"{RED}失败: {failed}{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}🎉 所有检查通过！迁移成功！{RESET}")
        return 0
    else:
        print(f"\n{RED}⚠️  有 {failed} 项检查失败，请检查上述错误{RESET}")
        return 1

if __name__ == "__main__":
    exit(main())
