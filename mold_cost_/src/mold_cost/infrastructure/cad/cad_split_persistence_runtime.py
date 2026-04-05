"""CAD 拆图结果持久化 runtime。"""

from __future__ import annotations

from typing import Any

from ...core.logging import get_logger

logger = get_logger(__name__)


def persist_split_results(
    *,
    export_files: list[dict[str, Any]],
    upload_results: dict[str, dict[str, Any]],
    db_manager,
    source_filename: str,
    job_id: str,
    xt_url_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """根据上传结果筛选可入库子图，并统一完成 subgraphs 持久化。"""

    result_files: list[dict[str, Any]] = []
    db_success_count = 0
    failed_upload_count = 0
    failed_db_count = 0
    xt_url_map = xt_url_map or {}

    for file_info in export_files:
        sub_code = file_info["sub_code"]

        if sub_code not in upload_results or not upload_results[sub_code].get("success"):
            failed_upload_count += 1
            upload_error = upload_results.get(sub_code, {}).get("error", "未知错误")
            logger.warning("CAD split upload failed: sub_code=%s error=%s", sub_code, upload_error)
            continue

        try:
            save_success = db_manager.save_subgraph(
                sub_code,
                file_info["minio_path"],
                source_filename,
                job_id,
                file_info["part_name"],
                file_info.get("part_code"),
                xt_url_map.get(sub_code),
            )
            if not save_success:
                failed_db_count += 1
                logger.error("CAD split db save failed: sub_code=%s", sub_code)
                continue

            result_files.append(
                {
                    "path": file_info["minio_path"],
                    "filename": f"{sub_code}.dxf",
                    "sub_code": sub_code,
                    "source_file": source_filename,
                    "part_name": file_info["part_name"],
                    "part_code": file_info.get("part_code"),
                }
            )
            db_success_count += 1
        except Exception as exc:
            failed_db_count += 1
            logger.error("CAD split db persistence exception: sub_code=%s error=%s", sub_code, exc, exc_info=True)

    return {
        "result_files": result_files,
        "db_success_count": db_success_count,
        "failed_upload_count": failed_upload_count,
        "failed_db_count": failed_db_count,
    }
