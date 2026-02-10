"""
检查数据库表结构的Python脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from shared.database import get_db


async def check_table_columns(table_name: str):
    """检查表的列结构"""
    print(f"\n{'='*60}")
    print(f"表: {table_name}")
    print('='*60)
    
    async with get_db() as db:
        sql = text("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """)
        
        result = await db.execute(sql, {"table_name": table_name})
        columns = result.fetchall()
        
        if not columns:
            print(f"⚠️  表 {table_name} 不存在或没有列")
            return []
        
        print(f"\n共 {len(columns)} 列:\n")
        print(f"{'列名':<30} {'类型':<20} {'可空':<10} {'默认值'}")
        print('-'*80)
        
        column_names = []
        for col in columns:
            column_name = col[0]
            data_type = col[1]
            is_nullable = col[2]
            default_value = col[3] or ''
            
            column_names.append(column_name)
            print(f"{column_name:<30} {data_type:<20} {is_nullable:<10} {default_value}")
        
        return column_names


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("数据库表结构检查工具")
    print("="*60)
    
    tables = [
        'price_items',
        'job_price_snapshots',
        'process_rules',
        'job_process_snapshots'
    ]
    
    table_columns = {}
    
    for table in tables:
        try:
            columns = await check_table_columns(table)
            table_columns[table] = columns
        except Exception as e:
            print(f"❌ 检查表 {table} 失败: {e}")
    
    # 对比分析
    print("\n" + "="*60)
    print("字段对比分析")
    print("="*60)
    
    # 检查 description 字段
    print("\n检查 'description' 字段:")
    for table, columns in table_columns.items():
        has_description = 'description' in columns
        status = "✅ 有" if has_description else "❌ 无"
        print(f"  {table:<30} {status}")
    
    # 检查源表和快照表的字段差异
    print("\n\nprice_items → job_price_snapshots 字段对比:")
    if 'price_items' in table_columns and 'job_price_snapshots' in table_columns:
        source_cols = set(table_columns['price_items'])
        snapshot_cols = set(table_columns['job_price_snapshots'])
        
        # 快照表独有的字段
        snapshot_only = snapshot_cols - source_cols
        print(f"\n快照表独有字段: {snapshot_only}")
        
        # 源表独有的字段
        source_only = source_cols - snapshot_cols
        print(f"源表独有字段: {source_only}")
        
        # 共同字段
        common = source_cols & snapshot_cols
        print(f"共同字段数量: {len(common)}")
    
    print("\n\nprocess_rules → job_process_snapshots 字段对比:")
    if 'process_rules' in table_columns and 'job_process_snapshots' in table_columns:
        source_cols = set(table_columns['process_rules'])
        snapshot_cols = set(table_columns['job_process_snapshots'])
        
        # 快照表独有的字段
        snapshot_only = snapshot_cols - source_cols
        print(f"\n快照表独有字段: {snapshot_only}")
        
        # 源表独有的字段
        source_only = source_cols - snapshot_cols
        print(f"源表独有字段: {source_only}")
        
        # 共同字段
        common = source_cols & snapshot_cols
        print(f"共同字段数量: {len(common)}")
    
    print("\n" + "="*60)
    print("检查完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
