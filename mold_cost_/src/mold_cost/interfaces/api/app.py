"""API 接口层主入口。"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from refactor_bootstrap import ensure_src_path

from ...core.logging import get_logger
from ...core.settings import settings
from ...infrastructure.messaging.rabbitmq_client import rabbitmq_client
from ...infrastructure.messaging.redis_client import redis_client
from ...infrastructure.review.action_handler_runtime import initialize_review_action_handlers
from .routers import files, jobs
from .websocket_runtime import manager

ensure_src_path()

load_dotenv()

from shared.logging_config import setup_logging  # noqa: E402
from shared.logging_middleware import LoggingMiddleware  # noqa: E402

setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    enable_console=True,
    enable_file=True,
    enable_module_logs=True,
    enable_json=os.getenv("ENABLE_JSON_LOG", "false").lower() == "true",
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage external connections used by the API process."""
    logger.info("API application starting")

    try:
        await rabbitmq_client.connect()
        logger.info("RabbitMQ connected")
    except Exception as exc:
        logger.error("RabbitMQ connection failed: %s", exc, exc_info=True)

    try:
        await redis_client.connect()
        logger.info("Redis connected")
    except Exception as exc:
        logger.error("Redis connection failed: %s", exc, exc_info=True)

    try:
        initialize_review_action_handlers()
        logger.info("Action handler factory initialized")
    except Exception as exc:
        logger.error("Action handler factory initialization failed: %s", exc, exc_info=True)

    try:
        manager.subscriber_task = asyncio.create_task(manager.start_redis_subscriber())
        logger.info("WebSocket Redis subscriber started")
    except Exception as exc:
        logger.error("WebSocket Redis subscriber startup failed: %s", exc, exc_info=True)

    yield

    logger.info("API application shutting down")

    try:
        if manager.subscriber_task:
            manager.subscriber_task.cancel()
            try:
                await manager.subscriber_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket Redis subscriber stopped")
    except Exception as exc:
        logger.error("Failed to stop WebSocket Redis subscriber: %s", exc, exc_info=True)

    try:
        await redis_client.close()
    except Exception as exc:
        logger.error("Redis shutdown failed: %s", exc, exc_info=True)

    try:
        await rabbitmq_client.close()
    except Exception as exc:
        logger.error("RabbitMQ shutdown failed: %s", exc, exc_info=True)

    logger.info("API application closed")


app = FastAPI(
    title="模具成本核算系统 API",
    version="2.1.0",
    description="基于AI Agent的模具成本核算系统",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else None,
        },
    )


app.include_router(jobs.router)
app.include_router(jobs.router_legacy)
app.include_router(files.router)

router_v1_jobs = APIRouter(prefix="/api/v1")
router_v1_jobs.include_router(jobs.router)
app.include_router(router_v1_jobs)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Mold Cost System API Gateway",
        "version": "2.1.0",
        "status": "running",
        "endpoints": {
            "jobs": "/jobs",
            "api_jobs": "/api/jobs",
            "v1_jobs": "/api/v1/jobs",
            "files": "/api/v1/files",
            "docs": "/docs",
            "health": "/health",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def get_app():
    """Return the singleton application instance."""
    return app


__all__ = ["app", "get_app"]
