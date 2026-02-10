"""
获取任务的所有子图ID
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from shared.database import AsyncSessionLocal
from shared.models import Subgraph

async def get_subgraph_ids(job_id: str):
    """获取任务的所有子图ID"""
    
    async with AsyncSessionLocal() as session:
        query = select(Subgraph.subgraph_id).where(Subgraph.job_id == job_id).order_by(Subgraph.subgraph_id)
        result = await session.execute(query)
        subgraph_ids = [row[0] for row in result.fetchall()]
    
    if not subgraph_ids:
        print(f"❌ 未找到任何子图")
        return
    
    print(f"找到 {len(subgraph_ids)} 个子图:")
    print()
    print('["' + '", "'.join(subgraph_ids) + '"]')
    print()
    print("复制上面的数组，用于 Postman 请求")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python get_subgraph_ids.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    asyncio.run(get_subgraph_ids(job_id))
