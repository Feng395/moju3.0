"""
快速诊断脚本
检查系统是否正常工作
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api_gateway.database import db


async def quick_diagnosis():
    """快速诊断"""
    
    print(f"\n{'='*80}")
    print("系统快速诊断")
    print(f"{'='*80}\n")
    
    try:
        # 1. 检查数据库连接
        print("[1] 检查数据库连接...")
        try:
            result = await db.fetch_one("SELECT 1 as test")
            print("✅ 数据库连接正常")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return
        print()
        
        # 2. 检查 price_items 表
        print("[2] 检查 price_items 表...")
        # 先检查表结构
        columns_sql = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'price_items'
            ORDER BY ordinal_position
        """
        columns = await db.fetch_all(columns_sql)
        
        if columns:
            print(f"   表结构:")
            for col in columns:
                print(f"   - {col['column_name']}: {col['data_type']}")
            print()
            
            # 检查数据
            price_items_sql = "SELECT COUNT(*) as total_count FROM price_items"
            price_items = await db.fetch_one(price_items_sql)
            
            if price_items['total_count'] > 0:
                print(f"✅ price_items 表有 {price_items['total_count']} 条数据")
            else:
                print("❌ price_items 表没有数据")
                print("   这会导致价格计算失败")
                print("   建议: 导入价格数据")
        else:
            print("❌ price_items 表不存在")
            print("   建议: 运行 init-db.sql 初始化数据库")
        print()
        
        # 3. 检查最近的任务
        print("[3] 检查最近的任务...")
        jobs_sql = """
            SELECT 
                job_id,
                dwg_file_name,
                status,
                total_cost,
                created_at
            FROM jobs
            ORDER BY created_at DESC
            LIMIT 5
        """
        jobs = await db.fetch_all(jobs_sql)
        
        if jobs:
            print(f"✅ 找到 {len(jobs)} 个最近的任务:")
            for job in jobs:
                print(f"\n   任务: {job['job_id']}")
                print(f"   文件: {job['dwg_file_name']}")
                print(f"   状态: {job['status']}")
                print(f"   总成本: {job['total_cost']}")
                print(f"   创建时间: {job['created_at']}")
        else:
            print("⚠️  没有找到任务")
        print()
        
        # 4. 检查子图数据
        print("[4] 检查子图数据...")
        if jobs:
            latest_job_id = jobs[0]['job_id']
            subgraphs_sql = """
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN total_cost > 0 THEN 1 END) as with_cost,
                    COUNT(CASE WHEN total_cost = 0 OR total_cost IS NULL THEN 1 END) as without_cost,
                    SUM(total_cost) as sum_cost
                FROM subgraphs
                WHERE job_id = $1::uuid
            """
            subgraphs = await db.fetch_one(subgraphs_sql, latest_job_id)
            
            print(f"   最新任务 ({latest_job_id}) 的子图:")
            print(f"   总数: {subgraphs['total_count']}")
            print(f"   有成本: {subgraphs['with_cost']}")
            print(f"   无成本: {subgraphs['without_cost']}")
            print(f"   成本汇总: {subgraphs['sum_cost']}")
            
            if subgraphs['without_cost'] > 0:
                print(f"\n   ⚠️  有 {subgraphs['without_cost']} 个子图没有成本数据")
        print()
        
        # 5. 检查计算明细
        print("[5] 检查计算明细...")
        if jobs:
            details_sql = """
                SELECT COUNT(*) as count
                FROM processing_cost_calculation_details
                WHERE job_id = $1::uuid
            """
            details = await db.fetch_one(details_sql, latest_job_id)
            
            if details['count'] > 0:
                print(f"✅ 找到 {details['count']} 条计算明细")
            else:
                print("❌ 没有找到计算明细")
                print("   这表明价格计算可能没有执行")
        print()
        
        # 总结
        print(f"{'='*80}")
        print("[诊断总结]")
        print(f"{'='*80}")
        
        if not columns:
            print("❌ price_items 表不存在，需要初始化数据库")
        elif price_items['total_count'] == 0:
            print("❌ 缺少价格数据，需要导入 price_items")
        elif jobs and subgraphs['without_cost'] > 0:
            print("⚠️  有子图没有成本数据，可能需要重新计算价格")
            print(f"\n   使用以下命令检查详情:")
            print(f"   python tests/infrastructure/check_pricing_data.py {latest_job_id}")
        elif not jobs:
            print("⚠️  系统中没有任务数据")
        else:
            print("✅ 系统看起来正常")
    
    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(quick_diagnosis())
