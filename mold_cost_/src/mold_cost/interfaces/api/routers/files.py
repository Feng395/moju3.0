"""文件管理路由。"""

from __future__ import annotations

import io
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from shared.timezone_utils import now_shanghai
from shared.unified_logging import get_logger

from ....core.settings import settings
from ..dependencies.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])


class PresignedUrlRequest(BaseModel):
    """预签名 URL 请求模型。"""

    file_path: str = Field(..., description="MinIO中的文件路径")
    expires_in: int = Field(..., description="URL过期时间（秒）", ge=60, le=604800)
    bucket_name: Optional[str] = Field(None, description="Bucket名称（可选）")
    download_filename: Optional[str] = Field(None, description="下载时的文件名（可选）")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, value: str):
        if ".." in value or value.startswith("/") or "\\" in value:
            raise ValueError("文件路径包含非法字符")
        if not value.strip():
            raise ValueError("文件路径不能为空")
        return value.strip()


class PresignedUrlResponse(BaseModel):
    success: bool = True
    data: dict


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    request: PresignedUrlRequest,
    current_user: dict = Depends(get_current_user),
):
    """生成 MinIO 文件的临时签名 URL。"""
    try:
        bucket_name = request.bucket_name or settings.MINIO_BUCKET_FILES
        logger.info(
            "生成预签名URL请求: user_id=%s, file_path=%s, expires_in=%ss, bucket=%s",
            current_user["user_id"],
            request.file_path,
            request.expires_in,
            bucket_name,
        )

        from ....infrastructure.storage.minio_client import minio_client

        try:
            minio_client.client.stat_object(bucket_name, request.file_path)
        except Exception as exc:
            logger.warning("文件可能不存在: %s, error=%s", request.file_path, exc)

        expires_delta = timedelta(seconds=request.expires_in)
        response_headers = {}
        if request.download_filename:
            response_headers["response-content-disposition"] = f'attachment; filename="{request.download_filename}"'

        if response_headers:
            url = minio_client.presigned_client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=request.file_path,
                expires=expires_delta,
                response_headers=response_headers,
            )
        else:
            url = minio_client.generate_presigned_url(
                object_name=request.file_path,
                expires=expires_delta,
                bucket=bucket_name,
            )

        expires_at = now_shanghai() + expires_delta
        return {
            "success": True,
            "data": {
                "url": url,
                "expires_at": expires_at.isoformat() + "Z",
                "expires_in": request.expires_in,
                "file_path": request.file_path,
                "bucket": bucket_name,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("生成预签名URL失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "URL_GENERATION_FAILED",
                    "message": f"生成预签名URL失败: {str(exc)}",
                },
            },
        ) from exc


@router.get("/proxy")
async def proxy_file(
    file_path: str,
    bucket_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """通过后端代理访问 MinIO 文件。"""
    try:
        if ".." in file_path or file_path.startswith("/") or "\\" in file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_PATH", "message": "文件路径包含非法字符"},
            )

        bucket = bucket_name or settings.MINIO_BUCKET_FILES
        logger.info("代理文件请求: %s, bucket=%s", file_path, bucket)

        from ....infrastructure.storage.minio_client import minio_client

        file_data = minio_client.get_file(file_path, bucket=bucket)

        content_type = "application/octet-stream"
        if file_path.endswith(".dxf"):
            content_type = "application/dxf"
        elif file_path.endswith(".dwg"):
            content_type = "application/acad"
        elif file_path.endswith(".json"):
            content_type = "application/json"

        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{file_path.split("/")[-1]}"',
                "Access-Control-Allow-Origin": "*",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("代理文件失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROXY_FAILED", "message": f"文件代理失败: {str(exc)}"},
        ) from exc


__all__ = ["router", "PresignedUrlRequest", "PresignedUrlResponse"]
