"""历史 CAD/特征识别独立服务的兼容 API。"""

from __future__ import annotations

import os
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from ...core.logging import get_logger

logger = get_logger(__name__)


class ChaiTuRequest(BaseModel):
    """拆图请求。"""

    dwg_url: Optional[str] = None
    prt_url: Optional[str] = None
    job_id: str


class ChaiTuResponse(BaseModel):
    """拆图响应。"""

    status: str
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class FeatureRecognitionRequest(BaseModel):
    """特征识别请求。"""

    job_id: str
    subgraph_id: Optional[str] = None


class FeatureRecognitionResponse(BaseModel):
    """特征识别响应。"""

    success: bool
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class UploadFeatureDbRequest(BaseModel):
    """上传滑块特征库请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "csv_folder": r"D:\demo\split_result",
                "minio_path": "slider/feature_database.json",
            }
        }
    )

    csv_folder: str
    minio_path: Optional[str] = None


def create_app() -> FastAPI:
    """创建兼容 FastAPI 应用。"""
    app = FastAPI(
        title="CAD Legacy Compatibility API",
        version="2.0.0",
        description="为历史 unified_api.py 提供的兼容服务入口。",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/api/chaitu", response_model=ChaiTuResponse, tags=["拆图服务"])
    async def chaitu_api(request: ChaiTuRequest):
        """兼容旧拆图接口。"""
        try:
            from mold_cost.domain.cad.services import cad_split_service

            # 中文注释：legacy 接口里虽然保留 prt_url 字段，但当前底层拆图服务未使用该字段。
            if request.prt_url:
                logger.info("legacy chaitu 请求携带 prt_url，当前兼容层仅保留参数，不参与底层调用")

            result = await cad_split_service.split(
                dwg_url=request.dwg_url,
                job_id=request.job_id,
            )
            if result.get("status") == "error":
                error = result.get("error") or {}
                status_code = 400 if error.get("code") == "MISSING_JOB_ID" else 500
                raise HTTPException(status_code=status_code, detail=error.get("message", result.get("message", "拆图失败")))
            return ChaiTuResponse(**result)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("legacy chaitu 接口异常: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/chaitu/health", tags=["拆图服务"])
    async def chaitu_health():
        """拆图服务健康检查。"""
        return {
            "service": "拆图服务",
            "status": "healthy",
            "available": True,
        }

    @app.post("/api/feature-recognition/batch", response_model=FeatureRecognitionResponse, tags=["特征识别服务"])
    async def feature_recognition_batch_api(request: FeatureRecognitionRequest):
        """兼容旧特征识别批处理接口。"""
        try:
            from mold_cost.domain.features.services import feature_recognition_service

            result = feature_recognition_service.batch_recognize(
                job_id=request.job_id,
                subgraph_id=request.subgraph_id,
            )
            if result.get("status") == "error" or not result.get("success"):
                error = result.get("error") or {}
                detail = error.get("message", result.get("message", "特征识别失败"))
                if error.get("code") == "SUBGRAPHS_NOT_FOUND" or "未找到子图" in detail:
                    raise HTTPException(status_code=404, detail=detail)
                if error.get("code") == "MISSING_JOB_ID":
                    raise HTTPException(status_code=400, detail=detail)
                raise HTTPException(status_code=500, detail=detail)
            return FeatureRecognitionResponse(**result)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("legacy feature 接口异常: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/feature-recognition/health", tags=["特征识别服务"])
    async def feature_recognition_health():
        """特征识别服务健康检查。"""
        return {
            "service": "特征识别服务",
            "status": "healthy",
            "available": True,
        }

    @app.post("/api/feature-recognition/upload-feature-db", tags=["特征识别服务"])
    async def upload_feature_db_api(request: UploadFeatureDbRequest):
        """兼容旧滑块特征库上传接口。"""
        try:
            from mold_cost.domain.features.services import feature_recognition_service

            # 中文说明：legacy 上传入口继续保留，但真正逻辑统一收口到领域服务。
            return feature_recognition_service.upload_feature_database(
                csv_folder=request.csv_folder,
                minio_path=request.minio_path,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("legacy feature upload 接口异常: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/", tags=["通用"])
    async def root():
        """根路由。"""
        return {
            "service": "CAD Legacy Compatibility API",
            "version": "2.0.0",
            "services": {
                "chaitu": {
                    "available": True,
                    "endpoints": [
                        "POST /api/chaitu",
                        "GET /api/chaitu/health",
                    ],
                },
                "feature_recognition": {
                    "available": True,
                    "endpoints": [
                        "POST /api/feature-recognition/batch",
                        "GET /api/feature-recognition/health",
                        "POST /api/feature-recognition/upload-feature-db",
                    ],
                },
            },
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", tags=["通用"])
    async def health():
        """统一健康检查。"""
        return {
            "status": "healthy",
            "service": "CAD Legacy Compatibility API",
            "services": {
                "chaitu": "available",
                "feature_recognition": "available",
            },
        }

    return app

def run(module_name: str = "unified_api:app") -> None:
    """运行兼容 API 服务。"""
    host = os.getenv("CAD_SERVER_HOST", os.getenv("API_HOST", "0.0.0.0"))
    port = int(os.getenv("CAD_SERVER_PORT", os.getenv("API_PORT", "8200")))
    reload_enabled = os.getenv("API_RELOAD", "false").lower() == "true"
    workers = int(os.getenv("API_WORKERS", "1"))

    logger.info("启动 legacy compatibility API: host=%s port=%s reload=%s workers=%s", host, port, reload_enabled, workers)
    uvicorn.run(
        module_name,
        host=host,
        port=port,
        reload=reload_enabled,
        workers=1 if reload_enabled else workers,
    )


app = create_app()
