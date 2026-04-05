"""CAD 拆图上传 runtime。"""

from __future__ import annotations

from typing import Any

from ...core.logging import get_logger

logger = get_logger(__name__)


def upload_split_files(*, export_files: list[dict[str, Any]], minio_client) -> dict[str, dict[str, Any]]:
    """批量上传拆图结果到 MinIO，并统一返回按 sub_code 索引的结果。"""

    if minio_client is None:
        logger.error("CAD upload runtime missing minio_client")
        return {}

    upload_list = [
        (file_info["sub_code"], file_info["local_path"], file_info["minio_path"])
        for file_info in export_files
    ]
    if not upload_list:
        return {}

    return minio_client.batch_upload_files(upload_list)
