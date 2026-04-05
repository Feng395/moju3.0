"""CAD 拆图 .x_t 导出 runtime。"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable

from ...core.logging import get_logger

logger = get_logger(__name__)

XtExporter = Callable[..., dict[str, str]]
NxImporter = Callable[[], Any]
MinioPathDetector = Callable[[str | None], bool]


def _default_is_probable_minio_object_path(path: str | None) -> bool:
    if not path or not isinstance(path, str):
        return False

    normalized = path.strip().replace("\\", "/")
    if not normalized or normalized.startswith(("http://", "https://")):
        return False
    if os.path.isabs(path):
        return False

    first_segment = normalized.split("/", 1)[0].lower()
    return first_segment in {"dwg", "prt", "dxf", "xt", "uploads", "files"}


def _default_nx_importer():
    import NXOpen  # noqa: F401

    return NXOpen


async def export_xt_files(
    *,
    job_id: str,
    temp_dir: str,
    export_files: list[dict[str, Any]],
    storage_manager,
    db_manager,
    minio_client,
    export_xt_from_prt: XtExporter,
    nx_importer: NxImporter | None = None,
    is_probable_minio_object_path: MinioPathDetector | None = None,
) -> dict[str, str]:
    """在 NX 环境可用时，从 PRT 导出子图 .x_t 并上传。"""

    if not export_files or minio_client is None:
        return {}

    try:
        (nx_importer or _default_nx_importer)()
    except ImportError:
        logger.info("步骤6: 非 NX 环境，跳过 .x_t 导出")
        return {}
    except Exception as exc:
        logger.warning("步骤6 NX 环境检测异常（不影响主流程）: %s", exc)
        return {}

    prt_source = db_manager.get_prt_file_path(job_id)
    if not prt_source:
        logger.info("步骤6: 未提供 PRT 文件，跳过 .x_t 导出")
        return {}

    should_use_minio = (is_probable_minio_object_path or _default_is_probable_minio_object_path)(prt_source)
    prt_local = os.path.join(temp_dir, "source.prt")
    prt_ok = await storage_manager.get_file(prt_source, prt_local, use_minio=should_use_minio)
    if not prt_ok:
        logger.warning("步骤6: 下载 PRT 文件失败: %s，跳过 .x_t 导出", prt_source)
        return {}

    timestamp = datetime.now()
    xt_minio_base = f"xt/{timestamp:%Y}/{timestamp:%m}/{job_id}"
    logger.info("步骤6: 检测到 NX 环境，开始从 PRT 导出 .x_t 文件: %s", prt_source)
    return export_xt_from_prt(
        prt_local=prt_local,
        export_files=export_files,
        temp_dir=temp_dir,
        xt_minio_base=xt_minio_base,
        minio_client=minio_client,
    )
