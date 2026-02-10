"""
修复 process_rules 表的工艺代码

问题：
- 数据库中存储的是 fast_cut
- 代码中使用的是 fast_and_one

解决方案：
1. 检查当前的工艺代码
2. 提供映射关系
3. 可选：更新数据库
"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 工艺代码映射（数据库 -> 代码）
PROCESS_CODE_MAPPING = {
    "fast_cut": "fast_and_one",      # 快走丝割一刀
    "slow_cut": "slow_and_one",      # 慢走丝割一刀
    "mid_cut": "mid_and_one",        # 中走丝割一刀
    # 可以添加更多映射...
}


async def check_process_rules():
    """检查 process_rules 表的工艺代码"""
    
    # 数据库连接
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/mold_cost")
    engine = create_async_engine(db_url, echo=False)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    print("=" * 60)
    print("🔍 检查 process_rules 表的工艺代码")
    print("=" * 60)
    print()
    
    async with async_session() as session:
        # 1. 查询所有线切割工艺规则
        print("📋 查询所有线切割工艺规则...")
        result = await session.execute(text("""
            SELECT 
                id,
                name,
                description,
                conditions AS process_code,
                priority,
                is_active
            FROM process_rules
            WHERE feature_type = 'wire'
              AND is_active = true
            ORDER BY priority DESC
        """))
        
        rules = result.fetchall()
        
        if not rules:
            print("⚠️  未找到任何线切割工艺规则")
            return
        
        print(f"✅ 找到 {len(rules)} 条工艺规则\n")
        
        # 2. 显示当前的工艺代码
        print("当前工艺代码:")
        print("-" * 60)
        
        needs_fix = []
        for rule in rules:
            rule_id, name, description, process_code, priority, is_active = rule
            
            # 检查是否需要修复
            if process_code in PROCESS_CODE_MAPPING:
                expected_code = PROCESS_CODE_MAPPING[process_code]
                needs_fix.append((rule_id, name, process_code, expected_code))
                status = f"❌ 需要修复 -> {expected_code}"
            else:
                status = "✅ 正常"
            
            print(f"ID: {rule_id}")
            print(f"  名称: {name}")
            print(f"  描述: {description}")
            print(f"  工艺代码: {process_code}")
            print(f"  状态: {status}")
            print()
        
        # 3. 如果有需要修复的
        if needs_fix:
            print("=" * 60)
            print(f"⚠️  发现 {len(needs_fix)} 条需要修复的工艺代码")
            print("=" * 60)
            print()
            
            for rule_id, name, old_code, new_code in needs_fix:
                print(f"- {name}: {old_code} -> {new_code}")
            
            print()
            print("💡 修复方案:")
            print("   方案1: 手动执行 SQL 更新")
            print("   方案2: 运行 fix_process_rules.py --apply")
            print()
            print("SQL 示例:")
            for rule_id, name, old_code, new_code in needs_fix:
                print(f"   UPDATE process_rules SET conditions = '{new_code}' WHERE id = '{rule_id}';")
        else:
            print("✅ 所有工艺代码都正常，无需修复")
    
    await engine.dispose()


async def fix_process_rules():
    """修复 process_rules 表的工艺代码"""
    
    # 数据库连接
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/mold_cost")
    engine = create_async_engine(db_url, echo=False)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    print("=" * 60)
    print("🔧 修复 process_rules 表的工艺代码")
    print("=" * 60)
    print()
    
    async with async_session() as session:
        # 查询需要修复的规则
        result = await session.execute(text("""
            SELECT 
                id,
                name,
                conditions AS process_code
            FROM process_rules
            WHERE feature_type = 'wire'
              AND is_active = true
        """))
        
        rules = result.fetchall()
        
        fixed_count = 0
        for rule in rules:
            rule_id, name, process_code = rule
            
            if process_code in PROCESS_CODE_MAPPING:
                new_code = PROCESS_CODE_MAPPING[process_code]
                
                print(f"🔧 修复: {name}")
                print(f"   {process_code} -> {new_code}")
                
                # 执行更新
                await session.execute(text("""
                    UPDATE process_rules
                    SET conditions = :new_code
                    WHERE id = :rule_id
                """), {"new_code": new_code, "rule_id": rule_id})
                
                fixed_count += 1
        
        # 提交事务
        await session.commit()
        
        print()
        print(f"✅ 修复完成: {fixed_count} 条记录")
    
    await engine.dispose()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--apply":
        # 应用修复
        print("⚠️  警告: 即将修改数据库数据")
        confirm = input("确认继续? (yes/no): ")
        
        if confirm.lower() == "yes":
            asyncio.run(fix_process_rules())
        else:
            print("❌ 已取消")
    else:
        # 只检查，不修复
        asyncio.run(check_process_rules())
