"""
列出数据库中的所有任务
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from shared.database import AsyncSessionLocal
from shared.models import Job

async def list_jobs():
    """列出所有任务"""
    
    print("=" * 80)
    print("数据库中的任务列表")
    print("=" * 80)
    print()
    
    async with AsyncSessionLocal() as session:
        query = select(Job).order_by(Job.created_at.desc()).limit(20)
        result = await session.execute(query)
        jobs = result.scalars().all()
        
        if not jobs:
            print("❌ 数据库中没有任何任务")
            return
        
        print(f"找到 {len(jobs)} 个任务（最近20个）:")
        print()
        
        for i, job in enumerate(jobs, 1):
            print(f"{i}. Job ID: {job.job_id}")
            print(f"   状态: {job.status}")
            print(f"   总成本: {job.total_cost if job.total_cost else 0:.2f} CNY")
            print(f"   子图数: {job.total_subgraphs if job.total_subgraphs else 0}")
            print(f"   创建时间: {job.created_at}")
            print(f"   更新时间: {job.updated_at}")
            print()
    
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(list_jobs())
