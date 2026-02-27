"""
=== 文件合并信息 ===
合并日期: 2026-02-10
更新日期: 2026-02-27
更新内容: 使用统一配置模块 shared.config
=====================

数据库连接模块
负责人：人员A
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 使用统一配置
from shared.config import settings

DATABASE_URL = settings.DATABASE_URL

print(f"[Database] 连接地址: postgresql+asyncpg://{settings.DB_USER}:***@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

# 创建异步引擎（优化连接池配置）
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 关闭SQL日志以提升性能
    pool_size=settings.DB_POOL_SIZE,  # 从配置读取
    max_overflow=settings.DB_MAX_OVERFLOW,  # 从配置读取
    pool_timeout=30,  # 连接超时时间（秒）
    pool_recycle=3600,  # 连接回收时间（1小时）
    pool_pre_ping=True,  # 连接前检查是否有效
)

# 创建会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # 禁用自动flush（来自 mold_cost_）
    autocommit=False  # 禁用自动提交（来自 mold_cost_）
)

# 创建Base类
Base = declarative_base()

async def get_db():
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
