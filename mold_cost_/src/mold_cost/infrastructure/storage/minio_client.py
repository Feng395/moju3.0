"""MinIO client used by the refactored package."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from ...core.logging import get_logger
from ...core.settings import settings

logger = get_logger(__name__)


class MinIOClient:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_HTTPS,
            region=settings.MINIO_REGION,
        )
        if settings.MINIO_EXTERNAL_ENDPOINT and settings.MINIO_EXTERNAL_ENDPOINT != settings.MINIO_ENDPOINT:
            self.presigned_client = Minio(
                endpoint=settings.MINIO_EXTERNAL_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_HTTPS,
                region=settings.MINIO_REGION,
            )
        else:
            self.presigned_client = self.client
        self.bucket_files = settings.MINIO_BUCKET_FILES
        self._ensure_buckets()

    def _ensure_buckets(self):
        try:
            if not self.client.bucket_exists(self.bucket_files):
                self.client.make_bucket(self.bucket_files)
        except S3Error as exc:
            logger.error("failed to ensure MinIO bucket: %s", exc)
            raise

    async def upload_file(self, file: UploadFile, prefix: str = "files") -> dict[str, str | int]:
        try:
            file_id = str(uuid.uuid4())
            now = datetime.now()
            suffix = Path(file.filename).suffix.lower()
            object_name = f"{prefix}/{now.year}/{now.month:02d}/{file_id}{suffix}"
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            result = self.client.put_object(
                bucket_name=self.bucket_files,
                object_name=object_name,
                data=file.file,
                length=file_size,
                content_type=file.content_type or "application/octet-stream",
            )
            return {
                "file_id": file_id,
                "object_name": object_name,
                "file_path": object_name,
                "file_size": file_size,
                "etag": result.etag,
                "bucket": self.bucket_files,
                "original_filename": file.filename,
            }
        except Exception as exc:
            logger.error("failed to upload file: %s", exc)
            raise

    def get_file(self, object_name: str, bucket: Optional[str] = None) -> bytes:
        bucket_name = bucket or self.bucket_files
        response = self.client.get_object(bucket_name, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_file_stream(self, object_name: str, bucket: Optional[str] = None):
        return self.client.get_object(bucket or self.bucket_files, object_name)

    def delete_file(self, object_name: str, bucket: Optional[str] = None):
        self.client.remove_object(bucket or self.bucket_files, object_name)

    def generate_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=24),
        bucket: Optional[str] = None,
    ) -> str:
        return self.presigned_client.presigned_get_object(
            bucket_name=bucket or self.bucket_files,
            object_name=object_name,
            expires=expires,
        )

    def download_file(self, object_name: str, local_path: str, bucket: Optional[str] = None) -> bool:
        try:
            self.client.fget_object(bucket or self.bucket_files, object_name, local_path)
            return True
        except S3Error as exc:
            logger.error("failed to download file %s: %s", object_name, exc)
            return False

    def upload_file_from_path(
        self,
        object_name: str,
        local_path: str,
        content_type: str | None = None,
        bucket: Optional[str] = None,
    ) -> bool:
        try:
            self.client.fput_object(
                bucket or self.bucket_files,
                object_name,
                local_path,
                content_type=content_type,
            )
            return True
        except S3Error as exc:
            logger.error("failed to upload path %s: %s", local_path, exc)
            return False

    def upload_bytes(
        self,
        object_name: str,
        file_content: bytes,
        content_type: str | None = None,
        bucket: Optional[str] = None,
    ) -> bool:
        try:
            self.client.put_object(
                bucket or self.bucket_files,
                object_name,
                io.BytesIO(file_content),
                length=len(file_content),
                content_type=content_type,
            )
            return True
        except S3Error as exc:
            logger.error("failed to upload bytes to %s: %s", object_name, exc)
            return False

    def file_exists(self, object_name: str, bucket: Optional[str] = None) -> bool:
        try:
            self.client.stat_object(bucket or self.bucket_files, object_name)
            return True
        except S3Error:
            return False

    def get_file_info(self, object_name: str, bucket: Optional[str] = None) -> Optional[dict]:
        try:
            stat = self.client.stat_object(bucket or self.bucket_files, object_name)
            return {
                "size": stat.size,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "etag": stat.etag,
                "bucket": bucket or self.bucket_files,
                "object_name": object_name,
            }
        except S3Error as exc:
            logger.error("failed to stat object %s: %s", object_name, exc)
            return None

    def list_files(self, prefix: str = "", recursive: bool = False, bucket: Optional[str] = None) -> list[dict]:
        try:
            objects = self.client.list_objects(bucket or self.bucket_files, prefix=prefix, recursive=recursive)
            return [
                {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                }
                for obj in objects
            ]
        except S3Error as exc:
            logger.error("failed to list objects: %s", exc)
            return []


minio_client = MinIOClient()


def upload_file_to_minio(bucket_name: str, object_name: str, file_data, content_type: str | None = None) -> bool:
    try:
        if not minio_client.client.bucket_exists(bucket_name):
            minio_client.client.make_bucket(bucket_name)
        if isinstance(file_data, bytes):
            stream = io.BytesIO(file_data)
            size = len(file_data)
        elif hasattr(file_data, "read"):
            file_data.seek(0)
            payload = file_data.read()
            stream = io.BytesIO(payload)
            size = len(payload)
        else:
            raise ValueError("file_data must be bytes or a file-like object")
        minio_client.client.put_object(bucket_name, object_name, stream, length=size, content_type=content_type)
        return True
    except Exception as exc:
        logger.error("failed to upload %s to MinIO: %s", object_name, exc)
        return False


def get_file_url(bucket_name: str, object_name: str, expires: int = 3600) -> Optional[str]:
    try:
        return minio_client.presigned_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=timedelta(seconds=expires),
        )
    except Exception as exc:
        logger.error("failed to build presigned url for %s: %s", object_name, exc)
        return None
