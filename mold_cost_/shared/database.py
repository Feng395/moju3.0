"""
数据库连接模块
负责人：人员A
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 从环境变量构造数据库URL
DB_HOST = os.getenv("DB_HOST", "192.168.1.54")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mold_cost_db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "yunzai123")
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 改为False，减少日志
    pool_size=10,  # 减少连接池大小
    max_overflow=5,  # 减少最大溢出
    pool_pre_ping=True,  # 添加：连接前先ping，确保连接有效
    pool_recycle=3600,  # 添加：1小时后回收连接
)

# 创建会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # 添加：禁用自动flush
    autocommit=False  # 添加：禁用自动提交
)

# 创建Base类
Base = declarative_base()

async def get_db():
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session
