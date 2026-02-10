"""
修复快丝工艺代码映射

问题：
- 数据库中 price_items 表存储的是 fast_and_one
- 代码中使用的是 fast_cut
- 导致工艺修改时使用了错误的代码

解决方案：
将数据库中的 fast_and_one 统一改为 fast_cut

影响范围：
1. price_items 表的 sub_category 字段
2. subgraphs 表的 wire_process 字段（如果有的话）
"""
import asyncio
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from shared.models import PriceItem, Subgraph
from infrastructure.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_fast_cut_mapping():
    """修复快丝工艺代码映射"""
    
    # 创建数据库引擎
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        pool_pre_ping=True
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # 1. 修复 price_items 表
            logger.info("🔧 修复 price_items 表...")
            
            stmt = update(PriceItem).where(
                PriceItem.sub_category == "fast_and_one"
            ).values(
                sub_category="fast_cut"
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            logger.info(f"✅ price_items 表修复完成: {result.rowcount} 条记录")
            
            # 2. 修复 subgraphs 表
            logger.info("🔧 修复 subgraphs 表...")
            
            stmt = update(Subgraph).where(
                Subgraph.wire_process == "fast_and_one"
            ).values(
                wire_process="fast_cut"
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            logger.info(f"✅ subgraphs 表修复完成: {result.rowcount} 条记录")
            
            # 3. 验证修复结果
            logger.info("🔍 验证修复结果...")
            
            # 检查 price_items
            stmt = select(PriceItem).where(
                PriceItem.category == "wire",
                PriceItem.note.ilike("%快丝%")
            )
            result = await session.execute(stmt)
            items = result.scalars().all()
            
            for item in items:
                logger.info(f"  price_items: id={item.id}, sub_category={item.sub_category}, note={item.note}")
            
            # 检查 subgraphs
            stmt = select(Subgraph).where(
                Subgraph.wire_process == "fast_cut"
            ).limit(5)
            result = await session.execute(stmt)
            subgraphs = result.scalars().all()
            
            logger.info(f"  subgraphs: {len(subgraphs)} 条记录使用 fast_cut")
            
            logger.info("✅ 修复完成！")
            
        except Exception as e:
            logger.error(f"❌ 修复失败: {e}", exc_info=True)
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_fast_cut_mapping())
