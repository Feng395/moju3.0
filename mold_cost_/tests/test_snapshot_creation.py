"""
测试快照创建功能
"""
import asyncio
import sys
from pathlib import Path
import uuid

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_gateway.repositories.snapshot_repository import SnapshotRepository
from shared.database import get_db


async def test_create_snapshots():
    """测试创建快照"""
    print("\n" + "="*60)
    print("测试快照创建功能")
    print("="*60)
    
    # 生成测试job_id
    test_job_id = str(uuid.uuid4())
    print(f"\n测试 Job ID: {test_job_id}")
    
    try:
        async with get_db() as db:
            # 测试1: 创建价格快照
            print("\n1. 创建价格快照...")
            try:
                count = await SnapshotRepository.create_price_snapshots(db, test_job_id)
                print(f"✅ 价格快照创建成功: {count} 条记录")
            except Exception as e:
                print(f"❌ 价格快照创建失败: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # 测试2: 创建工艺快照
            print("\n2. 创建工艺快照...")
            try:
                count = await SnapshotRepository.create_process_snapshots(db, test_job_id)
                print(f"✅ 工艺快照创建成功: {count} 条记录")
            except Exception as e:
                print(f"❌ 工艺快照创建失败: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # 提交事务
            await db.commit()
            print("\n✅ 事务已提交")
            
            # 测试3: 查询价格快照
            print("\n3. 查询价格快照...")
            try:
                snapshots = await SnapshotRepository.get_price_snapshots(db, test_job_id)
                print(f"✅ 查询成功: {len(snapshots)} 条记录")
                
                if snapshots:
                    print("\n前3条记录:")
                    for i, snap in enumerate(snapshots[:3], 1):
                        print(f"  {i}. category={snap.category}, sub_category={snap.sub_category}, price={snap.price}")
            except Exception as e:
                print(f"❌ 查询价格快照失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 测试4: 查询工艺快照
            print("\n4. 查询工艺快照...")
            try:
                snapshots = await SnapshotRepository.get_process_snapshots(db, test_job_id)
                print(f"✅ 查询成功: {len(snapshots)} 条记录")
                
                if snapshots:
                    print("\n前3条记录:")
                    for i, snap in enumerate(snapshots[:3], 1):
                        print(f"  {i}. feature_type={snap.feature_type}, name={snap.name}, priority={snap.priority}")
            except Exception as e:
                print(f"❌ 查询工艺快照失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n" + "="*60)
            print("✅ 所有测试完成！")
            print("="*60)
            print(f"\n💡 提示: 测试数据已保存，job_id = {test_job_id}")
            print("   可以在数据库中查看:")
            print(f"   SELECT * FROM job_price_snapshots WHERE job_id = '{test_job_id}';")
            print(f"   SELECT * FROM job_process_snapshots WHERE job_id = '{test_job_id}';")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_create_snapshots())
