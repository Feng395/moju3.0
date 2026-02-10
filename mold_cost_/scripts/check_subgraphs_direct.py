"""
直接检查 subgraphs 表结构
负责人：人员B2

功能：
使用 asyncpg 直接连接数据库检查 subgraphs 表结构

使用方法：
    python scripts/check_subgraphs_direct.py
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "mold_cost_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


async def check_table_structure():
    """检查表结构"""
    conn = None
    try:
        print("=" * 60)
        print("检查 subgraphs 表结构")
        print("=" * 60)
        print(f"连接: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        
        # 连接数据库
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        print("✅ 数据库连接成功\n")
        
        # 查询表结构
        rows = await conn.fetch("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'subgraphs'
            ORDER BY ordinal_position
        """)
        
        if not rows:
            print("❌ 未找到 subgraphs 表")
            return False
        
        print(f"✅ 找到 {len(rows)} 个字段:\n")
        
        has_material = False
        for row in rows:
            col_name = row['column_name']
            data_type = row['data_type']
            max_length = row['character_maximum_length']
            nullable = row['is_nullable']
            
            length_info = f"({max_length})" if max_length else ""
            null_info = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"  {col_name:30} {data_type}{length_info:15} {null_info}")
            
            if col_name == "material":
                has_material = True
        
        print("\n" + "=" * 60)
        if has_material:
            print("✅ material 字段存在")
            print("\n💡 模型定义正确，可以继续测试")
        else:
            print("❌ material 字段不存在")
            print("\n💡 需要执行以下 SQL 添加字段:")
            print("   ALTER TABLE subgraphs ADD COLUMN material VARCHAR(50);")
            print("\n或者注释掉模型中的 material 字段")
        
        return has_material
    
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if conn:
            await conn.close()
            print("\n✅ 数据库连接已关闭")


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
