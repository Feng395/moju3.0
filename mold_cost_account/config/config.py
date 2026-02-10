#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
包含数据库连接、JWT、应用等配置信息
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Config:
    """基础配置类"""
    
    # 应用配置
    APP_NAME = "用户登录API"
    APP_VERSION = "1.0.0"
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 8000
    
    # 数据库配置
    DB_HOST = os.getenv('DB_HOST', '192.168.1.54')
    DB_PORT = os.getenv('DB_PORT', 5432)
    DB_NAME = os.getenv('DB_NAME', 'mold_cost_db')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'yunzai123')
    
    # 数据库连接池配置
    DB_POOL_SIZE = 5
    DB_MAX_OVERFLOW = 10
    DB_POOL_TIMEOUT = 30
    
    # JWT配置
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production-2024')
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRE_MINUTES', 30))
    
    # 安全配置
    MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv('MAX_FAILED_ATTEMPTS', 5))
    PASSWORD_HASH_ROUNDS = int(os.getenv('BCRYPT_ROUNDS', 12))
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def get_database_url(cls):
        """获取数据库连接URL"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def get_database_config(cls):
        """获取数据库配置字典"""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'database': cls.DB_NAME,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD
        }

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    
    # 生产环境安全配置
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')  # 生产环境必须设置
    MAX_FAILED_LOGIN_ATTEMPTS = 3
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 生产环境token有效期更短

class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    DB_NAME = 'test_mold_cost_db'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 5

# 配置映射
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """获取配置类"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    return config_map.get(config_name, DevelopmentConfig)