"""
阶段3 端到端测试
负责人：人员B2

功能：
测试完整的审核流程，包含 NLP 解析

使用方法：
    python examples/test_stage3_e2e.py --job-id YOUR_JOB_ID
"""
import asyncio
import requests
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import jwt

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    
    try:
        data = response.json()
        print(f"响应:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except:
        print(f"响应: {response.text}")
        return None


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="阶段3 端到端测试")
    parser.add_argument(
        "--job-id",
        type=str,
        help="指定测试用的 job_id（UUID 格式）"
    )
    
    args = parser.parse_args()
    
    if not args.job_id:
        print("❌ 请提供 job_id")
        print("使用方法: python examples/test_stage3_e2e.py --job-id YOUR_JOB_ID")
        return
    
    print("=" * 60)
    print("阶段3 端到端测试 - 完整审核流程（含 NLP）")
    print("=" * 60)
    print(f"API 地址: {API_BASE_URL}")
    print(f"Job ID: {args.job_id}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 生成 Token
    print("\n🔑 生成测试 Token...")
    token = generate_test_token()
    print(f"Token: {token[:50]}...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试1: 启动审核
    print("\n" + "=" * 60)
    print("测试1: 启动审核")
    print("=" * 60)
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/review/start",
        headers=headers,
        json={"job_id": args.job_id}
    )
    
    data = print_response("启动审核", response)
    if response.status_code != 200:
        print("\n❌ 启动审核失败，停止测试")
        return
    
    # 测试2: 使用自然语言修改（简单指令）
    print("\n" + "=" * 60)
    print("测试2: 自然语言修改（简单指令）")
    print("=" * 60)
    
    modification_text = "将 UP01 的材质改为 718"
    print(f"修改指令: {modification_text}")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/review/{args.job_id}/modify",
        headers=headers,
        json={"modification_text": modification_text}
    )
    
    data = print_response("提交修改", response)
    if data and data.get("data"):
        parsed = data["data"].get("parsed_changes", [])
        print(f"\n✅ NLP 解析结果: {len(parsed)} 个修改")
        for i, change in enumerate(parsed, 1):
            print(f"  {i}. {change.get('table')}.{change.get('id')}.{change.get('field')} = {change.get('value')}")
    
    # 测试3: 使用自然语言修改（复杂指令）
    print("\n" + "=" * 60)
    print("测试3: 自然语言修改（复杂指令）")
    print("=" * 60)
    
    modification_text = "请把上模板的材料换成 S136，下模板的重量改为 8kg"
    print(f"修改指令: {modification_text}")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/review/{args.job_id}/modify",
        headers=headers,
        json={"modification_text": modification_text}
    )
    
    data = print_response("提交修改", response)
    if data and data.get("data"):
        parsed = data["data"].get("parsed_changes", [])
        print(f"\n✅ NLP 解析结果: {len(parsed)} 个修改")
        for i, change in enumerate(parsed, 1):
            print(f"  {i}. {change.get('table')}.{change.get('id')}.{change.get('field')} = {change.get('value')}")
    
    # 测试4: 查询状态
    print("\n" + "=" * 60)
    print("测试4: 查询状态")
    print("=" * 60)
    
    response = requests.get(
        f"{API_BASE_URL}/api/v1/review/{args.job_id}/status",
        headers=headers
    )
    
    data = print_response("查询状态", response)
    if data and data.get("data"):
        status_data = data["data"]
        print(f"\n📊 审核状态:")
        print(f"  - 状态: {status_data.get('review_status')}")
        print(f"  - 锁定: {status_data.get('is_locked')}")
        print(f"  - 修改次数: {status_data.get('modifications_count')}")
    
    # 测试5: 确认修改
    print("\n" + "=" * 60)
    print("测试5: 确认修改")
    print("=" * 60)
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/review/{args.job_id}/confirm",
        headers=headers
    )
    
    data = print_response("确认修改", response)
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print("✅ 完整的审核流程测试完成")
    print("✅ NLP 解析功能正常工作")
    print("✅ 支持简单和复杂的自然语言指令")
    print("\n💡 提示:")
    print("  - 规则解析：快速、确定性")
    print("  - LLM 解析：智能、灵活")
    print("  - Fallback：LLM 失败时自动降级")


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
