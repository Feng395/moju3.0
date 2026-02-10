"""
应用成本同步解决方案
同时创建视图和触发器
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from api_gateway.database import db


async def apply_migrations():
    """应用迁移"""
    
    print(f"\n{'='*80}")
    print("应用成本同步解决方案（视图 + 触发器）")
    print(f"{'='*80}\n")
    
    migrations_dir = Path(__file__).parent
    
    # 迁移文件列表
    migrations = [
        ("create_job_cost_view.sql", "创建任务成本汇总视图"),
        ("create_auto_sync_trigger.sql", "创建自动同步触发器")
    ]
    
    success_count = 0
    failed_count = 0
    
    for sql_file, description in migrations:
        sql_path = migrations_dir / sql_file
        
        if not sql_path.exists():
            print(f"❌ 找不到迁移脚本: {sql_file}")
            failed_count += 1
            continue
        
        print(f"\n[{success_count + failed_count + 1}] {description}")
        print(f"    文件: {sql_file}")
        
        try:
            # 读取 SQL 文件
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 执行 SQL（使用 execute 方法）
            # 注意：对于包含多条语句的 SQL，需要逐条执行或使用事务
            pool = await db._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(sql_content)
            
            print(f"    ✅ 执行成功")
            success_count += 1
            
        except Exception as e:
            print(f"    ❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
    
    print(f"\n{'='*80}")
    print(f"迁移完成:")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"{'='*80}\n")
    
    if success_count == len(migrations):
        print("✅ 所有迁移已成功应用！")
        print("\n说明:")
        print("  1. 已创建 v_job_cost_summary 视图，查询时自动计算总成本")
        print("  2. 已创建触发器，subgraphs 更新时自动同步 jobs.total_cost")
        print("  3. 代码已更新为使用视图查询")
        print("\n后续步骤:")
        print("  1. 重启 API Gateway 服务")
        print("  2. 测试任务列表和详情接口")
        print("  3. 测试报表导出功能")
        return True
    else:
        print("⚠️  部分迁移失败，请检查错误日志")
        return False


if __name__ == "__main__":
    success = asyncio.run(apply_migrations())
    sys.exit(0 if success else 1)
