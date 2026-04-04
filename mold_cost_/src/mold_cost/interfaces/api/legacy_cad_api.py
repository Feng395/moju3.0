"""历史 CAD/特征识别独立服务的兼容 API。"""

from __future__ import annotations

import csv
import glob
import json
import os
import tempfile
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
            from mold_cost.domain.cad.services.split_service import cad_split_service

            # 中文注释：legacy 接口里虽然保留 prt_url 字段，但当前底层拆图服务未使用该字段。
            if request.prt_url:
                logger.info("legacy chaitu 请求携带 prt_url，当前兼容层仅保留参数，不参与底层调用")

            result = await cad_split_service.split(
                dwg_url=request.dwg_url,
                job_id=request.job_id,
            )
            if result.get("status") == "error":
                raise HTTPException(status_code=500, detail=result.get("message", "拆图失败"))
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
            if not result.get("success"):
                detail = result.get("message", "特征识别失败")
                if "未找到子图" in detail:
                    raise HTTPException(status_code=404, detail=detail)
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
        folder = os.path.abspath(request.csv_folder)
        if not os.path.isdir(folder):
            raise HTTPException(status_code=400, detail=f"文件夹不存在: {folder}")

        csv_path = _find_latest_feature_csv(folder)
        if csv_path is None:
            raise HTTPException(status_code=404, detail=f"未找到识别报告 CSV: {folder}")

        # 中文注释：这里保留旧接口能力，但内部实现收敛到兼容模块，避免继续散落在历史脚本中。
        database = _build_feature_database(csv_path)
        if not database:
            raise HTTPException(status_code=400, detail="CSV 中没有有效的红色面数据")

        minio_path = request.minio_path or os.getenv("SLIDER_FEATURE_DB_MINIO_PATH", "slider/feature_database.json")
        _upload_feature_database(database, minio_path)

        logger.info("特征库上传成功: %s, count=%s", minio_path, len(database))
        return {
            "success": True,
            "message": f"上传成功，共 {len(database)} 条记录",
            "minio_path": minio_path,
            "csv_source": csv_path,
        }

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


def _find_latest_feature_csv(folder: str) -> str | None:
    """查找最新的特征识别 CSV。"""
    pattern = os.path.join(folder, "特征面识别报告_增强特*.csv")
    csv_files = sorted(glob.glob(pattern), key=os.path.getmtime)
    return csv_files[-1] if csv_files else None


def _build_feature_database(csv_path: str) -> dict[str, Any]:
    """从 CSV 构建特征数据库内容。"""
    database: dict[str, Any] = {}
    with open(csv_path, "r", encoding="utf-8-sig") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            part_name = row.get("零件名", "").strip()
            if not part_name:
                continue
            if any("\u4e00" <= char <= "\u9fff" for char in part_name):
                continue

            red_count_str = row.get("红色面数量", "0").strip()
            area_str = row.get("总表面积(mm2)", "0").strip()
            red_count = int(red_count_str) if red_count_str.isdigit() else 0
            if red_count == 0:
                continue

            try:
                total_area = float(area_str)
            except ValueError:
                total_area = 0.0

            slider_result = row.get("识别结果", "").strip()
            code = "滑块" if slider_result not in ("", "未识别") else "none"
            database[part_name] = {
                "wire_cut_details": [
                    {
                        "code": code,
                        "cone": "f",
                        "view": "front_view",
                        "area_num": red_count,
                        "instruction": f"{red_count} -红色面",
                        "slider_angle": 0,
                        "total_length": round(total_area, 3),
                        "is_additional": False,
                        "matched_count": red_count,
                        "single_length": round(total_area / red_count, 3) if red_count else 0.0,
                        "expected_count": red_count,
                        "matched_line_ids": [],
                        "overlapping_length": 0.0,
                    }
                ]
            }
    return database


def _upload_feature_database(database: dict[str, Any], minio_path: str) -> None:
    """上传特征数据库到 MinIO，并清理缓存。"""
    from mold_cost.infrastructure.storage.minio_client import minio_client
    from scripts.feature_recognition.slider_red_face_lookup import invalidate_cache

    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8")
    try:
        json.dump(database, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()

        if not minio_client.upload_file_from_path(minio_path, temp_file.name, content_type="application/json"):
            raise RuntimeError("上传 MinIO 失败")

        invalidate_cache(minio_path)
    finally:
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass


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
