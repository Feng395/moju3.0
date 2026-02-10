"""
检查 API Gateway 是否运行
"""
import httpx
import sys

BASE_URL = "http://localhost:8211"

def check_server():
    """检查服务器是否运行"""
    try:
        # 尝试访问 chat health 接口
        response = httpx.get(f"{BASE_URL}/api/v1/chat/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ API Gateway 正在运行")
            print(f"   URL: {BASE_URL}")
            print(f"   响应: {response.json()}")
            return True
        else:
            print(f"⚠️  API Gateway 响应异常: {response.status_code}")
            return False
    except httpx.ConnectError:
        print("❌ 无法连接到 API Gateway")
        print(f"   URL: {BASE_URL}")
        print("\n请确保 API Gateway 正在运行:")
        print("   cd moldCost")
        print("   python -m api_gateway.main")
        return False
    except httpx.TimeoutException:
        print("❌ 连接超时")
        print(f"   URL: {BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("检查 API Gateway 状态")
    print("=" * 60)
    print()
    
    if check_server():
        sys.exit(0)
    else:
        sys.exit(1)
