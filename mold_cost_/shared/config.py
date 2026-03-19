"""
统一配置管理模块
所有配置项的唯一来源

使用方法:
    from shared.config import settings
    
    # 访问配置
    db_host = settings.DB_HOST
    redis_url = settings.REDIS_URL
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, computed_field
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """统一配置类 - 所有配置的唯一来源"""
    
    # ========== 应用配置 ==========
    APP_NAME: str = "模具成本核算系统"
    APP_VERSION: str = "2.1.0"
    PORT: int = 8000
    DEBUG: bool = True
    RELOAD: bool = True
    
    # ========== 数据库配置 ==========
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "mold_cost"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "root"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """构造数据库连接URL"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # ========== Redis配置 ==========
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 20
    SKIP_REDIS: bool = False  # 降级模式
    
    # ========== RabbitMQ配置 ==========
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_HEARTBEAT: int = 86400  # 24小时
    RABBITMQ_QUEUE_JOB_PROCESSING: str = "job_processing"
    RABBITMQ_QUEUE_DLX: str = "job_processing_dlx"
    ENABLE_MESSAGE_RETRY: bool = False
    
    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        """构造RabbitMQ连接URL"""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
    
    # ========== MinIO配置 ==========
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_USE_HTTPS: bool = False  # 兼容旧变量名
    MINIO_BUCKET: str = "mold-cost"
    MINIO_BUCKET_FILES: str = "mold-cost"
    MINIO_REGION: str = "us-east-1"
    MINIO_EXTERNAL_ENDPOINT: str = ""
    MINIO_UPLOAD_PART_SIZE: int = 10485760  # 10MB
    MINIO_UPLOAD_WORKERS: int = 5
    MINIO_DOWNLOAD_WORKERS: int = 5
    
    @field_validator('MINIO_USE_HTTPS', mode='before')
    @classmethod
    def validate_minio_use_https(cls, v):
        """支持 MINIO_SECURE 和 MINIO_USE_HTTPS 两种环境变量名"""
        minio_secure = os.getenv('MINIO_SECURE')
        if minio_secure is not None:
            # 确保 minio_secure 是字符串
            if isinstance(minio_secure, str):
                return minio_secure.lower() in ('true', '1', 'yes')
            # 如果不是字符串，返回 False
            return False
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return v
    
    @computed_field
    @property
    def MINIO_PRESIGNED_ENDPOINT(self) -> str:
        """用于生成预签名URL的endpoint（优先使用外部地址）"""
        return self.MINIO_EXTERNAL_ENDPOINT or self.MINIO_ENDPOINT
    
    # ========== JWT配置 ==========
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production-2024"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # ========== 文件上传配置 ==========
    MAX_FILE_SIZE_MB: int = 1000
    ALLOWED_FILE_EXTENSIONS: str = ".dwg,.prt"
    
    @computed_field
    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """最大文件大小（字节）"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @computed_field
    @property
    def ALLOWED_EXTENSIONS_LIST(self) -> List[str]:
        """允许的文件扩展名列表"""
        return [ext.strip() for ext in self.ALLOWED_FILE_EXTENSIONS.split(",")]
    
    # ========== LLM配置 ==========
    OPENAI_API_KEY: str = "sk-dummy"
    OPENAI_MODEL: str = "Qwen3-30B-A3B-Instruct"
    OPENAI_BASE_URL: str = "http://192.168.0.22:8000/v1"
    USE_LLM: bool = True
    USE_LLM_FOR_QUERY_DETAILS: bool = True
    USE_CHAT_HISTORY: bool = True
    MAX_HISTORY_MESSAGES: int = 10
    LLM_TIMEOUT: int = 300
    LLM_TEMPERATURE: float = 0.0
    
    # ========== 外部服务配置 ==========
    NC_AGENT_ENABLED: bool = True
    NC_AGENT_URL: str = "http://192.168.0.65:8001"
    NC_AGENT_TIMEOUT: int = 60
    NC_SERVICE_URL: Optional[str] = None  # 兼容旧变量名
    NC_SERVICE_TIMEOUT: Optional[int] = None  # 兼容旧变量名
    
    ODA_FILE_CONVERTER_PATH: str = "D:\\workspace\\ODA\\ODAFileConverter.exe"
    
    # 外部API
    FEATURE_REPROCESS_API_URL: str = "http://192.168.1.51:8300/api/features/reprocess"
    PRICING_RECALCULATE_API_URL: str = "http://192.168.1.51:8300/api/pricing/recalculate"
    WEIGHT_PRICE_API_URL: str = "http://192.168.0.20:8201/api/price_wg"
    API_TIMEOUT: int = 60
    
    # ========== MCP服务配置 ==========
    CAD_PRICE_SEARCH_MCP_URL: str = "http://localhost:8200"
    CAD_PRICE_SEARCH_MCP_HOST: str = "0.0.0.0"
    CAD_PRICE_SEARCH_MCP_PORT: int = 8200
    
    # ========== 性能配置 ==========
    MAX_RETRIES: int = 3
    JOB_PROCESSING_CONCURRENCY: int = 3
    PRICING_RECALCULATE_CONCURRENCY: int = 4
    FEATURE_RECOGNITION_MAX_CONCURRENT: int = 25
    FEATURE_RECOGNITION_ADAPTIVE_CONCURRENCY: bool = False
    FEATURE_RECOGNITION_MIN_CONCURRENT: int = 10
    FEATURE_RECOGNITION_MAX_CONCURRENT_LIMIT: int = 50
    FEATURE_RECOGNITION_SLOW_THRESHOLD: int = 30000  # 毫秒
    FEATURE_RECOGNITION_LOG_PERFORMANCE: bool = True
    
    MCP_CLIENT_POOL_SIZE: int = 30
    MCP_CLIENT_MAX_RETRIES: int = 3
    MCP_CLIENT_TIMEOUT: int = 600
    
    PRICING_BATCH_SIZE: int = 50
    EXPORT_WORKERS: int = 5
    
    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FORMAT: str = "json"
    ENABLE_JSON_LOG: bool = False
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_FILE: str = "app.log"
    
    # ========== 监控配置 ==========
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000
    
    # ========== 安全配置 ==========
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    PASSWORD_HASH_ROUNDS: int = 12
    CHAT_SESSION_TIMEOUT: int = 3600
    ACCOUNT_LOCK_DURATION: int = 1800
    
    # ========== CORS配置 ==========
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"
    CORS_ALLOW_CREDENTIALS: bool = True
    
    @computed_field
    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """CORS允许的源列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # ========== 功能开关 ==========
    ENABLE_WEBSOCKET: bool = True
    ENABLE_CHAT_HISTORY: bool = True
    ENABLE_REVIEW_SYSTEM: bool = True
    ENABLE_METRICS: bool = True
    
    # ========== 参数验证配置 ==========
    SUPPORTED_MATERIALS: str = "P20,718,NAK80,S136,H13,2738"
    MIN_THICKNESS: int = 1
    MAX_THICKNESS: int = 500
    MIN_WIRE_LENGTH: int = 0
    MAX_WIRE_LENGTH: int = 10000
    
    @computed_field
    @property
    def SUPPORTED_MATERIALS_LIST(self) -> List[str]:
        """支持的材质列表"""
        return [mat.strip() for mat in self.SUPPORTED_MATERIALS.split(",")]
    
    # ========== 服务器配置 ==========
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    SERVER_RELOAD: bool = False
    SERVER_WORKERS: int = 1
    WORKER_PROCESSES: int = 2
    WORKER_TIMEOUT: int = 300
    KEEP_ALIVE: int = 5
    
    # ========== API Gateway配置 ==========
    API_GATEWAY_HOST: str = "0.0.0.0"
    API_GATEWAY_PORT: int = 8000
    API_HOST: Optional[str] = None  # 兼容旧变量名
    API_PORT: Optional[int] = None  # 兼容旧变量名
    API_RELOAD: Optional[bool] = None  # 兼容旧变量名
    API_WORKERS: Optional[int] = None  # 兼容旧变量名
    API_DEBUG: Optional[bool] = None  # 兼容旧变量名
    
    class Config:
        """Pydantic配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # 允许额外的字段
        
        # 支持从多个位置加载 .env
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    使用 lru_cache 确保配置只加载一次
    """
    return Settings()


# 全局配置实例
settings = get_settings()


def print_config_summary():
    """打印配置摘要（用于调试）"""
    print("=" * 70)
    print("配置摘要")
    print("=" * 70)
    print(f"应用: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"数据库: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"Redis: {settings.REDIS_URL}")
    print(f"RabbitMQ: {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")
    print(f"MinIO: {settings.MINIO_ENDPOINT}")
    print(f"调试模式: {settings.DEBUG}")
    print(f"日志级别: {settings.LOG_LEVEL}")
    print("=" * 70)


if __name__ == "__main__":
    # 测试配置加载
    print_config_summary()
