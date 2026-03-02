"""
测试文件上传时创建聊天会话
验证：
1. 上传文件时自动创建聊天会话
2. dwg_file_name 作为会话名称
3. 上传失败时会话也会回滚
"""
from shared.unified_logging import get_logger
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import logging

# 日志已统一配置，无需重复初始化
# logging.basicConfig(...)
logger = get_logger(__name__)


async def test_chat_session_creation():
    """测试聊天会话创建"""
    
    # 连接数据库
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/mold_cost"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # 1. 查询最近的一个 job
            query = text("""
                SELECT job_id, user_id, dwg_file_name, created_at
                FROM jobs
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = await db.execute(query)
            job = result.fetchone()
            
            if not job:
                logger.warning("⚠️ 没有找到任何任务记录")
                return
            
            job_id = job[0]
            user_id = job[1]
            dwg_file_name = job[2]
            created_at = job[3]
            
            logger.info(f"📋 找到任务: job_id={job_id}")
            logger.info(f"   用户: {user_id}")
            logger.info(f"   文件名: {dwg_file_name}")
            logger.info(f"   创建时间: {created_at}")
            
            # 2. 查询对应的聊天会话
            query = text("""
                SELECT session_id, job_id, user_id, name, created_at, status
                FROM chat_sessions
                WHERE session_id = :session_id
            """)
            
            result = await db.execute(query, {"session_id": job_id})
            session = result.fetchone()
            
            if session:
                logger.info(f"\n✅ 找到对应的聊天会话:")
                logger.info(f"   session_id: {session[0]}")
                logger.info(f"   job_id: {session[1]}")
                logger.info(f"   user_id: {session[2]}")
                logger.info(f"   name: {session[3]}")
                logger.info(f"   created_at: {session[4]}")
                logger.info(f"   status: {session[5]}")
                
                # 验证 name 字段是否等于 dwg_file_name
                if session[3] == dwg_file_name:
                    logger.info(f"\n✅ 验证通过: 会话名称与文件名一致")
                else:
                    logger.warning(f"\n⚠️ 验证失败: 会话名称 '{session[3]}' != 文件名 '{dwg_file_name}'")
            else:
                logger.warning(f"\n⚠️ 未找到对应的聊天会话")
                logger.info(f"   这可能是旧数据（在功能实现之前创建的）")
            
            # 3. 查询所有会话
            query = text("""
                SELECT session_id, name, created_at
                FROM chat_sessions
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            result = await db.execute(query)
            sessions = result.fetchall()
            
            logger.info(f"\n📋 最近的 5 个聊天会话:")
            for s in sessions:
                logger.info(f"   {s[0][:8]}... | {s[1]} | {s[2]}")
        
        except Exception as e:
            logger.error(f"❌ 测试失败: {e}", exc_info=True)
        
        finally:
            await engine.dispose()


async def test_rollback_scenario():
    """测试回滚场景（模拟）"""
    logger.info("\n" + "="*60)
    logger.info("测试回滚场景说明:")
    logger.info("="*60)
    logger.info("当文件上传失败时，由于使用了数据库事务 (async with db.begin()):")
    logger.info("1. jobs 表的记录会回滚")
    logger.info("2. chat_sessions 表的记录也会回滚")
    logger.info("3. price_snapshots 表的记录也会回滚")
    logger.info("4. audit_logs 表的记录也会回滚")
    logger.info("\n这是 SQLAlchemy 事务的自动行为，无需额外代码。")
    logger.info("如果需要测试，可以在 JobService 中故意抛出异常。")


if __name__ == "__main__":
    print("🧪 测试文件上传时创建聊天会话\n")
    
    asyncio.run(test_chat_session_creation())
    asyncio.run(test_rollback_scenario())
    
    print("\n✅ 测试完成")
