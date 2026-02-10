"""
乐观锁手动测试脚本
负责人：人员B2

使用方法：
1. 启动 API Gateway: python -m api_gateway.main
2. 在 moldCost 目录下运行: python examples/test_optimistic_lock_manual.py
"""
import asyncio
import httpx
import json
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 配置
BASE_URL = "http://localhost:8211"
TOKEN = "your-jwt-token-here"  # 替换为实际的 JWT Token
JOB_ID = "test-job-optimistic-lock"


async def test_normal_flow():
    """测试正常流程（无冲突）"""
    print("\n" + "="*60)
    print("测试 1: 正常流程（无冲突）")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        
        # 1. 启动审核
        print("\n1️⃣ 启动审核...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/start",
            json={"job_id": JOB_ID},
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 2. 修改
        print("\n2️⃣ 提交修改...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/{JOB_ID}/modify",
            json={"modification_text": "将 UP01 的材质改为 718"},
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 3. 确认
        print("\n3️⃣ 确认修改...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/{JOB_ID}/confirm",
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 测试通过：正常流程成功")
            print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 测试失败：{response.text}")


async def test_version_conflict():
    """测试版本冲突检测"""
    print("\n" + "="*60)
    print("测试 2: 版本冲突检测")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        
        # 1. 启动审核
        print("\n1️⃣ 启动审核...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/start",
            json={"job_id": JOB_ID},
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        
        # 2. 模拟外部系统修改
        print("\n2️⃣ 模拟外部系统修改数据库...")
        print("⚠️  请手动在数据库中修改数据，例如：")
        print(f"   UPDATE subgraphs SET material='718' WHERE subgraph_id='UP01' AND job_id='{JOB_ID}';")
        print("\n按 Enter 继续...")
        input()
        
        # 3. 尝试确认
        print("\n3️⃣ 尝试确认修改...")
        response = await client.post(
            f"{BASE_URL}/api/v1/review/{JOB_ID}/confirm",
            headers=headers
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 409:
            print("✅ 测试通过：成功检测到版本冲突")
            print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 测试失败：应该返回 409，实际返回 {response.status_code}")
            print(f"响应: {response.text}")


async def test_version_calculation():
    """测试版本计算"""
    print("\n" + "="*60)
    print("测试 3: 版本哈希计算")
    print("="*60)
    
    from agents.interaction_agent import InteractionAgent
    
    agent = InteractionAgent()
    
    # 测试数据
    data = {
        "subgraphs": [
            {
                "subgraph_id": "UP01",
                "material": "P20",
                "weight": 10.5
            },
            {
                "subgraph_id": "UP02",
                "material": "718",
                "weight": 8.3
            }
        ],
        "features": [
            {
                "feature_id": "F001",
                "name": "孔"
            }
        ]
    }
    
    print("\n测试数据:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # 计算版本
    version = agent._calculate_data_version(data)
    
    print("\n计算的版本哈希:")
    for key, hash_value in version.items():
        print(f"  {key}: {hash_value}")
    
    print(f"\n✅ 测试通过：成功计算 {len(version)} 条记录的版本哈希")


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("乐观锁功能测试")
    print("="*60)
    
    print("\n请选择测试:")
    print("1. 正常流程（无冲突）")
    print("2. 版本冲突检测")
    print("3. 版本哈希计算")
    print("4. 全部测试")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == "1":
        await test_normal_flow()
    elif choice == "2":
        await test_version_conflict()
    elif choice == "3":
        await test_version_calculation()
    elif choice == "4":
        await test_version_calculation()
        await test_normal_flow()
        await test_version_conflict()
    else:
        print("❌ 无效选项")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
