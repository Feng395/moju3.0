"""
NC Time Agent 集成测试
测试完整的 NC 时间计算流程
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.nc_time_agent import NCTimeAgent


async def test_file_path_detection():
    """测试文件路径检测逻辑"""
    print("=" * 60)
    print("测试 1: 文件路径检测")
    print("=" * 60)
    
    agent = NCTimeAgent()
    
    # 测试用例
    test_cases = [
        ("files/jobs/xxx/model.prt", "MinIO 路径"),
        ("/tmp/model.prt", "Linux 本地路径"),
        ("C:\\temp\\model.prt", "Windows 本地路径"),
        ("jobs/2024/01/model.prt", "MinIO 路径（无 files 前缀）"),
    ]
    
    for file_path, expected_type in test_cases:
        is_local = file_path.startswith('/') or (len(file_path) > 1 and file_path[1] == ':')
        detected_type = "本地路径" if is_local else "MinIO 路径"
        status = "✅" if detected_type == expected_type else "❌"
        print(f"{status} {file_path:40s} -> {detected_type}")
    
    print()


async def test_minio_connection():
    """测试 MinIO 连接"""
    print("=" * 60)
    print("测试 2: MinIO 连接")
    print("=" * 60)
    
    try:
        from scripts.minio_client import MinIOClient
        
        minio_client = MinIOClient()
        
        if minio_client.client:
            print("✅ MinIO 客户端创建成功")
            print(f"   Endpoint: {os.getenv('MINIO_ENDPOINT')}")
            print(f"   Bucket: {os.getenv('MINIO_BUCKET_FILES', 'files')}")
            
            # 测试连接（列出 bucket）
            try:
                buckets = minio_client.client.list_buckets()
                print(f"✅ MinIO 连接正常，找到 {len(buckets)} 个 bucket")
                for bucket in buckets:
                    print(f"   - {bucket.name}")
            except Exception as e:
                print(f"⚠️ MinIO 连接测试失败: {e}")
        else:
            print("❌ MinIO 客户端创建失败")
            
    except Exception as e:
        print(f"❌ MinIO 测试失败: {e}")
    
    print()


async def test_nc_agent_with_sample_files():
    """测试 NC Agent 调用（需要实际文件）"""
    print("=" * 60)
    print("测试 3: NC Agent 完整流程测试")
    print("=" * 60)
    print("⚠️ 此测试需要实际的 PRT 和 DXF 文件")
    print()
    
    # 从用户获取测试文件路径
    print("请提供测试文件路径（可以是 MinIO 路径或本地路径）：")
    print("示例 MinIO 路径: files/jobs/test/model.prt")
    print("示例本地路径: C:\\temp\\model.prt")
    print()
    
    # 这里可以硬编码测试路径，或者跳过
    print("跳过实际文件测试（需要手动配置测试文件）")
    print()
    
    # 如果要测试，取消注释以下代码：
    """
    prt_file = input("PRT 文件路径: ").strip()
    dwg_file = input("DXF/DWG 文件路径: ").strip()
    test_job_id = input("测试 Job ID (或按回车使用默认): ").strip() or "test-job-id"
    
    if prt_file and dwg_file:
        agent = NCTimeAgent()
        
        try:
            print(f"\n开始测试 NC Agent 调用...")
            print(f"  Job ID: {test_job_id}")
            print(f"  PRT: {prt_file}")
            print(f"  DWG: {dwg_file}")
            print()
            
            result = await agent.process({
                "job_id": test_job_id,
                "prt_file_path": prt_file,
                "dwg_file_path": dwg_file
            })
            
            print(f"\n测试结果:")
            print(f"  状态: {result.get('status')}")
            print(f"  消息: {result.get('message')}")
            
            if result.get('summary'):
                summary = result['summary']
                print(f"  总子图数: {summary.get('total_subgraphs')}")
                print(f"  成功数: {summary.get('success_count')}")
                print(f"  失败数: {summary.get('failed_count')}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    """


async def test_environment_config():
    """测试环境配置"""
    print("=" * 60)
    print("测试 4: 环境配置检查")
    print("=" * 60)
    
    configs = {
        "NC Agent": {
            "NC_AGENT_URL": os.getenv("NC_AGENT_URL"),
            "NC_AGENT_TIMEOUT": os.getenv("NC_AGENT_TIMEOUT"),
        },
        "MinIO": {
            "MINIO_ENDPOINT": os.getenv("MINIO_ENDPOINT"),
            "MINIO_BUCKET_FILES": os.getenv("MINIO_BUCKET_FILES"),
            "MINIO_ACCESS_KEY": "***" if os.getenv("MINIO_ACCESS_KEY") else None,
            "MINIO_SECRET_KEY": "***" if os.getenv("MINIO_SECRET_KEY") else None,
        }
    }
    
    for category, items in configs.items():
        print(f"\n{category} 配置:")
        for key, value in items.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {value or '未配置'}")
    
    print()


async def main():
    """运行所有测试"""
    print("\n")
    print("=" * 60)
    print("NC Time Agent 集成测试套件")
    print("=" * 60)
    print()
    
    # 运行测试
    await test_environment_config()
    await test_file_path_detection()
    await test_minio_connection()
    await test_nc_agent_with_sample_files()
    
    # 总结
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print()
    print("下一步:")
    print("1. 确保所有环境配置正确（NC_AGENT_URL, MinIO 配置）")
    print("2. 准备测试用的 PRT 和 DXF 文件")
    print("3. 运行 test_nc_agent_connection.py 测试 NC Agent 连接")
    print("4. 使用实际任务测试完整流程")
    print()


if __name__ == "__main__":
    asyncio.run(main())
