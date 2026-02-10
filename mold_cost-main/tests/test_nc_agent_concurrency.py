"""
测试 NC Agent 的并发能力
用于确定 JOB_PROCESSING_CONCURRENCY 的最大值

运行方式：
    python tests/test_nc_agent_concurrency.py
"""
import asyncio
import httpx
import time
from pathlib import Path

NC_AGENT_URL = "http://192.168.0.65:8001"

async def test_nc_agent_single():
    """测试单个请求的响应时间"""
    print("测试单个请求...")
    
    # 准备测试文件（使用你的实际文件）
    test_prt = Path("path/to/test.prt")  # 替换为实际路径
    test_dwg = Path("path/to/test.dwg")  # 替换为实际路径
    
    if not test_prt.exists() or not test_dwg.exists():
        print("❌ 测试文件不存在，请修改脚本中的文件路径")
        return None
    
    start = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            files = {
                'prt_file': ('model.prt', open(test_prt, 'rb'), 'application/octet-stream'),
                'dxf_file': ('drawing.dwg', open(test_dwg, 'rb'), 'application/octet-stream')
            }
            data = {
                'skip_approval': 'true',
                'auto_continue': 'true'
            }
            
            response = await client.post(
                f"{NC_AGENT_URL}/api/v1/workflow/3d/run",
                files=files,
                data=data
            )
            
            duration = time.time() - start
            
            if response.status_code == 200:
                print(f"✅ 单个请求成功，耗时: {duration:.1f}秒")
                return duration
            else:
                print(f"❌ 请求失败: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

async def test_nc_agent_concurrent(concurrency: int):
    """测试并发请求"""
    print(f"\n测试并发 {concurrency} 个请求...")
    
    # 准备测试文件
    test_prt = Path("path/to/test.prt")  # 替换为实际路径
    test_dwg = Path("path/to/test.dwg")  # 替换为实际路径
    
    if not test_prt.exists() or not test_dwg.exists():
        print("❌ 测试文件不存在")
        return
    
    async def single_request(task_id: int):
        """单个请求"""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                files = {
                    'prt_file': ('model.prt', open(test_prt, 'rb'), 'application/octet-stream'),
                    'dxf_file': ('drawing.dwg', open(test_dwg, 'rb'), 'application/octet-stream')
                }
                data = {
                    'skip_approval': 'true',
                    'auto_continue': 'true'
                }
                
                response = await client.post(
                    f"{NC_AGENT_URL}/api/v1/workflow/3d/run",
                    files=files,
                    data=data
                )
                
                duration = time.time() - start
                
                if response.status_code == 200:
                    return {"task_id": task_id, "success": True, "duration": duration}
                else:
                    return {"task_id": task_id, "success": False, "status": response.status_code}
                    
        except Exception as e:
            duration = time.time() - start
            return {"task_id": task_id, "success": False, "error": str(e), "duration": duration}
    
    # 并发执行
    start = time.time()
    tasks = [single_request(i) for i in range(concurrency)]
    results = await asyncio.gather(*tasks)
    total_duration = time.time() - start
    
    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    failed_count = concurrency - success_count
    
    print(f"\n结果:")
    print(f"  总耗时: {total_duration:.1f}秒")
    print(f"  成功: {success_count}/{concurrency}")
    print(f"  失败: {failed_count}/{concurrency}")
    
    if success_count > 0:
        durations = [r["duration"] for r in results if r["success"]]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        print(f"  平均响应时间: {avg_duration:.1f}秒")
        print(f"  最快: {min_duration:.1f}秒")
        print(f"  最慢: {max_duration:.1f}秒")
    
    # 显示失败的任务
    if failed_count > 0:
        print(f"\n失败的任务:")
        for r in results:
            if not r["success"]:
                print(f"  任务 {r['task_id']}: {r.get('error', r.get('status'))}")
    
    return success_count == concurrency

async def main():
    """主函数"""
    print("=" * 80)
    print("NC Agent 并发能力测试")
    print("=" * 80)
    print(f"NC Agent URL: {NC_AGENT_URL}")
    print()
    
    # 1. 测试单个请求
    single_duration = await test_nc_agent_single()
    
    if single_duration is None:
        print("\n❌ 单个请求失败，无法继续测试")
        return
    
    # 2. 测试不同的并发数
    for concurrency in [2, 3, 4, 5]:
        success = await test_nc_agent_concurrent(concurrency)
        
        if not success:
            print(f"\n⚠️  并发 {concurrency} 时出现失败")
            print(f"💡 建议: JOB_PROCESSING_CONCURRENCY 不要超过 {concurrency - 1}")
            break
        
        # 等待一下，避免对 NC Agent 造成压力
        await asyncio.sleep(5)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
