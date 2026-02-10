"""
阶段2 API 测试脚本
负责人：人员B2

功能：
1. 测试启动审核 API
2. 测试提交修改 API
3. 测试查询状态 API
4. 测试确认修改 API

使用方法：
    python examples/test_stage2_api.py
"""
import asyncio
import requests
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import jwt

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8211")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-2024")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def generate_test_token():
    """生成测试 JWT Token"""
    payload = {
        "sub": "test_user",
        "user_id": "test_user_001",
        "username": "test_user",
        "role": "admin",
        "email": "test@example.com",
        "real_name": "测试用户",
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def print_response(title, response):
    """打印响应"""
    print(f"\n{'=' * 60}")
    print(f"📋 {title}")
    print(f"{'=' * 60}")
    print(f"状态码: {response.status_code}")
    print(f"响应:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_start_review(token, job_id):
    """测试启动审核"""
    url = f"{API_BASE_URL}/api/v1/review/start"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "job_id": job_id
    }
    
    response = requests.post(url, headers=headers, json=data)
    print_response("启动审核", response)
    return response.status_code == 200


def test_modify_review(token, job_id, modification_text):
    """测试提交修改"""
    url = f"{API_BASE_URL}/api/v1/review/{job_id}/modify"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "modification_text": modification_text
    }
    
    response = requests.post(url, headers=headers, json=data)
    print_response("提交修改", response)
    return response.status_code == 200


def test_get_status(token, job_id):
    """测试查询状态"""
    url = f"{API_BASE_URL}/api/v1/review/{job_id}/status"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(url, headers=headers)
    print_response("查询状态", response)
    return response.status_code == 200


def test_confirm_review(token, job_id):
    """测试确认修改"""
    url = f"{API_BASE_URL}/api/v1/review/{job_id}/confirm"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(url, headers=headers)
    print_response("确认修改", response)
    return response.status_code == 200


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="阶段2 API 测试")
    parser.add_argument(
        "--job-id",
        type=str,
        help="指定测试用的 job_id（UUID 格式）"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("阶段2 API 测试")
    print("=" * 60)
    print(f"API 地址: {API_BASE_URL}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 生成 Token
    print("\n🔑 生成测试 Token...")
    token = generate_test_token()
    print(f"Token: {token[:50]}...")
    
    # 测试任务 ID
    if args.job_id:
        job_id = args.job_id
        print(f"任务 ID: {job_id} (用户指定)")
    else:
        job_id = str(uuid.uuid4())
        print(f"任务 ID: {job_id} (随机生成)")
        print(f"\n⚠️  注意: 使用随机 UUID，数据库中可能不存在此任务")
        print(f"   如果测试失败，请先运行: python scripts/get_test_job_id.py")
        print(f"   然后使用: python examples/test_stage2_api.py --job-id YOUR_JOB_ID")
    
    # 测试流程
    results = []
    
    # 1. 启动审核
    print("\n" + "=" * 60)
    print("测试1: 启动审核")
    print("=" * 60)
    success = test_start_review(token, job_id)
    results.append(("启动审核", success))
    
    if not success:
        print("\n❌ 启动审核失败，停止测试")
        return
    
    # 2. 提交修改（第一次）
    print("\n" + "=" * 60)
    print("测试2: 提交修改（第一次）")
    print("=" * 60)
    success = test_modify_review(token, job_id, "将 UP01 的材质改为 718")
    results.append(("提交修改1", success))
    
    # 3. 提交修改（第二次）
    print("\n" + "=" * 60)
    print("测试3: 提交修改（第二次）")
    print("=" * 60)
    success = test_modify_review(token, job_id, "将 UP02 的厚度改为 15mm")
    results.append(("提交修改2", success))
    
    # 4. 查询状态
    print("\n" + "=" * 60)
    print("测试4: 查询状态")
    print("=" * 60)
    success = test_get_status(token, job_id)
    results.append(("查询状态", success))
    
    # 5. 确认修改
    print("\n" + "=" * 60)
    print("测试5: 确认修改")
    print("=" * 60)
    success = test_confirm_review(token, job_id)
    results.append(("确认修改", success))
    
    # 打印测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    # 统计
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 API 服务器")
        print("请确保 API Gateway 正在运行：")
        print("  python -m api_gateway.main")
    except KeyboardInterrupt:
        print("\n\n🛑 测试已取消")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
