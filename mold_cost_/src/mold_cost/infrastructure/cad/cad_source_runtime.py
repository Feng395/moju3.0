"""CAD 拆图输入源解析 runtime。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable


ModelCodeExtractor = Callable[[str], str | None]


def is_probable_minio_object_path(path: str | None) -> bool:
    """根据对象路径特征判断是否应走 MinIO 下载。"""

    if not path or not isinstance(path, str):
        return False

    normalized = path.strip().replace("\\", "/")
    if not normalized or normalized.startswith(("http://", "https://")):
        return False
    if os.path.isabs(path):
        return False

    first_segment = normalized.split("/", 1)[0].lower()
    return first_segment in {"dwg", "prt", "dxf", "xt", "uploads", "files"}


def resolve_dwg_source(
    *,
    dwg_url: str | None,
    job_id: str,
    db_manager,
    extract_model_code_from_source: ModelCodeExtractor,
) -> dict[str, Any] | None:
    """解析拆图主流程使用的 DWG 来源、文件名与 MinIO 模式。"""

    dwg_source = dwg_url
    use_minio = False

    if not dwg_source:
        dwg_source = db_manager.get_dwg_file_path(job_id)
        if not dwg_source:
            return None
        use_minio = True

    if not use_minio and is_probable_minio_object_path(dwg_source):
        use_minio = True

    if dwg_source.startswith(("http://", "https://")):
        url_filename = dwg_source.split("/")[-1]
    else:
        url_filename = Path(dwg_source).name

    source_filename = os.path.splitext(url_filename)[0]
    model_code = extract_model_code_from_source(dwg_source) or source_filename

    return {
        "dwg_source": dwg_source,
        "use_minio": use_minio,
        "url_filename": url_filename,
        "source_filename": source_filename,
        "model_code": model_code,
    }


def resolve_prt_source(*, job_id: str, db_manager) -> dict[str, Any] | None:
    """解析 `.x_t` 导出阶段使用的 PRT 来源。"""

    prt_source = db_manager.get_prt_file_path(job_id)
    if not prt_source:
        return None

    return {
        "prt_source": prt_source,
        "use_minio": is_probable_minio_object_path(prt_source),
    }
