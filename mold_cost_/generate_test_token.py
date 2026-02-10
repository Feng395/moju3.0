"""
生成测试JWT Token
用于开发测试
"""
import sys
import os
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 需要先加载环境变量
from dotenv import load_dotenv
load_dotenv()

from datetime import timedelta
from jose import jwt
from datetime import datetime

def generate_test_token():
    """生成测试token"""
    # 从环境变量读取配置
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    
    # 测试用户数据 - 使用固定的UUID方便测试
    test_user_id = "a63b7863-5faf-4b00-9ec3-758495b0fb66"
    
    # 获取当前UTC时间
    now = datetime.utcnow()
    
    user_data = {
        "user_id": test_user_id,  # 固定的测试用户UUID
        "username": "test_user",
        "sub": "test_user",  # JWT标准字段
        "roles": ["admin"],
        "role": "admin",  # 兼容字段
        "iat": now,  # 签发时间 - 必须添加
        "exp": now + timedelta(hours=24)  # 过期时间
    }
    
    # 生成token
    token = jwt.encode(user_data, SECRET_KEY, algorithm=ALGORITHM)
    
    return token, test_user_id


if __name__ == "__main__":
    print("=" * 60)
    print("生成测试JWT Token")
    print("=" * 60)
    
    token, user_id = generate_test_token()
    
    print(f"\n测试用户ID（UUID格式）：{user_id}")
    print(f"\n测试Token（有效期24小时）：")
    print(f"\n{token}\n")
    
    print("=" * 60)
    print("使用方法：")
    print("=" * 60)
    print(f"\ncurl -X POST http://localhost:8000/api/v1/jobs/upload \\")
    print(f'  -H "Authorization: Bearer {token}" \\')
    print(f'  -F "dwg_file=@test.dwg" \\')
    print(f'  -F "prt_file=@test.prt"')
    print()

