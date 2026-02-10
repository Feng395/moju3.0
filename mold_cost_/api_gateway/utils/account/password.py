"""密码加密工具"""
import hashlib
import bcrypt
from typing import Tuple


def hash_password_bcrypt(password: str) -> str:
    """
    使用bcrypt加密密码
    
    Args:
        password: 明文密码
        
    Returns:
        加密后的密码哈希
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def hash_password_sha256(password: str) -> str:
    """
    使用SHA256加密密码（用于兼容旧数据）
    
    Args:
        password: 明文密码
        
    Returns:
        SHA256哈希值
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        stored_hash: 存储的密码哈希
        
    Returns:
        密码是否匹配
    """
    try:
        # 检查是否是bcrypt哈希
        if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'):
            return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash.encode('utf-8'))
        else:
            # 简单哈希比较（用于测试或旧数据）
            return hash_password_sha256(plain_password) == stored_hash
    except Exception:
        return False
