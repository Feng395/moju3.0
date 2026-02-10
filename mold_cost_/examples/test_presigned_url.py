"""
测试预签名URL接口

使用方法:
1. 确保API Gateway正在运行: python -m api_gateway.main
2. 运行此测试: python examples/test_presigned_url.py
"""
import requests
import json
from datetime import datetime

# 配置
API_BASE_URL = "http://localhost:8211"
TEST_FILE_PATH = "dxf/2026/01/9ba97078-a7bf-4472-a977-564dca64cee7/LP-02.dxf"

# 生成测试JWT Token（使用项目中的方法）
def generate_test_token():
    """生成测试用的JWT Token"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from api_gateway.auth import create_access_token
    
    token = create_access_token({
        "sub": "test_user",
        "user_id": "test_user_001",
        "username": "test_user",
        "role": "user",
        "email": "test@example.com",
        "real_name": "测试用户"
    })
    
    return token


def test_generate_presigned_url():
    """测试生成预签名URL"""
    print("=" * 60)
    print("测试: 生成MinIO文件预签名URL")
    print("=" * 60)
    
    # 1. 生成JWT Token
    print("\n1️⃣ 生成JWT Token...")
    try:
        token = generate_test_token()
        print(f"✅ Token生成成功")
        print(f"   Token: {token[:50]}...")
    except Exception as e:
        print(f"❌ Token生成失败: {e}")
        return
    
    # 2. 测试基本请求
    print("\n2️⃣ 测试基本请求（1小时过期）...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/files/presigned-url",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "file_path": TEST_FILE_PATH,
                "expires_in": 3600
            }
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 请求成功")
            print(f"   URL: {data['data']['url'][:100]}...")
            print(f"   过期时间: {data['data']['expires_at']}")
            print(f"   过期秒数: {data['data']['expires_in']}")
            print(f"   文件路径: {data['data']['file_path']}")
            print(f"   Bucket: {data['data']['bucket']}")
        else:
            print(f"❌ 请求失败")
            print(f"   响应: {response.text}")
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 3. 测试自定义下载文件名
    print("\n3️⃣ 测试自定义下载文件名...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/files/presigned-url",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "file_path": TEST_FILE_PATH,
                "expires_in": 7200,
                "download_filename": "我的图纸.dxf"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 请求成功")
            print(f"   URL包含自定义文件名参数")
            print(f"   过期时间: {data['data']['expires_in']}秒 (2小时)")
        else:
            print(f"❌ 请求失败: {response.text}")
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 4. 测试最短过期时间（60秒）
    print("\n4️⃣ 测试最短过期时间（60秒）...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/files/presigned-url",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "file_path": TEST_FILE_PATH,
                "expires_in": 60
            }
        )
        
        if response.status_code == 200:
            print(f"✅ 最短过期时间测试通过")
        else:
            print(f"❌ 请求失败: {response.text}")
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 5. 测试最长过期时间（7天）
    print("\n5️⃣ 测试最长过期时间（7天 = 604800秒）...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/files/presigned-url",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "file_path": TEST_FILE_PATH,
                "expires_in": 604800
            }
        )
        
        if response.status_code == 200:
            print(f"✅ 最长过期时间测试通过")
        else:
            print(f"❌ 请求失败: {response.text}")
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 6. 测试参数验证 - 过期时间过短
    print("\n6️⃣ 测试参数验证 - 过期时间过短（应该失败）...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/files/presigned-url",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "file_path": TEST_FILE_PATH,
                "expires_in": 30  # 少于60秒
            }
        )
        
        if response.status_code == 422:
            print(f"✅ 参数验证正常（拒绝了过短的过期时间）")
        else:
            print(f"⚠️ 预期422错误，实际: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 7. 测试参数验证 - 路径遍历攻击
    print("\n7️⃣ 测试安全验证 - 路径遍历攻击（应该失败）...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/files/presigned-url",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "file_path": "../../../etc/passwd",
                "expires_in": 3600
            }
        )
        
        if response.status_code == 422:
            print(f"✅ 安全验证正常（拒绝了路径遍历攻击）")
        else:
            print(f"⚠️ 预期422错误，实际: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 8. 测试无Token访问（应该失败）
    print("\n8️⃣ 测试无Token访问（应该失败）...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/files/presigned-url",
            headers={
                "Content-Type": "application/json"
            },
            json={
                "file_path": TEST_FILE_PATH,
                "expires_in": 3600
            }
        )
        
        if response.status_code == 403:
            print(f"✅ JWT认证正常（拒绝了无Token请求）")
        else:
            print(f"⚠️ 预期403错误，实际: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_generate_presigned_url()
