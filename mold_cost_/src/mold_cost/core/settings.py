"""重构后统一配置入口。"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """运行时配置唯一入口。"""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", ".env.colleague"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )

    APP_NAME: str = "Mold Cost System"
    APP_VERSION: str = "2.1.0"
    PORT: int = 8000
    DEBUG: bool = True
    RELOAD: bool = True

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "mold_cost"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "root"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5

    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 20
    SKIP_REDIS: bool = False

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_HEARTBEAT: int = 86400
    RABBITMQ_QUEUE_JOB_PROCESSING: str = "job_processing"
    RABBITMQ_QUEUE_DLX: str = "job_processing_dlx"
    ENABLE_MESSAGE_RETRY: bool = False

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_USE_HTTPS: bool = False
    MINIO_BUCKET: str = "mold-cost"
    MINIO_BUCKET_FILES: str = "mold-cost"
    MINIO_REGION: str = "us-east-1"
    MINIO_EXTERNAL_ENDPOINT: str = ""
    MINIO_UPLOAD_PART_SIZE: int = 10485760
    MINIO_UPLOAD_WORKERS: int = 5
    MINIO_DOWNLOAD_WORKERS: int = 5

    JWT_SECRET_KEY: str = "your-secret-key-change-in-production-2024"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    MAX_FILE_SIZE_MB: int = 1000
    ALLOWED_FILE_EXTENSIONS: str = ".dwg,.prt"

    OPENAI_API_KEY: str = "sk-dummy"
    OPENAI_MODEL: str = "Qwen3-30B-A3B-Instruct"
    OPENAI_BASE_URL: str = "http://192.168.0.22:8000/v1"
    USE_LLM: bool = True
    USE_LLM_FOR_QUERY_DETAILS: bool = True
    USE_CHAT_HISTORY: bool = True
    MAX_HISTORY_MESSAGES: int = 10
    LLM_TIMEOUT: int = 300
    LLM_TEMPERATURE: float = 0.0

    NC_AGENT_ENABLED: bool = True
    NC_AGENT_URL: str = "http://192.168.0.65:8001"
    NC_AGENT_TIMEOUT: int = 60
    NC_SERVICE_URL: Optional[str] = None
    NC_SERVICE_TIMEOUT: Optional[int] = None

    ODA_FILE_CONVERTER_PATH: str = "D:\\workspace\\tools\\ODA\\ODAFileConverter.exe"

    FEATURE_REPROCESS_API_URL: str = "http://192.168.1.51:8300/api/features/reprocess"
    PRICING_RECALCULATE_API_URL: str = "http://192.168.1.51:8300/api/pricing/recalculate"
    WEIGHT_PRICE_API_URL: str = "http://192.168.0.20:8201/api/price_wg"
    API_TIMEOUT: int = 60

    CAD_PRICE_SEARCH_MCP_URL: str = "http://localhost:8200"
    CAD_PRICE_SEARCH_MCP_HOST: str = "0.0.0.0"
    CAD_PRICE_SEARCH_MCP_PORT: int = 8200

    MAX_RETRIES: int = 3
    JOB_PROCESSING_CONCURRENCY: int = 3
    PRICING_RECALCULATE_CONCURRENCY: int = 4
    FEATURE_RECOGNITION_MAX_CONCURRENT: int = 25
    FEATURE_RECOGNITION_ADAPTIVE_CONCURRENCY: bool = False
    FEATURE_RECOGNITION_MIN_CONCURRENT: int = 10
    FEATURE_RECOGNITION_MAX_CONCURRENT_LIMIT: int = 50
    FEATURE_RECOGNITION_SLOW_THRESHOLD: int = 30000
    FEATURE_RECOGNITION_LOG_PERFORMANCE: bool = True
    MCP_CLIENT_POOL_SIZE: int = 30
    MCP_CLIENT_MAX_RETRIES: int = 3
    MCP_CLIENT_TIMEOUT: int = 600
    PRICING_BATCH_SIZE: int = 50
    EXPORT_WORKERS: int = 5

    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FORMAT: str = "json"
    ENABLE_JSON_LOG: bool = False
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5
    LOG_FILE: str = "app.log"

    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000

    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    PASSWORD_HASH_ROUNDS: int = 12
    CHAT_SESSION_TIMEOUT: int = 3600
    ACCOUNT_LOCK_DURATION: int = 1800

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"
    CORS_ALLOW_CREDENTIALS: bool = True

    ENABLE_WEBSOCKET: bool = True
    ENABLE_CHAT_HISTORY: bool = True
    ENABLE_REVIEW_SYSTEM: bool = True
    ENABLE_METRICS: bool = True

    SUPPORTED_MATERIALS: str = "P20,718,NAK80,S136,H13,2738"
    MIN_THICKNESS: int = 1
    MAX_THICKNESS: int = 500
    MIN_WIRE_LENGTH: int = 0
    MAX_WIRE_LENGTH: int = 10000

    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    SERVER_RELOAD: bool = False
    SERVER_WORKERS: int = 1
    WORKER_PROCESSES: int = 2
    WORKER_TIMEOUT: int = 300
    KEEP_ALIVE: int = 5

    API_GATEWAY_HOST: str = "0.0.0.0"
    API_GATEWAY_PORT: int = 8000
    API_HOST: Optional[str] = None
    API_PORT: Optional[int] = None
    API_RELOAD: Optional[bool] = None
    API_WORKERS: Optional[int] = None
    API_DEBUG: Optional[bool] = None

    @staticmethod
    def _parse_bool_like(value):
        """兼容环境变量中常见的布尔表达。"""
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"false", "0", "no", "off", "release", "production", "prod"}:
                return False
        return value

    @field_validator(
        "DEBUG",
        "RELOAD",
        "SERVER_RELOAD",
        "ENABLE_JSON_LOG",
        "ENABLE_WEBSOCKET",
        "ENABLE_CHAT_HISTORY",
        "ENABLE_REVIEW_SYSTEM",
        "ENABLE_METRICS",
        "NC_AGENT_ENABLED",
        "USE_LLM",
        "USE_LLM_FOR_QUERY_DETAILS",
        "USE_CHAT_HISTORY",
        "FEATURE_RECOGNITION_ADAPTIVE_CONCURRENCY",
        mode="before",
    )
    @classmethod
    def validate_bool_flags(cls, value):
        return cls._parse_bool_like(value)

    @field_validator("MINIO_USE_HTTPS", mode="before")
    @classmethod
    def validate_minio_use_https(cls, value):
        minio_secure = os.getenv("MINIO_SECURE")
        if minio_secure is not None:
            return cls._parse_bool_like(minio_secure)
        return cls._parse_bool_like(value)

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
        )

    @computed_field
    @property
    def MINIO_PRESIGNED_ENDPOINT(self) -> str:
        return self.MINIO_EXTERNAL_ENDPOINT or self.MINIO_ENDPOINT

    @computed_field
    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @computed_field
    @property
    def ALLOWED_EXTENSIONS_LIST(self) -> list[str]:
        return [extension.strip() for extension in self.ALLOWED_FILE_EXTENSIONS.split(",") if extension.strip()]

    @computed_field
    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @computed_field
    @property
    def SUPPORTED_MATERIALS_LIST(self) -> list[str]:
        return [material.strip() for material in self.SUPPORTED_MATERIALS.split(",") if material.strip()]


@lru_cache()
def get_settings() -> Settings:
    """返回缓存后的配置单例。"""
    return Settings()


settings = get_settings()


def print_config_summary() -> None:
    """输出当前关键配置，便于排查环境问题。"""
    print("=" * 70)
    print("Config Summary")
    print("=" * 70)
    print(f"App: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"Redis: {settings.REDIS_URL}")
    print(f"RabbitMQ: {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")
    print(f"MinIO: {settings.MINIO_ENDPOINT}")
    print(f"Debug: {settings.DEBUG}")
    print(f"Log level: {settings.LOG_LEVEL}")
    print("=" * 70)
