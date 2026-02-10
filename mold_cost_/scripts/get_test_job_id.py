"""
获取测试用的 job_id
负责人：人员B2

功能：
从数据库中查询一个已存在的 job_id 用于测试

使用方法：
    python scripts/get_test_job_id.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database import get_db
from sqlalchemy import select, text


async def get_test_job_id():
    """获取一个测试用的 job_id"""
    try:
        print("=" * 60)
        print("查询测试用的 job_id")
        print("=" * 60)
        
        async for db in get_db():
            # 查询最近的一个 job
            result = await db.execute(
                text("SELECT job_id FROM jobs ORDER BY created_at DESC LIMIT 1")
            )
            row = result.fetchone()
            
            if row:
                job_id = str(row[0])
                print(f"\n✅ 找到 job_id: {job_id}")
                print(f"\n💡 使用此 job_id 测试:")
                print(f"   export TEST_JOB_ID={job_id}")
                print(f"   python examples/test_stage2_api.py --job-id {job_id}")
                return job_id
            else:
                print("\n❌ 数据库中没有任务")
                print("\n💡 提示:")
                print("   1. 先创建一个任务")
                print("   2. 或者使用 Mock 测试: python examples/test_stage2_api_mock.py")
                return None
    
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主函数"""
    await get_test_job_id()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 已取消")
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
