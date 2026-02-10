"""
验证数据库修改
负责人：人员B2

功能：
查询数据库，验证审核流程是否真的修改了数据

使用方法：
    python scripts/verify_database_changes.py --job-id YOUR_JOB_ID
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "mold_cost_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


async def check_database_data(job_id: str):
    """检查数据库中的数据"""
    conn = None
    try:
        print("=" * 60)
        print("验证数据库修改")
        print("=" * 60)
        print(f"Job ID: {job_id}")
        print(f"数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 连接数据库
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        print("\n✅ 数据库连接成功")
        
        # 查询 features 表
        print("\n" + "=" * 60)
        print("📊 Features 表")
        print("=" * 60)
        
        features = await conn.fetch(
            "SELECT feature_id, subgraph_id, material, length_mm, width_mm, thickness_mm FROM features WHERE job_id = $1",
            job_id
        )
        
        if features:
            print(f"找到 {len(features)} 条记录:\n")
            for f in features:
                print(f"  Feature ID: {f['feature_id']}")
                print(f"  Subgraph ID: {f['subgraph_id']}")
                print(f"  材质: {f['material']}")
                print(f"  尺寸: {f['length_mm']} x {f['width_mm']} x {f['thickness_mm']}")
                print()
        else:
            print("❌ 未找到记录")
        
        # 查询 subgraphs 表
        print("=" * 60)
        print("📊 Subgraphs 表")
        print("=" * 60)
        
        subgraphs = await conn.fetch(
            "SELECT subgraph_id, part_name, weight_kg, total_cost, process_description FROM subgraphs WHERE job_id = $1",
            job_id
        )
        
        if subgraphs:
            print(f"找到 {len(subgraphs)} 条记录:\n")
            for s in subgraphs:
                print(f"  Subgraph ID: {s['subgraph_id']}")
                print(f"  零件名称: {s['part_name']}")
                print(f"  重量: {s['weight_kg']} kg")
                print(f"  总成本: {s['total_cost']}")
                print(f"  工艺说明: {s['process_description']}")
                print()
        else:
            print("❌ 未找到记录")
        
        # 查询 price_snapshots 表
        print("=" * 60)
        print("📊 Price Snapshots 表")
        print("=" * 60)
        
        price_snapshots = await conn.fetch(
            "SELECT snapshot_id, category, price, unit FROM job_price_snapshots WHERE job_id = $1 LIMIT 5",
            job_id
        )
        
        if price_snapshots:
            print(f"找到 {len(price_snapshots)} 条记录（显示前5条）:\n")
            for p in price_snapshots:
                print(f"  Snapshot ID: {p['snapshot_id']}")
                print(f"  类别: {p['category']}")
                print(f"  价格: {p['price']}")
                print(f"  单位: {p['unit']}")
                print()
        else:
            print("❌ 未找到记录")
        
        # 查询 process_snapshots 表
        print("=" * 60)
        print("📊 Process Snapshots 表")
        print("=" * 60)
        
        process_snapshots = await conn.fetch(
            "SELECT snapshot_id, name, description FROM job_process_snapshots WHERE job_id = $1 LIMIT 5",
            job_id
        )
        
        if process_snapshots:
            print(f"找到 {len(process_snapshots)} 条记录（显示前5条）:\n")
            for p in process_snapshots:
                print(f"  Snapshot ID: {p['snapshot_id']}")
                print(f"  名称: {p['name']}")
                print(f"  描述: {p['description']}")
                print()
        else:
            print("❌ 未找到记录")
        
        print("=" * 60)
        print("✅ 查询完成")
        print("=" * 60)
        
        print("\n💡 说明:")
        print("  1. 如果看到数据被修改，说明 confirm 接口成功更新了数据库")
        print("  2. 如果数据未变化，可能是:")
        print("     - 还没有调用 confirm 接口（修改还在 Redis 中）")
        print("     - 修改的字段不在查询列表中")
        print("     - 数据库事务回滚了")
    
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if conn:
            await conn.close()
            print("\n✅ 数据库连接已关闭")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="验证数据库修改")
    parser.add_argument(
        "--job-id",
        type=str,
        required=True,
        help="任务 ID（UUID 格式）"
    )
    
    args = parser.parse_args()
    
    await check_database_data(args.job_id)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 已取消")
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
