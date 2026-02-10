"""
验证 nc_time_cost 字段是否添加成功
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from shared.database import get_db

async def verify():
    """验证字段"""
    print("验证 nc_time_cost 字段...")
    
    async for db in get_db():
        try:
            # 查询字段信息
            result = await db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'features' 
                AND column_name = 'nc_time_cost'
            """))
            
            row = result.fetchone()
            
            if row:
                print(f"✓ 字段存在")
                print(f"  - 字段名: {row[0]}")
                print(f"  - 数据类型: {row[1]}")
                print(f"  - 可为空: {row[2]}")
            else:
                print("✗ 字段不存在")
            
            # 查询索引
            result = await db.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'features' 
                AND indexname = 'idx_features_nc_time_cost'
            """))
            
            row = result.fetchone()
            if row:
                print(f"✓ 索引存在: {row[0]}")
            else:
                print("✗ 索引不存在")
                
        except Exception as e:
            print(f"✗ 验证失败: {e}")
            raise
        
        break

if __name__ == "__main__":
    asyncio.run(verify())
