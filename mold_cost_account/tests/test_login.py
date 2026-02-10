import requests
import json

# 测试登录接口
def test_login():
    base_url = "http://localhost:8000"
    login_url = f"{base_url}/api/login"
    verify_url = f"{base_url}/api/verify-token"
    
    # 测试数据
    test_cases = [
        {
            "name": "正常登录",
            "data": {
                "username": "admin",
                "password": "123456"
            }
        },
        {
            "name": "用户名为空",
            "data": {
                "username": "",
                "password": "testpass"
            }
        },
        {
            "name": "密码为空",
            "data": {
                "username": "testuser",
                "password": ""
            }
        },
        {
            "name": "错误密码",
            "data": {
                "username": "admin",
                "password": "wrongpass"
            }
        }
    ]
    
    for case in test_cases:
        print(f"\n{'='*50}")
        print(f"测试: {case['name']}")
        print('='*50)
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(login_url, json=case['data'], headers=headers)
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 如果登录成功且有token，测试token验证
            if result.get('success') and result.get('token'):
                print(f"\n--- 测试Token验证 ---")
                token_data = {"token": result['token']}
                token_response = requests.post(verify_url, json=token_data, headers=headers)
                print(f"Token验证状态码: {token_response.status_code}")
                print(f"Token验证响应: {json.dumps(token_response.json(), indent=2, ensure_ascii=False)}")
                
        except Exception as e:
            print(f"请求错误: {e}")

def test_token_verification():
    """单独测试token验证"""
    print(f"\n{'='*50}")
    print("测试无效Token")
    print('='*50)
    
    verify_url = "http://localhost:8000/api/verify-token"
    
    # 测试无效token
    invalid_tokens = [
        {"name": "空token", "token": ""},
        {"name": "无效token", "token": "invalid.token.here"},
        {"name": "过期token", "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"}
    ]
    
    for test in invalid_tokens:
        print(f"\n测试: {test['name']}")
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(verify_url, json={"token": test['token']}, headers=headers)
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"请求错误: {e}")

if __name__ == "__main__":
    test_login()
    test_token_verification()