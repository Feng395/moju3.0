"""
检查 jobs.total_cost 和 subgraphs.total_cost 的一致性
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_gateway.database import db


async def check_job_total_cost(job_id: str):
    """检查指定 job 的总价是否正确"""
    
    # 1. 查询 jobs 表的 total_cost
    job_query = """
        SELECT job_id, total_cost, status, current_stage
        FROM jobs
        WHERE job_id = $1::uuid
    """
    
    job_result = await db.fetch_one(job_query, job_id)
    
    if not job_result:
        print(f"❌ 任务不存在: {job_id}")
        return
    
    print(f"\n📋 任务信息:")
    print(f"  Job ID: {job_result['job_id']}")
    print(f"  状态: {job_result['status']}")
    print(f"  当前阶段: {job_result['current_stage']}")
    print(f"  Jobs表总价: {job_result['total_cost']}")
    
    # 2. 查询所有子图的 total_cost 并求和
    subgraph_query = """
        SELECT 
            subgraph_id,
            part_code,
            total_cost,
            material_cost,
            heat_treatment_cost,
            processing_cost_total
        FROM subgraphs
        WHERE job_id = $1::uuid
        ORDER BY subgraph_id
    """
    
    subgraph_results = await db.fetch_all(subgraph_query, job_id)
    
    print(f"\n📦 子图价格明细 (共 {len(subgraph_results)} 个):")
    print("-" * 100)
    
    calculated_total = 0.0
    for row in subgraph_results:
        total_cost = float(row['total_cost']) if row['total_cost'] else 0.0
        material_cost = float(row['material_cost']) if row['material_cost'] else 0.0
        heat_cost = float(row['heat_treatment_cost']) if row['heat_treatment_cost'] else 0.0
        processing_cost = float(row['processing_cost_total']) if row['processing_cost_total'] else 0.0
        
        calculated_total += total_cost
        
        print(f"  {row['subgraph_id']:<15} {row['part_code']:<20} "
              f"总价: {total_cost:>10.2f} = 材料: {material_cost:>8.2f} + "
              f"热处理: {heat_cost:>8.2f} + 加工: {processing_cost:>8.2f}")
    
    print("-" * 100)
    print(f"  {'计算总价:':<37} {calculated_total:>10.2f}")
    print(f"  {'Jobs表总价:':<37} {float(job_result['total_cost']) if job_result['total_cost'] else 0.0:>10.2f}")
    
    # 3. 比较差异
    jobs_total = float(job_result['total_cost']) if job_result['total_cost'] else 0.0
    diff = abs(calculated_total - jobs_total)
    
    print(f"\n{'='*100}")
    if diff < 0.01:
        print(f"✅ 价格一致！差异: {diff:.4f}")
    else:
        print(f"❌ 价格不一致！差异: {diff:.2f}")
        print(f"   需要更新 jobs.total_cost 从 {jobs_total:.2f} 到 {calculated_total:.2f}")
        
        # 询问是否修复
        fix = input("\n是否修复此问题？(y/n): ")
        if fix.lower() == 'y':
            await fix_job_total_cost(job_id, calculated_total)


async def fix_job_total_cost(job_id: str, correct_total: float):
    """修复 jobs.total_cost"""
    update_sql = """
        UPDATE jobs
        SET 
            total_cost = $2,
            updated_at = NOW()
        WHERE job_id = $1::uuid
    """
    
    try:
        await db.execute(update_sql, job_id, correct_total)
        print(f"✅ 已修复 jobs.total_cost = {correct_total:.2f}")
    except Exception as e:
        print(f"❌ 修复失败: {e}")


async def list_recent_jobs():
    """列出最近的任务"""
    query = """
        SELECT job_id, status, total_cost, created_at
        FROM jobs
        ORDER BY created_at DESC
        LIMIT 10
    """
    
    results = await db.fetch_all(query)
    
    print("\n📋 最近的任务:")
    print("-" * 80)
    for row in results:
        print(f"  {row['job_id']} | {row['status']:<20} | "
              f"总价: {float(row['total_cost']) if row['total_cost'] else 0.0:>10.2f} | "
              f"{row['created_at']}")
    print("-" * 80)


async def main():
    """主函数"""
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
        await check_job_total_cost(job_id)
    else:
        await list_recent_jobs()
        print("\n使用方法: python check_job_total_cost.py <job_id>")


if __name__ == "__main__":
    asyncio.run(main())
