"""
直接使用asyncpg测试连接
"""
import asyncio
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

import asyncpg

async def test_direct_connection():
    """直接使用asyncpg测试"""
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "mold_cost_db")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "yunzai123")
    
    print("=" * 60)
    print("直接使用asyncpg测试数据库连接")
    print("=" * 60)
    print(f"连接到: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    try:
        # 直接创建连接
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        print("✅ 连接成功！")
        
        # 测试插入
        job_id = str(uuid.uuid4())
        dwg_file_id = str(uuid.uuid4())
        user_id = "a63b7863-5faf-4b00-9ec3-758495b0fb66"
        
        async with conn.transaction():
            await conn.execute("""
                INSERT INTO jobs (
                    job_id, user_id,
                    dwg_file_id, dwg_file_name, dwg_file_path,
                    status, current_stage, progress,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, job_id, user_id, dwg_file_id, "test.dwg", "test/path.dwg",
                "pending", "initializing", 0, datetime.now(), datetime.now())
            
            print(f"✅ 插入成功！Job ID: {job_id}")
        
        # 验证
        row = await conn.fetchrow("SELECT job_id, status FROM jobs WHERE job_id = $1", job_id)
        if row:
            print(f"✅ 验证成功！查询到记录: {dict(row)}")
        
        await conn.close()
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_connection())
