"""
验证 small_grinding_count 列是否存在
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_gateway.database import db


async def verify():
    """验证列是否存在"""
    sql = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'subgraphs' 
        AND column_name IN ('small_grinding_count', 'small_grinding_cost', 'small_grinding_time')
        ORDER BY column_name
    """
    
    result = await db.fetch_all(sql)
    
    print("subgraphs 表中与 small_grinding 相关的列：")
    print("-" * 60)
    for row in result:
        print(f"列名: {row['column_name']:<30} 类型: {row['data_type']:<15} 可空: {row['is_nullable']}")
    print("-" * 60)


if __name__ == "__main__":
    asyncio.run(verify())
