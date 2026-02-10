"""
检查 subgraphs.process_description 字段
1. 检查字段是否存在
2. 检查是否有数据
3. 检查报表导出是否包含此字段
"""
import sys
from pathlib import Path
import asyncio

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api_gateway.database import db

async def check_process_description():
    """检查 process_description 字段"""
    print("=" * 60)
    print("检查 subgraphs.process_description 字段")
    print("=" * 60)
    
    # 1. 检查字段是否存在
    print("\n[1] 检查字段是否存在...")
    check_column_sql = """
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'subgraphs' 
        AND column_name = 'process_description'
    """
    
    result = await db.fetch_one(check_column_sql)
    if result:
        print(f"✓ 字段存在: {result['column_name']}")
        print(f"  数据类型: {result['data_type']}")
        print(f"  最大长度: {result['character_maximum_length']}")
    else:
        print("✗ 字段不存在")
        return
    
    # 2. 检查数据统计
    print("\n[2] 检查数据统计...")
    stats_sql = """
        SELECT 
            COUNT(*) as total_count,
            COUNT(process_description) as has_value_count,
            COUNT(*) - COUNT(process_description) as null_count,
            ROUND(COUNT(process_description)::numeric / COUNT(*)::numeric * 100, 2) as fill_rate
        FROM subgraphs
    """
    
    stats = await db.fetch_one(stats_sql)
    print(f"  总记录数: {stats['total_count']}")
    print(f"  有值记录数: {stats['has_value_count']}")
    print(f"  空值记录数: {stats['null_count']}")
    print(f"  填充率: {stats['fill_rate']}%")
    
    # 3. 查看示例数据
    print("\n[3] 查看示例数据（最近10条有值的记录）...")
    sample_sql = """
        SELECT 
            job_id,
            subgraph_id,
            part_name,
            process_description,
            updated_at
        FROM subgraphs
        WHERE process_description IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT 10
    """
    
    samples = await db.fetch_all(sample_sql)
    if samples:
        for i, row in enumerate(samples, 1):
            print(f"\n  [{i}] {row['part_name']} ({row['subgraph_id'][:8]}...)")
            print(f"      工艺描述: {row['process_description']}")
            print(f"      更新时间: {row['updated_at']}")
    else:
        print("  没有找到有值的记录")
    
    # 4. 按 job_id 统计
    print("\n[4] 按任务统计（最近5个任务）...")
    job_stats_sql = """
        SELECT 
            j.job_id,
            j.dwg_file_name,
            COUNT(s.subgraph_id) as total_subgraphs,
            COUNT(s.process_description) as has_process_desc,
            ROUND(COUNT(s.process_description)::numeric / COUNT(s.subgraph_id)::numeric * 100, 2) as fill_rate
        FROM jobs j
        LEFT JOIN subgraphs s ON j.job_id = s.job_id
        GROUP BY j.job_id, j.dwg_file_name
        ORDER BY j.created_at DESC
        LIMIT 5
    """
    
    job_stats = await db.fetch_all(job_stats_sql)
    if job_stats:
        for i, row in enumerate(job_stats, 1):
            print(f"\n  [{i}] {row['dwg_file_name'] or row['job_id']}")
            print(f"      子图总数: {row['total_subgraphs']}")
            print(f"      有工艺描述: {row['has_process_desc']}")
            print(f"      填充率: {row['fill_rate']}%")
    
    # 5. 检查报表导出代码
    print("\n[5] 检查报表导出代码...")
    report_file = project_root / "api_gateway" / "routers" / "reports.py"
    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'process_description' in content:
                print("  ✓ 报表代码中包含 process_description")
                # 查找具体位置
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'process_description' in line:
                        print(f"    第 {i} 行: {line.strip()}")
            else:
                print("  ✗ 报表代码中未找到 process_description")
    else:
        print("  ✗ 报表文件不存在")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_process_description())
