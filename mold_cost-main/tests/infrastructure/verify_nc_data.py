"""
验证 NC Agent 数据写入
检查：
1. 本地文件是否保存
2. subgraphs 表的时间字段是否更新
3. features 表的 nc_time_cost 字段是否更新
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database import get_db
from shared.models import Job, Subgraph, Feature
from sqlalchemy import select, func
import json


async def verify_nc_data(job_id: str = None):
    """
    验证 NC Agent 数据写入
    
    Args:
        job_id: 任务ID（可选，如果不提供则查询最新的任务）
    """
    print("=" * 80)
    print("NC Agent 数据写入验证")
    print("=" * 80)
    
    async for db in get_db():
        # 1. 查找任务
        if job_id:
            print(f"\n📋 查询指定任务: {job_id}")
            result = await db.execute(
                select(Job).where(Job.job_id == job_id)
            )
        else:
            print(f"\n📋 查询最新任务...")
            result = await db.execute(
                select(Job)
                .order_by(Job.created_at.desc())
                .limit(1)
            )
        
        job = result.scalar_one_or_none()
        
        if not job:
            print("❌ 未找到任务")
            return
        
        job_id = str(job.job_id)
        print(f"✅ 找到任务: {job_id}")
        print(f"   状态: {job.status}")
        print(f"   阶段: {job.current_stage}")
        print(f"   创建时间: {job.created_at}")
        print(f"   更新时间: {job.updated_at}")
        
        # 2. 检查本地文件
        print(f"\n📁 检查本地文件...")
        logs_dir = Path("logs/nc_responses")
        files = []
        
        if not logs_dir.exists():
            print(f"❌ 目录不存在: {logs_dir}")
        else:
            # 查找该任务的响应文件
            files = list(logs_dir.glob(f"{job_id}_*.json"))
            
            if not files:
                print(f"❌ 未找到响应文件: {logs_dir}/{job_id}_*.json")
            else:
                print(f"✅ 找到 {len(files)} 个响应文件:")
                for file in sorted(files):
                    file_size = file.stat().st_size
                    file_time = datetime.fromtimestamp(file.stat().st_mtime)
                    print(f"   - {file.name} ({file_size:,} bytes, {file_time})")
                    
                    # 读取最新的文件内容
                    if file == files[-1]:
                        try:
                            with open(file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            json_output = data.get("data", {}).get("json_output", {})
                            print(f"   - 包含 {len(json_output)} 个子图的数据")
                            
                            # 显示前 3 个子图
                            for i, (subgraph_name, subgraph_data) in enumerate(list(json_output.items())[:3]):
                                operations = subgraph_data.get("operations", [])
                                print(f"     • {subgraph_name}: {len(operations)} 个操作")
                            
                            if len(json_output) > 3:
                                print(f"     • ... 还有 {len(json_output) - 3} 个子图")
                                
                        except Exception as e:
                            print(f"   ⚠️  读取文件失败: {e}")
        
        # 3. 检查 subgraphs 表
        print(f"\n📊 检查 subgraphs 表...")
        result = await db.execute(
            select(Subgraph)
            .where(Subgraph.job_id == job_id)
            .order_by(Subgraph.subgraph_id)
        )
        subgraphs = result.scalars().all()
        
        if not subgraphs:
            print(f"❌ 未找到子图数据")
            return
        
        print(f"✅ 找到 {len(subgraphs)} 个子图")
        
        # 统计有 NC 时间数据的子图
        nc_data_count = 0
        total_roughing = 0
        total_milling = 0
        total_drilling = 0
        
        print(f"\n子图 NC 时间数据:")
        print(f"{'子图ID':<50} {'开粗(分)':<10} {'精铣(分)':<10} {'钻孔(分)':<10} {'总计(分)':<10}")
        print("-" * 90)
        
        for subgraph in subgraphs[:10]:  # 只显示前 10 个
            roughing = float(subgraph.nc_roughing_time or 0)
            milling = float(subgraph.nc_milling_time or 0)
            drilling = float(subgraph.drilling_time or 0)
            total = roughing + milling + drilling
            
            if total > 0:
                nc_data_count += 1
                total_roughing += roughing
                total_milling += milling
                total_drilling += drilling
                status = "✅"
            else:
                status = "❌"
            
            print(f"{status} {subgraph.subgraph_id:<48} {roughing:<10.2f} {milling:<10.2f} {drilling:<10.2f} {total:<10.2f}")
        
        if len(subgraphs) > 10:
            print(f"... 还有 {len(subgraphs) - 10} 个子图")
        
        print("-" * 90)
        print(f"有 NC 数据的子图: {nc_data_count}/{len(subgraphs)}")
        print(f"总开粗时间: {total_roughing:.2f} 分钟")
        print(f"总精铣时间: {total_milling:.2f} 分钟")
        print(f"总钻孔时间: {total_drilling:.2f} 分钟")
        print(f"总 NC 时间: {total_roughing + total_milling + total_drilling:.2f} 分钟")
        print(f"总 NC 时间: {(total_roughing + total_milling + total_drilling)/60:.2f} 小时")
        
        # 4. 检查 features 表
        print(f"\n📋 检查 features 表...")
        result = await db.execute(
            select(Feature)
            .where(Feature.job_id == job_id)
            .order_by(Feature.subgraph_id)
        )
        features = result.scalars().all()
        
        if not features:
            print(f"❌ 未找到特征数据")
            return
        
        print(f"✅ 找到 {len(features)} 个特征记录")
        
        # 统计有 nc_time_cost 数据的特征
        nc_cost_count = 0
        
        print(f"\n特征 NC 时间详细数据:")
        print(f"{'子图ID':<50} {'详细数据'}")
        print("-" * 100)
        
        for feature in features[:10]:  # 只显示前 10 个
            if feature.nc_time_cost:
                nc_cost_count += 1
                nc_details = feature.nc_time_cost.get("nc_details", [])
                
                # 格式化显示
                details_str = ", ".join([f"{d['code']}:{d['value']}分" for d in nc_details[:5]])
                if len(nc_details) > 5:
                    details_str += f" ... (+{len(nc_details) - 5})"
                
                print(f"✅ {feature.subgraph_id:<48} {details_str}")
            else:
                print(f"❌ {feature.subgraph_id:<48} (无数据)")
        
        if len(features) > 10:
            print(f"... 还有 {len(features) - 10} 个特征")
        
        print("-" * 100)
        print(f"有 nc_time_cost 数据的特征: {nc_cost_count}/{len(features)}")
        
        # 5. 显示一个完整的示例
        if nc_cost_count > 0:
            print(f"\n📝 完整示例（第一个有数据的特征）:")
            for feature in features:
                if feature.nc_time_cost:
                    print(f"子图ID: {feature.subgraph_id}")
                    print(f"nc_time_cost:")
                    print(json.dumps(feature.nc_time_cost, indent=2, ensure_ascii=False))
                    break
        
        # 6. 总结
        print(f"\n" + "=" * 80)
        print(f"验证总结:")
        print(f"=" * 80)
        
        # 检查本地文件
        file_status = "✅ 已保存" if files else "❌ 未保存"
        print(f"1. 本地文件: {file_status}")
        
        # 检查 subgraphs 表
        subgraph_status = "✅ 已写入" if nc_data_count > 0 else "❌ 未写入"
        subgraph_coverage = f"{nc_data_count}/{len(subgraphs)} ({nc_data_count/len(subgraphs)*100:.1f}%)" if len(subgraphs) > 0 else "0/0"
        print(f"2. subgraphs 表: {subgraph_status} ({subgraph_coverage})")
        
        # 检查 features 表
        feature_status = "✅ 已写入" if nc_cost_count > 0 else "❌ 未写入"
        feature_coverage = f"{nc_cost_count}/{len(features)} ({nc_cost_count/len(features)*100:.1f}%)" if len(features) > 0 else "0/0"
        print(f"3. features 表: {feature_status} ({feature_coverage})")
        
        # 整体评估
        if files and nc_data_count > 0 and nc_cost_count > 0:
            print(f"\n✅ NC Agent 数据写入正常！")
        elif files and (nc_data_count == 0 or nc_cost_count == 0):
            print(f"\n⚠️  本地文件已保存，但数据库未写入，请检查日志")
        else:
            print(f"\n❌ NC Agent 可能未执行或执行失败，请检查日志")
        
        break  # 只需要第一次迭代


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="验证 NC Agent 数据写入")
    parser.add_argument("--job-id", help="任务ID（可选，默认查询最新任务）")
    args = parser.parse_args()
    
    await verify_nc_data(args.job_id)


if __name__ == "__main__":
    asyncio.run(main())
