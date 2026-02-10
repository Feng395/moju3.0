"""
配置管理模块
从环境变量读取配置

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost_/api_gateway/config.py
- 合并策略：保留原文件（mold_cost-main 无此文件）
- 主要功能：
  1. 统一管理所有配置项
  2. 从环境变量读取配置
  3. 提供配置单例访问
  4. 支持数据库、Redis、RabbitMQ、MinIO、JWT等配置
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "mold_cost_db"
    DB_USER: str = "root"
    DB_PASSWORD: str = "yunzai123"
    
    @property
    def DATABASE_URL(self) -> str:
        """构造数据库连接URL"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    
    # RabbitMQ配置
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "admin"
    RABBITMQ_PASSWORD: str = "Admin@123"
    RABBITMQ_QUEUE_JOB_PROCESSING: str = "job_processing"
    RABBITMQ_QUEUE_DLX: str = "job_processing_dlx"
    
    @property
    def RABBITMQ_URL(self) -> str:
        """构造RabbitMQ连接URL"""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
    
    # MinIO配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_REGION: str = "us-east-1"
    MINIO_USE_HTTPS: bool = False
    MINIO_BUCKET_FILES: str = "files"
    MINIO_EXTERNAL_ENDPOINT: str = ""  # 外部访问地址（用于生成预签名URL）
    
    @property
    def MINIO_PRESIGNED_ENDPOINT(self) -> str:
        """用于生成预签名URL的endpoint（优先使用外部地址）"""
        return self.MINIO_EXTERNAL_ENDPOINT or self.MINIO_ENDPOINT
    
    # JWT配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    
    # 文件上传配置
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_FILE_EXTENSIONS: str = ".dwg,.prt"
    
    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """最大文件大小（字节）"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def ALLOWED_EXTENSIONS_LIST(self) -> List[str]:
        """允许的文件扩展名列表"""
        return [ext.strip() for ext in self.ALLOWED_FILE_EXTENSIONS.split(",")]
    
    # 外部NC Agent配置
    NC_AGENT_URL: str = "http://nc-agent:8001"
    NC_AGENT_TIMEOUT: int = 60
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # 外部NC Agent配置
    NC_AGENT_URL: str = "http://nc-agent:8001"
    NC_AGENT_TIMEOUT: int = 60
    
    # MCP服务配置（可选，第一期不使用）
    CAD_PARSER_MCP_URL: str = "http://localhost:8101"
    FEATURE_RECOGNITION_MCP_URL: str = "http://localhost:8102"
    NC_CONNECTOR_MCP_URL: str = "http://localhost:8103"
    PRICING_SERVER_MCP_URL: str = "http://localhost:8105"
    REPORT_GENERATOR_MCP_URL: str = "http://localhost:8107"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # 监控配置（可选）
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000
    
    # 开发模式
    DEBUG: bool = True
    RELOAD: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # 允许额外的字段


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
