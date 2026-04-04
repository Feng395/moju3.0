"""Compatibility wrapper for the refactored MinIO client."""

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.storage.minio_client import (
    MinIOClient,
    get_file_url,
    minio_client,
    upload_file_to_minio,
)

__all__ = ["MinIOClient", "get_file_url", "minio_client", "upload_file_to_minio"]
