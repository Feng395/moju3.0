"""
检查 subgraphs 表结构
负责人：人员B2

功能：
检查数据库中 subgraphs 表的实际字段，特别是 material 字段是否存在

使用方法：
    python scripts/check_subgraphs_structure.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database import get_db
from sqlalchemy import text


async def check_table_structure():
    """检查表结构"""
    try:
        print("=" * 60)
        print("检查 subgraphs 表结构")
        print("=" * 60)
        
        async for db in get_db():
            # 查询表结构
            result = await db.execute(
                text("""
                    SELECT column_name, data_type, character_maximum_length, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'subgraphs'
                    ORDER BY ordinal_position
                """)
            )
            
            columns = result.fetchall()
            
            if not columns:
                print("\n❌ 未找到 subgraphs 表")
                return False
            
            print(f"\n✅ 找到 {len(columns)} 个字段:\n")
            
            has_material = False
            for col in columns:
                col_name, data_type, max_length, nullable = col
                length_info = f"({max_length})" if max_length else ""
                null_info = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"  {col_name:30} {data_type}{length_info:15} {null_info}")
                
                if col_name == "material":
                    has_material = True
            
            print("\n" + "=" * 60)
            if has_material:
                print("✅ material 字段存在")
            else:
                print("❌ material 字段不存在")
                print("\n💡 需要执行以下 SQL 添加字段:")
                print("   ALTER TABLE subgraphs ADD COLUMN material VARCHAR(50);")
            
            return has_material
    
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    await check_table_structure()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 已取消")
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
