"""
检查特定任务的成本数据
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api_gateway.database import db


async def check_job(job_name_pattern: str):
    """检查特定任务"""
    
    print(f"\n{'='*80}")
    print(f"检查任务: {job_name_pattern}")
    print(f"{'='*80}\n")
    
    # 查询任务
    query = """
        SELECT 
            job_id,
            dwg_file_name,
            status,
            progress,
            current_stage,
            total_cost,
            created_at
        FROM jobs
        WHERE dwg_file_name LIKE $1
        ORDER BY created_at DESC
        LIMIT 5
    """
    
    jobs = await db.fetch_all(query, f"%{job_name_pattern}%")
    
    if not jobs:
        print(f"❌ 没有找到匹配的任务")
        return
    
    print(f"找到 {len(jobs)} 个匹配的任务:\n")
    
    for i, job in enumerate(jobs, 1):
        job_id = job['job_id']
        print(f"[{i}] {job['dwg_file_name']}")
        print(f"    Job ID: {job_id}")
        print(f"    状态: {job['status']}")
        print(f"    进度: {job['progress']}%")
        print(f"    当前阶段: {job['current_stage']}")
        print(f"    jobs.total_cost: {float(job['total_cost']) if job['total_cost'] else 0.0:.2f}")
        
        # 查询子图数据
        subgraph_query = """
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(total_cost), 0) as total,
                COALESCE(SUM(material_cost), 0) as material,
                COALESCE(SUM(heat_treatment_cost), 0) as heat,
                COALESCE(SUM(processing_cost_total), 0) as processing
            FROM subgraphs
            WHERE job_id = $1
        """
        subgraph_result = await db.fetch_one(subgraph_query, job_id)
        
        print(f"    子图数量: {subgraph_result['count']}")
        print(f"    subgraphs 汇总: {float(subgraph_result['total']):.2f}")
        print(f"      - 材料成本: {float(subgraph_result['material']):.2f}")
        print(f"      - 热处理成本: {float(subgraph_result['heat']):.2f}")
        print(f"      - 加工成本: {float(subgraph_result['processing']):.2f}")
        
        # 查询视图数据
        view_query = """
            SELECT 
                total_cost,
                total_subgraphs
            FROM v_job_cost_summary
            WHERE job_id = $1
        """
        view_result = await db.fetch_one(view_query, job_id)
        
        if view_result:
            print(f"    视图 total_cost: {float(view_result['total_cost']) if view_result['total_cost'] else 0.0:.2f}")
        
        # 检查子图详情
        if subgraph_result['count'] > 0:
            subgraph_details_query = """
                SELECT 
                    subgraph_id,
                    part_name,
                    total_cost,
                    material_cost,
                    heat_treatment_cost,
                    processing_cost_total
                FROM subgraphs
                WHERE job_id = $1
                ORDER BY subgraph_id
                LIMIT 10
            """
            subgraph_details = await db.fetch_all(subgraph_details_query, job_id)
            
            print(f"\n    子图详情（前10个）:")
            for sg in subgraph_details:
                sg_total = float(sg['total_cost']) if sg['total_cost'] else 0.0
                sg_material = float(sg['material_cost']) if sg['material_cost'] else 0.0
                sg_heat = float(sg['heat_treatment_cost']) if sg['heat_treatment_cost'] else 0.0
                sg_processing = float(sg['processing_cost_total']) if sg['processing_cost_total'] else 0.0
                
                print(f"      {sg['subgraph_id']}: total={sg_total:.2f} "
                      f"(material={sg_material:.2f}, heat={sg_heat:.2f}, processing={sg_processing:.2f})")
        
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 默认查询 M250297
        pattern = "M250297"
    else:
        pattern = sys.argv[1]
    
    asyncio.run(check_job(pattern))
