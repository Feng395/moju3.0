"""
日志系统使用示例
演示各种日志功能的使用方法
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import uuid
from shared.logging_config import (
    setup_logging,
    get_logger,
    LogContext,
    PerformanceLogger,
    log_execution
)


# ========== 示例1：基础日志 ==========

def example_basic_logging():
    """基础日志示例"""
    logger = get_logger(__name__)
    
    print("\n" + "=" * 60)
    print("示例1：基础日志")
    print("=" * 60)
    
    logger.debug("🔍 这是调试信息")
    logger.info("✅ 这是普通信息")
    logger.warning("⚠️  这是警告信息")
    logger.error("❌ 这是错误信息")
    logger.critical("🔥 这是严重错误")


# ========== 示例2：日志上下文 ==========

def example_log_context():
    """日志上下文示例"""
    logger = get_logger(__name__)
    
    print("\n" + "=" * 60)
    print("示例2：日志上下文（trace_id）")
    print("=" * 60)
    
    # 模拟请求处理
    trace_id = str(uuid.uuid4())
    user_id = "user_001"
    job_id = "job_123"
    
    with LogContext(trace_id=trace_id, user_id=user_id, job_id=job_id):
        logger.info("📨 收到请求")
        logger.info("🔍 验证用户")
        logger.info("💾 保存数据")
        logger.info("✅ 请求处理完成")
    
    # 上下文外的日志不包含 trace_id
    logger.info("📊 统计信息")


# ========== 示例3：性能日志 ==========

async def example_performance_logging():
    """性能日志示例"""
    logger = get_logger(__name__)
    
    print("\n" + "=" * 60)
    print("示例3：性能日志")
    print("=" * 60)
    
    # 方式1：上下文管理器
    with PerformanceLogger("数据库查询", logger):
        await asyncio.sleep(0.5)  # 模拟数据库查询
    
    with PerformanceLogger("API 调用", logger):
        await asyncio.sleep(0.3)  # 模拟 API 调用


# ========== 示例4：装饰器 ==========

@log_execution()
async def process_data(data: dict):
    """使用装饰器自动记录执行时间"""
    await asyncio.sleep(0.2)
    return {"status": "ok", "data": data}


async def example_decorator():
    """装饰器示例"""
    print("\n" + "=" * 60)
    print("示例4：装饰器")
    print("=" * 60)
    
    result = await process_data({"key": "value"})
    print(f"结果: {result}")


# ========== 示例5：异常日志 ==========

def example_exception_logging():
    """异常日志示例"""
    logger = get_logger(__name__)
    
    print("\n" + "=" * 60)
    print("示例5：异常日志")
    print("=" * 60)
    
    try:
        # 模拟异常
        result = 1 / 0
    except Exception as e:
        # exc_info=True 会自动记录堆栈信息
        logger.error(f"❌ 计算失败: {e}", exc_info=True)


# ========== 示例6：结构化日志 ==========

def example_structured_logging():
    """结构化日志示例"""
    logger = get_logger(__name__)
    
    print("\n" + "=" * 60)
    print("示例6：结构化日志")
    print("=" * 60)
    
    # 添加额外的结构化数据
    logger.info(
        "用户登录",
        extra={
            "extra_data": {
                "user_id": "user_001",
                "ip": "192.168.1.100",
                "device": "mobile",
                "browser": "Chrome"
            }
        }
    )
    
    logger.info(
        "订单创建",
        extra={
            "extra_data": {
                "order_id": "order_123",
                "amount": 99.99,
                "items": 3
            }
        }
    )


# ========== 示例7：业务流程日志 ==========

async def example_business_flow():
    """业务流程日志示例"""
    logger = get_logger(__name__)
    
    print("\n" + "=" * 60)
    print("示例7：业务流程日志")
    print("=" * 60)
    
    trace_id = str(uuid.uuid4())
    
    with LogContext(trace_id=trace_id):
        logger.info("🚀 启动审核流程")
        
        with PerformanceLogger("查询数据", logger):
            await asyncio.sleep(0.3)
            logger.info("📊 查询到 100 条记录")
        
        with PerformanceLogger("数据验证", logger):
            await asyncio.sleep(0.2)
            logger.info("✅ 数据验证通过")
        
        with PerformanceLogger("保存结果", logger):
            await asyncio.sleep(0.1)
            logger.info("💾 结果已保存")
        
        logger.info("✅ 审核流程完成")


# ========== 主函数 ==========

async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("日志系统使用示例")
    print("=" * 60)
    
    # 初始化日志系统
    setup_logging(
        level="DEBUG",
        enable_console=True,
        enable_file=True,
        enable_json=False  # 开发环境不启用 JSON
    )
    
    # 运行示例
    example_basic_logging()
    example_log_context()
    await example_performance_logging()
    await example_decorator()
    example_exception_logging()
    example_structured_logging()
    await example_business_flow()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成")
    print("=" * 60)
    print("\n查看日志文件:")
    print("  - logs/app.log (所有日志)")
    print("  - logs/error.log (错误日志)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
