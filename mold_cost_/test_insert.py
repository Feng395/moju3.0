"""
测试数据库插入
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def test_insert():
    """测试插入数据"""
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "mold_cost_db")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "yunzai123")
    
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    print("=" * 60)
    print("测试数据库插入")
    print("=" * 60)
    
    try:
        # 创建引擎
        engine = create_async_engine(
            DATABASE_URL,
            echo=True,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # 创建会话工厂
        AsyncSessionLocal = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        
        # 测试插入
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # 先插入测试用户到users表
                test_user_id = "a63b7863-5faf-4b00-9ec3-758495b0fb66"
                
                # 检查用户是否已存在
                check_user_sql = text("SELECT user_id FROM users WHERE user_id = :user_id")
                result = await session.execute(check_user_sql, {"user_id": test_user_id})
                existing_user = result.fetchone()
                
                if not existing_user:
                    insert_user_sql = text("""
                        INSERT INTO users (user_id, username, email, role, created_at)
                        VALUES (:user_id, :username, :email, :role, :created_at)
                    """)
                    await session.execute(insert_user_sql, {
                        "user_id": test_user_id,
                        "username": "test_user",
                        "email": "test@example.com",
                        "role": "admin",
                        "created_at": datetime.now()
                    })
                    print(f"✅ 测试用户已创建: {test_user_id}")
                else:
                    print(f"✅ 测试用户已存在: {test_user_id}")
                
                # 插入job记录
                job_id = str(uuid.uuid4())
                dwg_file_id = str(uuid.uuid4())
                
                insert_sql = text("""
                    INSERT INTO jobs (
                        job_id, user_id,
                        dwg_file_id, dwg_file_name, dwg_file_path,
                        status, current_stage, progress,
                        created_at, updated_at
                    ) VALUES (
                        :job_id, :user_id,
                        :dwg_file_id, :dwg_file_name, :dwg_file_path,
                        :status, :current_stage, :progress,
                        :created_at, :updated_at
                    )
                """)
                
                await session.execute(insert_sql, {
                    "job_id": job_id,
                    "user_id": test_user_id,  # 使用已存在的用户ID
                    "dwg_file_id": dwg_file_id,
                    "dwg_file_name": "test.dwg",
                    "dwg_file_path": "test/path.dwg",
                    "status": "pending",
                    "current_stage": "initializing",
                    "progress": 0,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
                
                print(f"\n✅ 插入成功！Job ID: {job_id}")
        
        # 验证插入
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT job_id, user_id, status FROM jobs WHERE job_id = :job_id"),
                {"job_id": job_id}
            )
            row = result.fetchone()
            if row:
                print(f"✅ 验证成功！查询到记录: {row}")
            else:
                print(f"❌ 验证失败！未找到记录")
        
        await engine.dispose()
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_insert())
