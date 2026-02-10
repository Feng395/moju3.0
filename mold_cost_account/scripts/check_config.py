#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置检查脚本
用于查看当前配置信息
"""

from config import get_config

def check_config():
    """检查配置"""
    config = get_config()
    
    print("=" * 60)
    print("当前配置信息")
    print("=" * 60)
    
    print(f"\n【应用配置】")
    print(f"应用名称: {config.APP_NAME}")
    print(f"版本: {config.APP_VERSION}")
    print(f"调试模式: {config.DEBUG}")
    print(f"主机: {config.HOST}")
    print(f"端口: {config.PORT}")
    
    print(f"\n【数据库配置】")
    print(f"主机: {config.DB_HOST}")
    print(f"端口: {config.DB_PORT}")
    print(f"数据库名: {config.DB_NAME}")
    print(f"用户: {config.DB_USER}")
    print(f"密码: {'*' * len(str(config.DB_PASSWORD))}")
    
    print(f"\n【JWT配置】")
    print(f"密钥: {config.JWT_SECRET_KEY[:20]}...")
    print(f"算法: {config.JWT_ALGORITHM}")
    print(f"过期时间: {config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES} 分钟")
    
    print(f"\n【安全配置】")
    print(f"最大失败登录次数: {config.MAX_FAILED_LOGIN_ATTEMPTS}")
    print(f"密码哈希轮数: {config.PASSWORD_HASH_ROUNDS}")
    
    print(f"\n【日志配置】")
    print(f"日志级别: {config.LOG_LEVEL}")
    
    print("\n" + "=" * 60)
    
    # 检查环境变量
    import os
    print("\n【环境变量检查】")
    env_vars = [
        'FLASK_ENV',
        'DB_HOST',
        'DB_PORT',
        'DB_NAME',
        'DB_USER',
        'JWT_EXPIRE_MINUTES',
        'MAX_FAILED_ATTEMPTS',
        'LOG_LEVEL'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"{var}: {value}")
        else:
            print(f"{var}: (未设置，使用默认值)")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_config()
