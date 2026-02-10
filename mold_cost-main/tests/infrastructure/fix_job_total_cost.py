"""
修复 jobs.total_cost 字段
从 subgraphs 表重新计算并更新 jobs.total_cost

使用方法:
    python tests/infrastructure/fix_job_total_cost.py <job_id>
    python tests/infrastructure/fix_job_total_cost.py --all  # 修复所有任务
"""
import asyncio
import sys
import os
from uuid import UUID

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.database import get_db
from sqlalchemy import text


async def fix_single_job(job_id: str):
    """修复单个任务的 total_cost"""
    print(f"\n{'='*80}")
    print(f"修复任务: {job_id}")
    print(f"{'='*80}")
    
    async for db in get_db():
        try:
            # 1. 查询当前 jobs.total_cost
            job_query = text("""
                SELECT total_cost, dwg_file_name
                FROM jobs
                WHERE job_id = :job_id
            """)
            result = await db.execute(job_query, {"job_id": job_id})
            job_row = result.mappings().fetchone()
            
            if not job_row:
                print(f"❌ 任务不存在: {job_id}")
                return False
            
            current_total = float(job_row['total_cost']) if job_row['total_cost'] else 0.0
            dwg_name = job_row['dwg_file_name'] or job_id
            
            print(f"\n📋 任务信息: {dwg_name}")
            print(f"   当前 jobs.total_cost: {current_total:.2f}")
            
            # 2. 从 subgraphs 表计算正确的 total_cost
            subgraph_query = text("""
                SELECT 
                    COUNT(*) as subgraph_count,
                    COALESCE(SUM(total_cost), 0) as correct_total_cost,
                    COALESCE(SUM(material_cost), 0) as total_material_cost,
                    COALESCE(SUM(heat_treatment_cost), 0) as total_heat_cost,
                    COALESCE(SUM(processing_cost_total), 0) as total_processing_cost
                FROM subgraphs
                WHERE job_id = :job_id
            """)
            result = await db.execute(subgraph_query, {"job_id": job_id})
            summary = result.mappings().fetchone()
            
            correct_total = float(summary['correct_total_cost'])
            subgraph_count = summary['subgraph_count']
            
            print(f"\n📊 子图统计:")
            print(f"   子图数量: {subgraph_count}")
            print(f"   材料成本: {float(summary['total_material_cost']):.2f}")
            print(f"   热处理成本: {float(summary['total_heat_cost']):.2f}")
            print(f"   加工成本: {float(summary['total_processing_cost']):.2f}")
            print(f"   正确的总成本: {correct_total:.2f}")
            
            # 3. 比较差异
            diff = abs(correct_total - current_total)
            
            if diff < 0.01:
                print(f"\n✅ 数据一致，无需修复")
                return True
            
            print(f"\n⚠️  发现差异: {diff:.2f}")
            print(f"   jobs.total_cost:     {current_total:.2f}")
            print(f"   subgraphs 汇总:      {correct_total:.2f}")
            
            # 4. 更新 jobs.total_cost
            update_query = text("""
                UPDATE jobs
                SET 
                    total_cost = :total_cost,
                    updated_at = NOW()
                WHERE job_id = :job_id
            """)
            
            await db.execute(update_query, {"job_id": job_id, "total_cost": correct_total})
            await db.commit()
            
            print(f"\n✅ 已修复 jobs.total_cost = {correct_total:.2f}")
            return True
            
        except Exception as e:
            print(f"\n❌ 修复失败: {e}")
            import traceback
            traceback.print_exc()
            return False


async def fix_all_jobs():
    """修复所有任务的 total_cost"""
    print(f"\n{'='*80}")
    print(f"修复所有任务的 total_cost")
    print(f"{'='*80}")
    
    async for db in get_db():
        try:
            # 查询所有任务
            query = text("""
                SELECT 
                    j.job_id,
                    j.dwg_file_name,
                    j.total_cost as job_total,
                    COALESCE(SUM(s.total_cost), 0) as subgraph_total
                FROM jobs j
                LEFT JOIN subgraphs s ON j.job_id = s.job_id
                WHERE j.status != 'archived'
                GROUP BY j.job_id, j.dwg_file_name, j.total_cost
                HAVING ABS(COALESCE(j.total_cost, 0) - COALESCE(SUM(s.total_cost), 0)) > 0.01
                ORDER BY j.created_at DESC
            """)
            
            result = await db.execute(query)
            rows = result.mappings().all()
            
            if not rows:
                print("\n✅ 所有任务的 total_cost 都是正确的")
                return
            
            print(f"\n发现 {len(rows)} 个任务需要修复:\n")
            
            for row in rows:
                job_id = str(row['job_id'])
                dwg_name = row['dwg_file_name'] or job_id[:8]
                job_total = float(row['job_total']) if row['job_total'] else 0.0
                subgraph_total = float(row['subgraph_total'])
                diff = abs(job_total - subgraph_total)
                
                print(f"  {dwg_name:30s}  jobs: {job_total:10.2f}  subgraphs: {subgraph_total:10.2f}  差异: {diff:8.2f}")
            
            print(f"\n开始修复...")
            
            success_count = 0
            failed_count = 0
            
            for row in rows:
                job_id = str(row['job_id'])
                if await fix_single_job(job_id):
                    success_count += 1
                else:
                    failed_count += 1
            
            print(f"\n{'='*80}")
            print(f"修复完成:")
            print(f"  成功: {success_count}")
            print(f"  失败: {failed_count}")
            print(f"{'='*80}")
            
        except Exception as e:
            print(f"\n❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python tests/infrastructure/fix_job_total_cost.py <job_id>")
        print("  python tests/infrastructure/fix_job_total_cost.py --all")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == "--all":
        await fix_all_jobs()
    else:
        # 验证 job_id 格式
        try:
            UUID(arg)
        except ValueError:
            print(f"❌ 无效的 job_id 格式: {arg}")
            sys.exit(1)
        
        await fix_single_job(arg)


if __name__ == "__main__":
    asyncio.run(main())
