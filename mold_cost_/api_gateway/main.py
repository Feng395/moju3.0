"""
API Gateway - 主入口
负责人：ZZH

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost_/api_gateway/main.py + mold_cost-main/api_gateway/main.py
- 合并策略：使用 mold_cost_ 为基础，补充 mold_cost-main 的路由
- 主要改动：
  1. 保留 mold_cost_ 的完整架构（生命周期管理、日志、中间件）
  2. 补充 mold_cost-main 的路由（features, pricing, reports）
  3. 统一路由注册和端点信息
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径（确保调试模式下也能找到 shared 模块）
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
import asyncio
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 加载环境变量 - 必须在最开始
load_dotenv()

# 🆕 使用统一日志系统
from shared.logging_config import setup_logging, get_logger

# 初始化日志系统
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    enable_console=True,
    enable_file=True,
    enable_json=os.getenv("ENABLE_JSON_LOG", "false").lower() == "true"
)

logger = get_logger(__name__)

# 降低 watchfiles 和 uvicorn 的日志级别（避免刷屏）
import logging
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

from .routers import jobs, websocket_router, interactions, review_router, chat_router, file_router
from .utils.rabbitmq_client import rabbitmq_client
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 应用启动中...")
    
    # 连接RabbitMQ
    try:
        await rabbitmq_client.connect()
        logger.info("✅ RabbitMQ连接成功")
    except Exception as e:
        logger.error(f"❌ RabbitMQ连接失败: {e}")
    
    # 连接Redis
    try:
        from .utils.redis_client import redis_client
        await redis_client.connect()
        logger.info("✅ Redis连接成功")
    except Exception as e:
        logger.error(f"❌ Redis连接失败: {e}")
    
    # 初始化 Handler 工厂
    try:
        from agents.action_handlers import ActionHandlerFactory
        ActionHandlerFactory.initialize_handlers()
        logger.info("✅ Handler 工厂初始化成功")
    except Exception as e:
        logger.error(f"❌ Handler 工厂初始化失败: {e}")
    
    # 启动Redis订阅器（后台任务）
    try:
        from .websocket import manager
        manager.subscriber_task = asyncio.create_task(
            manager.start_redis_subscriber()
        )
        logger.info("✅ Redis订阅器后台任务已启动")
    except Exception as e:
        logger.error(f"❌ Redis订阅器启动失败: {e}")
    
    yield
    
    # 关闭时
    logger.info("🛑 应用关闭中...")
    
    # 取消Redis订阅器任务
    try:
        from .websocket import manager
        if manager.subscriber_task:
            manager.subscriber_task.cancel()
            try:
                await manager.subscriber_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ Redis订阅器已停止")
    except Exception as e:
        logger.error(f"❌ 停止Redis订阅器失败: {e}")
    
    # 关闭Redis连接
    try:
        from .utils.redis_client import redis_client
        await redis_client.close()
    except Exception as e:
        logger.error(f"❌ 关闭Redis连接失败: {e}")
    
    # 关闭RabbitMQ连接
    await rabbitmq_client.close()
    
    logger.info("✅ 应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="模具成本核算系统 API",
    version="2.1.0",
    description="基于AI Agent的模具成本核算系统",
    lifespan=lifespan
)

# 添加日志中间件（在 CORS 之前）
from shared.logging_middleware import LoggingMiddleware
app.add_middleware(LoggingMiddleware)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"❌ 未捕获的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# 注册路由
from api_gateway.routers import features, pricing, jobs, reports, weight_price, websocket_router
from api_gateway.routers import interactions, review_router, chat_router, file_router
from api_gateway.routers.account import auth, process_rules, price_items, chat_sessions

# 业务路由
app.include_router(features.router)
app.include_router(pricing.router)
app.include_router(jobs.router)
app.include_router(jobs.router_legacy)  # 兼容旧版本路由
app.include_router(reports.router)
app.include_router(weight_price.router)  # 价格加权路由
app.include_router(websocket_router.router)  # WebSocket路由

# 交互路由
app.include_router(interactions.router)
app.include_router(review_router.router)
app.include_router(chat_router.router)
app.include_router(file_router.router)

# 账户系统路由
app.include_router(auth.router, prefix="/api", tags=["认证"])
app.include_router(process_rules.router, prefix="/api/process-rules", tags=["工艺规则"])
app.include_router(price_items.router, prefix="/api/price-items", tags=["价格项"])
app.include_router(chat_sessions.router, prefix="/api/chat-sessions", tags=["聊天会话"])

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Mold Cost System API Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "jobs": "/api/v1/jobs",
            "features": "/api/features",
            "pricing": "/api/pricing",
            "weight_price": "/api/price_wg",
            "reports": "/api/v1/reports",
            "interactions": "/api/interactions",
            "reviews": "/api/reviews",
            "chat": "/api/chat",
            "files": "/api/files",
            "websocket": "/ws/{job_id}",
            # 账户系统端点
            "auth": {
                "login": "/api/login",
                "verify_token": "/api/verify-token",
                "change_password": "/api/change-password"
            },
            "process_rules": "/api/process-rules",
            "price_items": "/api/price-items",
            "chat_sessions": "/api/chat-sessions",
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
