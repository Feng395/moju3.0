"""
测试工艺代码映射功能

验证 ProcessRulesRepository 能正确将数据库中的旧格式工艺代码
映射为代码中使用的新格式
"""
import asyncio
import os
import sys

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api_gateway.repositories.process_rules_repository import (
    ProcessRulesRepository,
    PROCESS_CODE_MAPPING
)


async def test_process_code_mapping():
    """测试工艺代码映射"""
    
    print("=" * 60)
    print("🧪 测试工艺代码映射功能")
    print("=" * 60)
    print()
    
    # 1. 显示映射表
    print("📋 工艺代码映射表:")
    print("-" * 60)
    for db_code, app_code in PROCESS_CODE_MAPPING.items():
        if db_code != app_code:
            print(f"  {db_code:20} -> {app_code}")
    print()
    
    # 2. 测试数据库查询
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://root:yunzai123@192.168.0.30:5432/mold_cost_db"
    )
    
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        repo = ProcessRulesRepository()
        
        # 测试场景1: 查询"快丝割一刀"
        print("=" * 60)
        print("测试场景1: 查询'快丝割一刀'")
        print("=" * 60)
        print()
        
        rule = await repo.find_wire_process_by_description(
            session,
            "快丝割一刀"
        )
        
        if rule:
            print("✅ 查询成功:")
            print(f"  规则ID: {rule['id']}")
            print(f"  名称: {rule['name']}")
            print(f"  描述: {rule['description']}")
            print(f"  数据库原始代码: {rule['conditions']}")
            print(f"  映射后代码: {rule['process_code']}")
            print()
            
            # 验证映射
            if rule['conditions'] == 'fast_cut' and rule['process_code'] == 'fast_and_one':
                print("✅ 映射正确: fast_cut -> fast_and_one")
            elif rule['conditions'] == rule['process_code']:
                print("ℹ️  数据库已使用新格式，无需映射")
            else:
                print(f"⚠️  映射异常: {rule['conditions']} -> {rule['process_code']}")
        else:
            print("⚠️  未找到匹配的工艺规则")
        
        print()
        
        # 测试场景2: 获取所有工艺规则
        print("=" * 60)
        print("测试场景2: 获取所有线切割工艺规则")
        print("=" * 60)
        print()
        
        rules = await repo.get_all_wire_processes(session)
        
        if rules:
            print(f"✅ 找到 {len(rules)} 条工艺规则\n")
            
            for i, rule in enumerate(rules, 1):
                print(f"{i}. {rule['name']}")
                print(f"   数据库代码: {rule['conditions']}")
                print(f"   映射后代码: {rule['process_code']}")
                
                if rule['conditions'] != rule['process_code']:
                    print(f"   🔄 已映射")
                print()
        else:
            print("⚠️  未找到任何工艺规则")
    
    await engine.dispose()
    
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


async def test_mapping_logic():
    """测试映射逻辑（不需要数据库）"""
    
    print("\n" + "=" * 60)
    print("🧪 测试映射逻辑（单元测试）")
    print("=" * 60)
    print()
    
    # 根据实际数据库数据的测试用例
    test_cases = [
        # 数据库实际格式 -> 代码期望格式
        ("fast_cut", "fast_and_one"),           # 快丝割一刀
        ("slow_cut", "slow_and_one"),           # 慢丝割一刀
        ("middle_and_one", "mid_and_one"),      # 中丝割一修一
        ("slow_and_one", "slow_and_one"),       # 慢丝割一修一（已是新格式）
        ("fast_and_one", "fast_and_one"),       # 快丝割一刀（已是新格式）
        ("mid_and_one", "mid_and_one"),         # 中丝割一修一（已是新格式）
        ("unknown_code", "unknown_code"),       # 未知代码保持不变
    ]
    
    print("测试用例:")
    print("-" * 60)
    
    all_passed = True
    for db_code, expected in test_cases:
        result = PROCESS_CODE_MAPPING.get(db_code, db_code)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"{status} {db_code:20} -> {result:20} (期望: {expected})")
    
    print()
    if all_passed:
        print("✅ 所有测试用例通过")
    else:
        print("❌ 部分测试用例失败")
    print()


if __name__ == "__main__":
    # 先测试映射逻辑
    asyncio.run(test_mapping_logic())
    
    # 再测试数据库查询
    asyncio.run(test_process_code_mapping())
