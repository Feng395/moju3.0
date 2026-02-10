"""
检查数据库表结构
对比实际数据库和 init-db.sql 的差异
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api_gateway.database import db


async def check_table_schema(table_name: str):
    """检查表结构"""
    print(f"\n{'='*80}")
    print(f"表: {table_name}")
    print(f"{'='*80}")
    
    columns_sql = """
        SELECT 
            column_name, 
            data_type,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
    """
    
    columns = await db.fetch_all(columns_sql, table_name)
    
    if columns:
        print(f"找到 {len(columns)} 个字段:\n")
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            length = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
            print(f"  {col['column_name']:<40} {col['data_type']}{length:<20} {nullable}{default}")
    else:
        print("❌ 表不存在")


async def main():
    """主函数"""
    print("\n检查数据库表结构\n")
    
    tables = [
        'jobs',
        'subgraphs',
        'features',
        'price_items',
        'process_rules',
        'processing_cost_calculation_details'
    ]
    
    for table in tables:
        await check_table_schema(table)
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
