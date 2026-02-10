"""
测试数据库连接
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_connection():
    """测试数据库连接"""
    # 从环境变量读取配置
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "mold_cost_db")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "yunzai123")
    
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    print("=" * 60)
    print("测试数据库连接")
    print("=" * 60)
    print(f"数据库地址: {DB_HOST}:{DB_PORT}")
    print(f"数据库名称: {DB_NAME}")
    print(f"用户名: {DB_USER}")
    print(f"连接URL: {DATABASE_URL}")
    print("=" * 60)
    
    try:
        # 创建引擎
        engine = create_async_engine(DATABASE_URL, echo=True)
        
        # 测试连接
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"\n✅ 数据库连接成功！")
            print(f"PostgreSQL版本: {version}\n")
            
            # 测试查询jobs表
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM jobs"))
                count = result.scalar()
                print(f"✅ jobs表存在，当前记录数: {count}")
            except Exception as e:
                print(f"⚠️  jobs表不存在或无法访问: {e}")
            
            # 测试查询price_items表
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM price_items"))
                count = result.scalar()
                print(f"✅ price_items表存在，当前记录数: {count}")
            except Exception as e:
                print(f"⚠️  price_items表不存在: {e}")
            
            # 测试查询process_rules表
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM process_rules"))
                count = result.scalar()
                print(f"✅ process_rules表存在，当前记录数: {count}")
            except Exception as e:
                print(f"⚠️  process_rules表不存在: {e}")
        
        await engine.dispose()
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        print(f"\n请检查：")
        print(f"1. PostgreSQL服务是否启动")
        print(f"2. 数据库 {DB_NAME} 是否存在")
        print(f"3. 用户 {DB_USER} 是否有权限")
        print(f"4. 网络连接是否正常（{DB_HOST}:{DB_PORT}）")

if __name__ == "__main__":
    asyncio.run(test_connection())
