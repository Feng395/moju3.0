"""
清理审核系统的 Redis 锁和状态
负责人：人员B2

功能：
1. 清理所有审核锁
2. 清理所有审核状态
3. 显示清理结果

使用方法：
    python scripts/clear_review_locks.py
    python scripts/clear_review_locks.py --job-id test-job-001  # 清理特定任务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_gateway.utils.redis_client import redis_client


async def clear_all_review_data():
    """清理所有审核相关的 Redis 数据"""
    try:
        await redis_client.connect()
        
        print("=" * 60)
        print("清理审核系统 Redis 数据")
        print("=" * 60)
        
        # 获取所有审核相关的键（使用底层 client）
        lock_keys = await redis_client.client.keys("review:lock:*")
        state_keys = await redis_client.client.keys("review:state:*")
        
        print(f"\n找到 {len(lock_keys)} 个锁")
        print(f"找到 {len(state_keys)} 个状态")
        
        # 清理锁
        if lock_keys:
            print("\n清理锁:")
            for key in lock_keys:
                await redis_client.client.delete(key)
                print(f"  ✅ 已删除: {key}")
        
        # 清理状态
        if state_keys:
            print("\n清理状态:")
            for key in state_keys:
                await redis_client.client.delete(key)
                print(f"  ✅ 已删除: {key}")
        
        if not lock_keys and not state_keys:
            print("\n✨ 没有需要清理的数据")
        else:
            print(f"\n✅ 清理完成！共删除 {len(lock_keys) + len(state_keys)} 个键")
        
    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await redis_client.close()


async def clear_job_review_data(job_id: str):
    """清理特定任务的审核数据"""
    try:
        await redis_client.connect()
        
        print("=" * 60)
        print(f"清理任务 {job_id} 的审核数据")
        print("=" * 60)
        
        lock_key = f"review:lock:{job_id}"
        state_key = f"review:state:{job_id}"
        
        # 检查是否存在（使用底层 client）
        lock_exists = await redis_client.client.exists(lock_key)
        state_exists = await redis_client.client.exists(state_key)
        
        if not lock_exists and not state_exists:
            print(f"\n✨ 任务 {job_id} 没有审核数据")
            return
        
        # 删除锁
        if lock_exists:
            await redis_client.client.delete(lock_key)
            print(f"\n✅ 已删除锁: {lock_key}")
        
        # 删除状态
        if state_exists:
            await redis_client.client.delete(state_key)
            print(f"✅ 已删除状态: {state_key}")
        
        print(f"\n✅ 清理完成！")
        
    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await redis_client.close()


async def list_review_data():
    """列出所有审核数据"""
    try:
        await redis_client.connect()
        
        print("=" * 60)
        print("审核系统 Redis 数据")
        print("=" * 60)
        
        # 获取所有审核相关的键（使用底层 client）
        lock_keys = await redis_client.client.keys("review:lock:*")
        state_keys = await redis_client.client.keys("review:state:*")
        
        if lock_keys:
            print(f"\n🔒 锁 ({len(lock_keys)} 个):")
            for key in lock_keys:
                ttl = await redis_client.client.ttl(key)
                print(f"  - {key} (TTL: {ttl}秒)")
        
        if state_keys:
            print(f"\n📊 状态 ({len(state_keys)} 个):")
            for key in state_keys:
                ttl = await redis_client.client.ttl(key)
                value = await redis_client.client.get(key)
                if value:
                    import json
                    data = json.loads(value)
                    status = data.get("status", "unknown")
                    mods = len(data.get("modifications", []))
                    print(f"  - {key}")
                    print(f"    状态: {status}, 修改次数: {mods}, TTL: {ttl}秒")
        
        if not lock_keys and not state_keys:
            print("\n✨ 没有审核数据")
        
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await redis_client.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="清理审核系统 Redis 数据")
    parser.add_argument(
        "--job-id",
        type=str,
        help="清理特定任务的数据"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有审核数据"
    )
    
    args = parser.parse_args()
    
    if args.list:
        # 列出数据
        asyncio.run(list_review_data())
    elif args.job_id:
        # 清理特定任务
        asyncio.run(clear_job_review_data(args.job_id))
    else:
        # 清理所有数据
        asyncio.run(clear_all_review_data())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 已取消")
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
