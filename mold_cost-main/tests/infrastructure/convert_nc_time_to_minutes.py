"""
将 NC 时间字段从小时转换为分钟
只修改：nc_roughing_time, nc_milling_time, drilling_time

⚠️ 重要提示：
1. 此脚本会将现有数据乘以 60（小时转分钟）
2. 如果数据已经是分钟，请勿执行此脚本！
3. 执行前请先备份数据库
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database import get_db
from sqlalchemy import text


async def convert_hours_to_minutes():
    """将小时转换为分钟"""
    print("=" * 80)
    print("NC 时间单位转换：小时 -> 分钟")
    print("=" * 80)
    
    # 确认执行
    print("\n⚠️  警告：此操作会修改数据库中的所有 NC 时间数据！")
    print("⚠️  如果数据已经是分钟，请勿执行此脚本！")
    print("\n请确认：")
    print("1. 已备份数据库")
    print("2. 当前数据单位是小时（不是分钟）")
    print("3. 理解此操作不可逆（除非从备份恢复）")
    
    confirm = input("\n是否继续？(yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ 操作已取消")
        return
    
    async for db in get_db():
        try:
            # 1. 查看转换前的数据
            print("\n" + "=" * 80)
            print("1. 转换前的数据示例")
            print("=" * 80)
            
            result = await db.execute(text("""
                SELECT 
                    subgraph_id,
                    nc_roughing_time,
                    nc_milling_time,
                    drilling_time
                FROM subgraphs
                WHERE nc_roughing_time IS NOT NULL 
                   OR nc_milling_time IS NOT NULL 
                   OR drilling_time IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 5
            """))
            
            rows = result.fetchall()
            if rows:
                print(f"{'子图ID':<50} {'开粗':<10} {'精铣':<10} {'钻孔':<10}")
                print("-" * 80)
                for row in rows:
                    print(f"{row[0]:<50} {row[1] or 0:<10.2f} {row[2] or 0:<10.2f} {row[3] or 0:<10.2f}")
            else:
                print("没有找到数据")
            
            # 2. 统计需要转换的记录数
            result = await db.execute(text("""
                SELECT COUNT(*) as total
                FROM subgraphs
                WHERE nc_roughing_time IS NOT NULL 
                   OR nc_milling_time IS NOT NULL 
                   OR drilling_time IS NOT NULL
            """))
            total_count = result.scalar()
            
            print(f"\n需要转换的记录数: {total_count}")
            
            if total_count == 0:
                print("❌ 没有需要转换的数据")
                return
            
            # 最后确认
            final_confirm = input(f"\n确认转换 {total_count} 条记录？(yes/no): ").strip().lower()
            if final_confirm != "yes":
                print("❌ 操作已取消")
                return
            
            # 3. 执行转换
            print("\n" + "=" * 80)
            print("2. 执行转换（小时 * 60 = 分钟）")
            print("=" * 80)
            
            result = await db.execute(text("""
                UPDATE subgraphs
                SET 
                    nc_roughing_time = CASE WHEN nc_roughing_time IS NOT NULL THEN nc_roughing_time * 60 ELSE NULL END,
                    nc_milling_time = CASE WHEN nc_milling_time IS NOT NULL THEN nc_milling_time * 60 ELSE NULL END,
                    drilling_time = CASE WHEN drilling_time IS NOT NULL THEN drilling_time * 60 ELSE NULL END,
                    updated_at = NOW()
                WHERE 
                    nc_roughing_time IS NOT NULL 
                    OR nc_milling_time IS NOT NULL 
                    OR drilling_time IS NOT NULL
            """))
            
            await db.commit()
            print(f"✅ 已更新 {result.rowcount} 条记录")
            
            # 4. 添加字段注释
            print("\n" + "=" * 80)
            print("3. 添加字段注释")
            print("=" * 80)
            
            await db.execute(text("COMMENT ON COLUMN subgraphs.nc_roughing_time IS '开粗时间（分钟）'"))
            await db.execute(text("COMMENT ON COLUMN subgraphs.nc_milling_time IS '精铣时间（分钟）'"))
            await db.execute(text("COMMENT ON COLUMN subgraphs.drilling_time IS '钻孔时间（分钟）'"))
            await db.commit()
            print("✅ 字段注释已添加")
            
            # 5. 验证转换结果
            print("\n" + "=" * 80)
            print("4. 转换后的数据示例")
            print("=" * 80)
            
            result = await db.execute(text("""
                SELECT 
                    subgraph_id,
                    nc_roughing_time as roughing_minutes,
                    nc_milling_time as milling_minutes,
                    drilling_time as drilling_minutes,
                    ROUND(nc_roughing_time / 60.0, 2) as roughing_hours,
                    ROUND(nc_milling_time / 60.0, 2) as milling_hours,
                    ROUND(drilling_time / 60.0, 2) as drilling_hours
                FROM subgraphs
                WHERE nc_roughing_time IS NOT NULL 
                   OR nc_milling_time IS NOT NULL 
                   OR drilling_time IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 5
            """))
            
            rows = result.fetchall()
            if rows:
                print(f"{'子图ID':<50} {'开粗(分)':<12} {'精铣(分)':<12} {'钻孔(分)':<12}")
                print("-" * 86)
                for row in rows:
                    print(f"{row[0]:<50} {row[1] or 0:<12.2f} {row[2] or 0:<12.2f} {row[3] or 0:<12.2f}")
                
                print(f"\n{'子图ID':<50} {'开粗(时)':<12} {'精铣(时)':<12} {'钻孔(时)':<12}")
                print("-" * 86)
                for row in rows:
                    print(f"{row[0]:<50} {row[4] or 0:<12.2f} {row[5] or 0:<12.2f} {row[6] or 0:<12.2f}")
            
            # 6. 统计信息
            print("\n" + "=" * 80)
            print("5. 转换统计")
            print("=" * 80)
            
            result = await db.execute(text("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN nc_roughing_time IS NOT NULL THEN 1 END) as nc_roughing_count,
                    COUNT(CASE WHEN nc_milling_time IS NOT NULL THEN 1 END) as nc_milling_count,
                    COUNT(CASE WHEN drilling_time IS NOT NULL THEN 1 END) as drilling_count,
                    ROUND(AVG(nc_roughing_time), 2) as avg_nc_roughing_minutes,
                    ROUND(AVG(nc_milling_time), 2) as avg_nc_milling_minutes,
                    ROUND(AVG(drilling_time), 2) as avg_drilling_minutes,
                    ROUND(MAX(nc_roughing_time), 2) as max_nc_roughing_minutes,
                    ROUND(MAX(nc_milling_time), 2) as max_nc_milling_minutes,
                    ROUND(MAX(drilling_time), 2) as max_drilling_minutes
                FROM subgraphs
            """))
            
            row = result.fetchone()
            print(f"总记录数: {row[0]}")
            print(f"有开粗时间的记录: {row[1]}")
            print(f"有精铣时间的记录: {row[2]}")
            print(f"有钻孔时间的记录: {row[3]}")
            print(f"\n平均开粗时间: {row[4] or 0:.2f} 分钟")
            print(f"平均精铣时间: {row[5] or 0:.2f} 分钟")
            print(f"平均钻孔时间: {row[6] or 0:.2f} 分钟")
            print(f"\n最大开粗时间: {row[7] or 0:.2f} 分钟")
            print(f"最大精铣时间: {row[8] or 0:.2f} 分钟")
            print(f"最大钻孔时间: {row[9] or 0:.2f} 分钟")
            
            # 7. 检查异常值
            print("\n" + "=" * 80)
            print("6. 异常值检查")
            print("=" * 80)
            
            result = await db.execute(text("""
                SELECT COUNT(*) as records_with_large_values
                FROM subgraphs
                WHERE 
                    nc_roughing_time > 10000
                    OR nc_milling_time > 10000
                    OR drilling_time > 10000
            """))
            
            large_count = result.scalar()
            if large_count > 0:
                print(f"⚠️  发现 {large_count} 条记录的时间超过 10000 分钟（约 166 小时）")
                print("   这可能表示数据异常或重复执行了转换")
            else:
                print("✅ 没有发现异常大的值")
            
            print("\n" + "=" * 80)
            print("✅ 转换完成！")
            print("=" * 80)
            print("\n下一步：")
            print("1. 重启 orchestrator_worker")
            print("2. 提交新任务测试")
            print("3. 运行验证脚本: python tests/infrastructure/verify_nc_data.py")
            
        except Exception as e:
            print(f"\n❌ 转换失败: {e}")
            await db.rollback()
            raise
        
        break  # 只需要第一次迭代


if __name__ == "__main__":
    asyncio.run(convert_hours_to_minutes())
