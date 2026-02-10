#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("错误: bcrypt库未安装")
    print("请运行: pip install bcrypt")
    exit(1)

def hash_password_bcrypt(password: str, rounds: int = 12) -> str:
    """
    使用bcrypt加密密码
    
    Args:
        password: 明文密码
        rounds: 加密轮数，默认12（推荐10-12）
    
    Returns:
        bcrypt哈希字符串
    """
    # 将密码转换为字节
    password_bytes = password.encode('utf-8')
    
    # 生成盐并哈希
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # 返回字符串格式
    return hashed.decode('utf-8')

def verify_password_bcrypt(password: str, hashed: str) -> bool:
    """
    验证bcrypt密码
    
    Args:
        password: 明文密码
        hashed: bcrypt哈希
    
    Returns:
        验证结果
    """
    password_bytes = password.encode('utf-8')
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

if __name__ == "__main__":
    # 加密密码 "123456"
    password = "123456"
    
    print(f"原始密码: {password}")
    print()
    
    # 生成不同轮数的哈希
    for rounds in [10, 12, 14]:
        hashed = hash_password_bcrypt(password, rounds)
        print(f"bcrypt哈希 (rounds={rounds}):")
        print(hashed)
        
        # 验证
        is_valid = verify_password_bcrypt(password, hashed)
        print(f"验证结果: {is_valid}")
        print("-" * 80)
    
    # 推荐使用的哈希（rounds=12）
    recommended_hash = hash_password_bcrypt(password, 12)
    print("推荐使用的哈希值（可直接存入数据库）:")
    print(recommended_hash)