"""
检查价格数据
用于诊断价格为 0 的问题
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api_gateway.database import db


async def check_pricing_data(job_id: str):
    """检查价格数据"""
    
    print(f"\n{'='*80}")
    print(f"检查价格数据: {job_id}")
    print(f"{'='*80}\n")
    
    try:
        # 1. 检查 jobs 表
        print("[1] 检查 jobs 表...")
        job_sql = """
            SELECT job_id, dwg_file_name, status, total_cost, created_at
            FROM jobs
            WHERE job_id = $1::uuid
        """
        job = await db.fetch_one(job_sql, job_id)
        
        if not job:
            print(f"❌ 未找到任务: {job_id}")
            return
        
        print(f"✅ 任务信息:")
        print(f"   文件名: {job['dwg_file_name']}")
        print(f"   状态: {job['status']}")
        print(f"   总成本: {job['total_cost']}")
        print(f"   创建时间: {job['created_at']}")
        print()
        
        # 2. 检查 subgraphs 表
        print("[2] 检查 subgraphs 表...")
        subgraphs_sql = """
            SELECT 
                subgraph_id,
                part_name,
                total_cost,
                material_cost,
                heat_treatment_cost,
                processing_cost_total,
                nc_roughing_cost,
                nc_milling_cost,
                drilling_cost
            FROM subgraphs
            WHERE job_id = $1::uuid
            ORDER BY subgraph_id
            LIMIT 5
        """
        subgraphs = await db.fetch_all(subgraphs_sql, job_id)
        
        print(f"✅ 找到 {len(subgraphs)} 个子图（显示前5个）:")
        for sg in subgraphs:
            print(f"\n   子图: {sg['subgraph_id']} - {sg['part_name']}")
            print(f"   总成本: {sg['total_cost']}")
            print(f"   材料成本: {sg['material_cost']}")
            print(f"   热处理成本: {sg['heat_treatment_cost']}")
            print(f"   加工成本总计: {sg['processing_cost_total']}")
            print(f"   NC开粗: {sg['nc_roughing_cost']}")
            print(f"   NC精铣: {sg['nc_milling_cost']}")
            print(f"   钻床: {sg['drilling_cost']}")
        print()
        
        # 3. 检查 features 表
        print("[3] 检查 features 表...")
        features_sql = """
            SELECT 
                subgraph_id,
                length_mm,
                width_mm,
                thickness_mm,
                material,
                quantity
            FROM features
            WHERE job_id = $1::uuid
            LIMIT 5
        """
        features = await db.fetch_all(features_sql, job_id)
        
        print(f"✅ 找到 {len(features)} 个特征（显示前5个）:")
        for f in features:
            print(f"\n   子图: {f['subgraph_id']}")
            print(f"   尺寸: {f['length_mm']} x {f['width_mm']} x {f['thickness_mm']}")
            print(f"   材料: {f['material']}")
            print(f"   数量: {f['quantity']}")
        print()
        
        # 4. 检查 processing_cost_calculation_details 表
        print("[4] 检查 processing_cost_calculation_details 表...")
        details_sql = """
            SELECT 
                subgraph_id,
                material_cost,
                heat_treatment_cost,
                nc_roughing_cost,
                nc_milling_cost,
                drilling_cost
            FROM processing_cost_calculation_details
            WHERE job_id = $1::uuid
            LIMIT 5
        """
        details = await db.fetch_all(details_sql, job_id)
        
        if details:
            print(f"✅ 找到 {len(details)} 条计算明细（显示前5个）:")
            for d in details:
                print(f"\n   子图: {d['subgraph_id']}")
                print(f"   材料成本: {d['material_cost']}")
                print(f"   热处理成本: {d['heat_treatment_cost']}")
                print(f"   NC开粗: {d['nc_roughing_cost']}")
                print(f"   NC精铣: {d['nc_milling_cost']}")
                print(f"   钻床: {d['drilling_cost']}")
        else:
            print("❌ 未找到计算明细数据")
        print()
        
        # 5. 统计汇总
        print("[5] 统计汇总...")
        summary_sql = """
            SELECT 
                COUNT(*) as total_subgraphs,
                SUM(total_cost) as sum_total_cost,
                SUM(material_cost) as sum_material_cost,
                SUM(heat_treatment_cost) as sum_heat_cost,
                SUM(processing_cost_total) as sum_processing_cost,
                COUNT(CASE WHEN total_cost > 0 THEN 1 END) as subgraphs_with_cost,
                COUNT(CASE WHEN total_cost = 0 OR total_cost IS NULL THEN 1 END) as subgraphs_without_cost
            FROM subgraphs
            WHERE job_id = $1::uuid
        """
        summary = await db.fetch_one(summary_sql, job_id)
        
        print(f"✅ 统计结果:")
        print(f"   总子图数: {summary['total_subgraphs']}")
        print(f"   总成本汇总: {summary['sum_total_cost']}")
        print(f"   材料成本汇总: {summary['sum_material_cost']}")
        print(f"   热处理成本汇总: {summary['sum_heat_cost']}")
        print(f"   加工成本汇总: {summary['sum_processing_cost']}")
        print(f"   有成本的子图: {summary['subgraphs_with_cost']}")
        print(f"   无成本的子图: {summary['subgraphs_without_cost']}")
        
        # 6. 诊断建议
        print(f"\n{'='*80}")
        print("[诊断建议]")
        print(f"{'='*80}")
        
        if summary['subgraphs_without_cost'] > 0:
            print(f"⚠️  发现 {summary['subgraphs_without_cost']} 个子图没有成本数据")
            print("   可能原因:")
            print("   1. 价格计算未执行或执行失败")
            print("   2. 特征识别数据不完整")
            print("   3. 价格表（price_items）中缺少对应的价格数据")
            print("\n   建议:")
            print("   1. 检查 Worker 日志，查看价格计算是否有错误")
            print("   2. 重新触发价格计算")
            print("   3. 检查 price_items 表是否有数据")
        
        if not details:
            print("⚠️  未找到计算明细数据")
            print("   这表明价格计算可能没有执行")
            print("\n   建议:")
            print("   1. 检查 Pricing Worker 是否正常运行")
            print("   2. 检查 MCP 服务是否正常")
            print("   3. 手动触发价格计算")
        
        if job['total_cost'] == 0 or job['total_cost'] is None:
            print("⚠️  jobs.total_cost 为 0")
            print("   建议:")
            print("   1. 运行价格计算")
            print("   2. 或手动更新: python tests/infrastructure/check_job_total_cost.py <job_id>")
    
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python check_pricing_data.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    asyncio.run(check_pricing_data(job_id))
