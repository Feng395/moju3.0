"""
=== 文件合并信息 ===
合并日期: 2026-02-10
源文件: mold_cost-main/shared/database.py + mold_cost_/shared/database.py
合并策略: 使用 mold_cost-main 为基础，补充 mold_cost_ 的会话配置
主要改动:
  1. 保留 mold_cost-main 的灵活配置方式（支持 DATABASE_URL 或分开配置）
  2. 保留 mold_cost-main 的大连接池配置（pool_size=20, max_overflow=40）
  3. 补充 mold_cost_ 的 autoflush=False 和 autocommit=False
  4. 保留 mold_cost-main 的错误处理（try-finally）
说明: 数据库连接模块，支持异步连接池和会话管理
=====================

数据库连接模块
负责人：人员A
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
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
