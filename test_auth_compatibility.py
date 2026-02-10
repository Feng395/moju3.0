"""
认证API兼容性测试脚本
用于验证 FastAPI 版本与 Flask 版本的响应格式一致性
"""
import requests
import json

# 配置
BASE_URL = "http://localhost:8211"  # FastAPI 版本
# BASE_URL = "http://192.168.0.14:8000"  # Flask 版本（用于对比）

def print_response(title, response):
    """打印响应信息"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    try:
        print(f"响应体: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应体: {response.text}")

def test_login_success():
    """测试登录成功"""
    url = f"{BASE_URL}/api/login"
    data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(url, json=data)
    print_response("测试1: 登录成功", response)
    
    # 验证
    assert response.status_code == 200, f"期望状态码200，实际{response.status_code}"
    json_data = response.json()
    assert json_data["success"] == True, "期望success为True"
    assert "token" in json_data, "期望返回token"
    assert "user_info" in json_data, "期望返回user_info"
    
    return json_data.get("token")

def test_login_failure():
    """测试登录失败"""
    url = f"{BASE_URL}/api/login"
    data = {
        "username": "admin",
        "password": "wrongpassword"
    }
    
    response = requests.post(url, json=data)
    print_response("测试2: 登录失败（密码错误）", response)
    
    # 验证：登录失败应该返回200状态码，不是401
    assert response.status_code == 200, f"期望状态码200，实际{response.status_code}"
    json_data = response.json()
    assert json_data["success"] == False, "期望success为False"
    assert "message" in json_data, "期望返回message"

def test_login_empty_username():
    """测试空用户名"""
    url = f"{BASE_URL}/api/login"
    data = {
        "username": "",
        "password": "admin123"
    }
    
    response = requests.post(url, json=data)
    print_response("测试3: 空用户名", response)
    
    # 验证
    assert response.status_code == 422, f"期望状态码422（Pydantic验证失败），实际{response.status_code}"

def test_verify_token_valid(token):
    """测试验证有效token"""
    url = f"{BASE_URL}/api/verify-token"
    data = {
        "token": token
    }
    
    response = requests.post(url, json=data)
    print_response("测试4: 验证有效token", response)
    
    # 验证
    assert response.status_code == 200, f"期望状态码200，实际{response.status_code}"
    json_data = response.json()
    assert json_data["success"] == True, "期望success为True"
    assert "payload" in json_data, "期望返回payload"

def test_verify_token_invalid():
    """测试验证无效token"""
    url = f"{BASE_URL}/api/verify-token"
    data = {
        "token": "invalid_token_here"
    }
    
    response = requests.post(url, json=data)
    print_response("测试5: 验证无效token", response)
    
    # 验证：无效token应该返回401状态码
    assert response.status_code == 401, f"期望状态码401，实际{response.status_code}"
    json_data = response.json()
    assert json_data["success"] == False, "期望success为False"

def test_change_password(token):
    """测试修改密码"""
    url = f"{BASE_URL}/api/change-password"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    data = {
        "new_password": "newpassword123"
    }
    
    response = requests.post(url, json=data, headers=headers)
    print_response("测试6: 修改密码", response)
    
    # 验证
    assert response.status_code in [200, 400], f"期望状态码200或400，实际{response.status_code}"
    json_data = response.json()
    assert "success" in json_data, "期望返回success字段"
    assert "message" in json_data, "期望返回message字段"

def test_change_password_no_token():
    """测试修改密码（无token）"""
    url = f"{BASE_URL}/api/change-password"
    data = {
        "new_password": "newpassword123"
    }
    
    response = requests.post(url, json=data)
    print_response("测试7: 修改密码（无token）", response)
    
    # 验证：无token应该返回401
    assert response.status_code == 401, f"期望状态码401，实际{response.status_code}"

def test_options_request():
    """测试OPTIONS预检请求"""
    url = f"{BASE_URL}/api/login"
    
    response = requests.options(url)
    print_response("测试8: OPTIONS预检请求", response)
    
    # 验证CORS头
    assert "access-control-allow-origin" in response.headers, "期望返回CORS头"

def main():
    """运行所有测试"""
    print(f"\n{'#'*60}")
    print(f"# 认证API兼容性测试")
    print(f"# 测试地址: {BASE_URL}")
    print(f"{'#'*60}")
    
    try:
        # 测试登录
        token = test_login_success()
        test_login_failure()
        test_login_empty_username()
        
        # 测试token验证
        test_verify_token_valid(token)
        test_verify_token_invalid()
        
        # 测试修改密码
        test_change_password(token)
        test_change_password_no_token()
        
        # 测试CORS
        test_options_request()
        
        print(f"\n{'='*60}")
        print("✅ 所有测试通过！")
        print(f"{'='*60}\n")
        
    except AssertionError as e:
        print(f"\n{'='*60}")
        print(f"❌ 测试失败: {e}")
        print(f"{'='*60}\n")
        return 1
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ 测试异常: {e}")
        print(f"{'='*60}\n")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
