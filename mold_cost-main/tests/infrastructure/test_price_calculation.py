"""
测试价格计算流程
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_gateway.database import db


async def simulate_batch_calculation(job_id: str):
    """
    模拟分批计算的场景
    """
    print(f"\n{'='*80}")
    print(f"模拟分批计算场景: job_id={job_id}")
    print(f"{'='*80}\n")
    
    # 1. 查询所有子图
    query = """
        SELECT subgraph_id, part_code, total_cost
        FROM subgraphs
        WHERE job_id = $1::uuid
        ORDER BY subgraph_id
    """
    
    subgraphs = await db.fetch_all(query, job_id)
    
    if not subgraphs:
        print(f"❌ 没有找到子图")
        return
    
    print(f"📦 找到 {len(subgraphs)} 个子图:")
    for sg in subgraphs:
        print(f"  - {sg['subgraph_id']}: {sg['part_code']}, total_cost={sg['total_cost']}")
    
    # 2. 计算预期的总价
    expected_total = sum(float(sg['total_cost']) if sg['total_cost'] else 0.0 for sg in subgraphs)
    print(f"\n💰 预期总价（所有子图总和）: {expected_total:.2f}")
    
    # 3. 查询 jobs.total_cost
    job_query = """
        SELECT total_cost
        FROM jobs
        WHERE job_id = $1::uuid
    """
    
    job_result = await db.fetch_one(job_query, job_id)
    actual_total = float(job_result['total_cost']) if job_result and job_result['total_cost'] else 0.0
    
    print(f"💰 实际总价（jobs.total_cost）: {actual_total:.2f}")
    
    # 4. 比较
    diff = abs(expected_total - actual_total)
    print(f"\n{'='*80}")
    if diff < 0.01:
        print(f"✅ 价格一致！")
    else:
        print(f"❌ 价格不一致！差异: {diff:.2f}")
        print(f"   预期: {expected_total:.2f}")
        print(f"   实际: {actual_total:.2f}")
    print(f"{'='*80}\n")


async def main():
    """主函数"""
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
        await simulate_batch_calculation(job_id)
    else:
        # 列出最近的任务
        query = """
            SELECT job_id, status, total_cost, created_at
            FROM jobs
            ORDER BY created_at DESC
            LIMIT 5
        """
        
        results = await db.fetch_all(query)
        
        print("\n📋 最近的任务:")
        print("-" * 80)
        for row in results:
            print(f"  {row['job_id']} | {row['status']:<20} | "
                  f"总价: {float(row['total_cost']) if row['total_cost'] else 0.0:>10.2f}")
        print("-" * 80)
        print("\n使用方法: python test_price_calculation.py <job_id>")


if __name__ == "__main__":
    asyncio.run(main())
