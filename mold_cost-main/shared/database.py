"""
数据库连接模块
负责人：人员A
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 支持两种配置方式
# 方式1: 直接使用 DATABASE_URL
# 方式2: 使用分开的配置项
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # 从分开的配置项构建 URL
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password")
    dbname = os.getenv("DB_NAME", "mold_cost_db")
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"

print(f"[Database] 连接地址: postgresql+asyncpg://{user}:***@{host}:{port}/{dbname}")

# 创建异步引擎（优化连接池配置）
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 关闭SQL日志以提升性能
    pool_size=20,  # 连接池大小（保持20）
    max_overflow=40,  # 最大溢出连接数（从10增加到40）
    pool_timeout=30,  # 连接超时时间（秒）
    pool_recycle=3600,  # 连接回收时间（1小时）
    pool_pre_ping=True,  # 连接前检查是否有效
)

# 创建会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
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
