"""
测试 process_rules 表查询
验证工艺规则查询功能
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api_gateway.repositories.process_rules_repository import ProcessRulesRepository


async def test_process_rules_query():
    """测试工艺规则查询"""
    
    # 数据库连接
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://root:yunzai123@192.168.0.30:5432/mold_cost_db"
    )
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("=" * 60)
    print("🧪 测试 process_rules 表查询")
    print("=" * 60)
    print()
    
    async with async_session() as session:
        repo = ProcessRulesRepository()
        
        # 测试 1: 查询所有线切割工艺
        print("测试 1: 获取所有线切割工艺规则")
        print("-" * 60)
        
        try:
            rules = await repo.get_all_wire_processes(session)
            print(f"✅ 找到 {len(rules)} 条工艺规则")
            
            if rules:
                print("\n工艺规则列表:")
                for i, rule in enumerate(rules, 1):
                    print(f"\n{i}. {rule['name']}")
                    print(f"   ID: {rule['id']}")
                    print(f"   描述: {rule['description']}")
                    print(f"   工艺代码: {rule['process_code']}")
                    print(f"   优先级: {rule['priority']}")
            else:
                print("⚠️  未找到任何工艺规则")
                print("\n💡 提示: 请确保 process_rules 表中有数据")
                print("   表结构应该包含以下字段:")
                print("   - id, version_id, feature_type, name, description")
                print("   - conditions (JSONB), output_params (JSONB)")
                print("   - priority, is_active")
        
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("=" * 60)
        
        # 测试 2: 模糊匹配工艺描述
        print("测试 2: 模糊匹配工艺描述")
        print("-" * 60)
        
        test_descriptions = [
            "快丝割一刀",
            "慢丝割两刀",
            "快走丝",
            "慢走丝"
        ]
        
        for desc in test_descriptions:
            print(f"\n查询: '{desc}'")
            try:
                rule = await repo.find_wire_process_by_description(session, desc)
                
                if rule:
                    print(f"✅ 找到匹配: {rule['name']}")
                    print(f"   工艺代码: {rule['process_code']}")
                    print(f"   描述: {rule['description']}")
                else:
                    print(f"⚠️  未找到匹配")
            
            except Exception as e:
                print(f"❌ 查询失败: {e}")
        
        print()
        print("=" * 60)
        print("✅ 测试完成")
        print("=" * 60)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_process_rules_query())
