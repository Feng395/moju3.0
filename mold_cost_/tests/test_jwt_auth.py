"""
JWT认证测试脚本
基于JWT_GUIDE.md标准
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import jwt
from datetime import datetime, timedelta
from shared.security import (
    create_access_token,
    verify_access_token,
    generate_token_pair,
    extract_user_from_token,
    decode_token
)

def test_create_token():
    """测试创建JWT Token"""
    print("\n" + "="*60)
    print("测试1: 创建JWT Token")
    print("="*60)
    
    # 创建token
    token_data = {
        "sub": "admin",
        "user_id": "12345678-1234-1234-1234-123456789012",
        "role": "admin",
        "email": "admin@example.com",
        "real_name": "管理员"
    }
    
    token = create_access_token(token_data)
    
    if token:
        print(f"✅ Token创建成功")
        print(f"Token: {token[:50]}...")
        
        # 解析token（不验证签名，仅用于查看内容）
        parts = token.split('.')
        if len(parts) == 3:
            import base64
            import json
            
            # 解码header
            header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
            print(f"\nHeader: {json.dumps(header, indent=2)}")
            
            # 解码payload
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            print(f"\nPayload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            # 检查必需字段
            required_fields = ['sub', 'user_id', 'role', 'exp', 'iat']
            missing = [f for f in required_fields if f not in payload]
            
            if missing:
                print(f"\n⚠️  缺少字段: {missing}")
            else:
                print(f"\n✅ 所有必需字段都存在")
        
        return token
    else:
        print("❌ Token创建失败")
        return None


def test_verify_token(token):
    """测试验证JWT Token"""
    print("\n" + "="*60)
    print("测试2: 验证JWT Token")
    print("="*60)
    
    if not token:
        print("❌ 没有token可验证")
        return
    
    # 验证token
    payload = verify_access_token(token)
    
    if payload:
        print("✅ Token验证成功")
        print(f"\n用户信息:")
        print(f"  - 用户名: {payload.get('sub')}")
        print(f"  - 用户ID: {payload.get('user_id')}")
        print(f"  - 角色: {payload.get('role')}")
        print(f"  - 邮箱: {payload.get('email')}")
        print(f"  - 真实姓名: {payload.get('real_name')}")
        print(f"  - 签发时间: {datetime.fromtimestamp(payload.get('iat'))}")
        print(f"  - 过期时间: {datetime.fromtimestamp(payload.get('exp'))}")
    else:
        print("❌ Token验证失败")


def test_expired_token():
    """测试过期Token"""
    print("\n" + "="*60)
    print("测试3: 过期Token处理")
    print("="*60)
    
    # 创建一个已过期的token（过期时间为-1秒）
    token_data = {
        "sub": "test_user",
        "user_id": "test_123",
        "role": "user"
    }
    
    expired_token = create_access_token(
        token_data,
        expires_delta=timedelta(seconds=-1)
    )
    
    print(f"创建过期token: {expired_token[:50]}...")
    
    # 尝试验证
    payload = verify_access_token(expired_token)
    
    if payload:
        print("❌ 过期token不应该验证成功")
    else:
        print("✅ 过期token正确被拒绝")


def test_token_pair():
    """测试生成Token对"""
    print("\n" + "="*60)
    print("测试4: 生成Token对（Access + Refresh）")
    print("="*60)
    
    tokens = generate_token_pair(
        user_id="12345678-1234-1234-1234-123456789012",
        username="admin",
        role="admin",
        email="admin@example.com",
        real_name="管理员"
    )
    
    if tokens:
        print("✅ Token对生成成功")
        print(f"\nAccess Token: {tokens['access_token'][:50]}...")
        print(f"Refresh Token: {tokens['refresh_token'][:50]}...")
        print(f"Token Type: {tokens['token_type']}")
        print(f"Expires In: {tokens['expires_in']} 秒")
        
        # 验证access token
        access_payload = verify_access_token(tokens['access_token'])
        if access_payload:
            print(f"\n✅ Access Token验证成功")
            print(f"  - Token类型: {access_payload.get('type')}")
        
        return tokens
    else:
        print("❌ Token对生成失败")
        return None


def test_extract_user():
    """测试从Token提取用户信息"""
    print("\n" + "="*60)
    print("测试5: 从Token提取用户信息")
    print("="*60)
    
    # 创建token
    token_data = {
        "sub": "test_user",
        "user_id": "test_123",
        "role": "operator",
        "email": "test@example.com",
        "real_name": "测试用户"
    }
    
    token = create_access_token(token_data)
    
    # 提取用户信息
    user_info = extract_user_from_token(token)
    
    if user_info:
        print("✅ 用户信息提取成功")
        print(f"\n用户信息:")
        for key, value in user_info.items():
            print(f"  - {key}: {value}")
    else:
        print("❌ 用户信息提取失败")


def test_invalid_token():
    """测试无效Token"""
    print("\n" + "="*60)
    print("测试6: 无效Token处理")
    print("="*60)
    
    invalid_tokens = [
        "invalid.token.here",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        "",
        None
    ]
    
    for i, token in enumerate(invalid_tokens, 1):
        print(f"\n测试无效token {i}: {str(token)[:30]}...")
        payload = decode_token(token) if token else None
        
        if payload:
            print(f"  ❌ 不应该验证成功")
        else:
            print(f"  ✅ 正确拒绝无效token")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("JWT认证测试 - 基于JWT_GUIDE.md标准")
    print("="*60)
    
    try:
        # 测试1: 创建token
        token = test_create_token()
        
        # 测试2: 验证token
        test_verify_token(token)
        
        # 测试3: 过期token
        test_expired_token()
        
        # 测试4: token对
        test_token_pair()
        
        # 测试5: 提取用户信息
        test_extract_user()
        
        # 测试6: 无效token
        test_invalid_token()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
