"""CAD 子图识别与导出编排 runtime。"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from ...core.logging import get_logger
from .cad_region_runtime import build_batch_export_list, collect_export_files, resolve_region_infos

logger = get_logger(__name__)


def analyze_and_export_subgraphs(
    *,
    analysis_system,
    temp_dxf: str,
    temp_dir: str,
    minio_base_path: str,
) -> dict[str, Any]:
    """组织 CAD 子图识别、编号解析与批量导出，但不改动底层 analyzer/export 算法。"""

    logger.info("步骤1: 开始识别所有子图...")
    analysis_start = datetime.now()
    all_regions: list[tuple[str, dict[str, Any]]] = []
    for region_id, region, index, total in analysis_system.analyzer.analyze_cad_file_streaming(temp_dxf):
        if index == 1:
            logger.info("CAD analysis runtime detected %s subgraphs", total)
        all_regions.append((region_id, region))

    analysis_time = (datetime.now() - analysis_start).total_seconds()
    if not all_regions:
        return {"success": False, "message": "未识别到任何子图", "analysis_time": analysis_time}

    logger.info("步骤2: 识别各子图的编号、品名和编号...")
    region_resolution = resolve_region_infos(
        all_regions=all_regions,
        resolver=analysis_system.analyzer.resolve_region_info,
    )
    region_info_list = region_resolution["region_info_list"]
    failed_recognition_count = region_resolution["failed_recognition_count"]
    if not region_info_list:
        return {
            "success": False,
            "message": "所有子图的编号和品名识别失败",
            "analysis_time": analysis_time,
            "all_regions": all_regions,
            "failed_recognition_count": failed_recognition_count,
        }

    logger.info("步骤3: 开始导出所有子图...")
    export_start = datetime.now()
    batch_export_list = build_batch_export_list(
        region_info_list=region_info_list,
        temp_dir=temp_dir,
    )
    max_workers = int(os.getenv("EXPORT_WORKERS", "5"))
    export_results = analysis_system.batch_export_regions_concurrent(
        batch_export_list,
        pad=0.0,
        horizontal_spacing=50.0,
        align_to_origin=True,
        max_workers=max_workers,
    )
    export_summary = collect_export_files(
        region_info_list=region_info_list,
        export_results=export_results,
        minio_base_path=minio_base_path,
    )
    export_files = export_summary["export_files"]
    failed_export_count = export_summary["failed_export_count"]
    export_time = (datetime.now() - export_start).total_seconds()
    if not export_files:
        return {
            "success": False,
            "message": "所有子图导出失败",
            "analysis_time": analysis_time,
            "export_time": export_time,
            "all_regions": all_regions,
            "region_info_list": region_info_list,
            "failed_recognition_count": failed_recognition_count,
            "failed_export_count": failed_export_count,
        }

    return {
        "success": True,
        "analysis_time": analysis_time,
        "export_time": export_time,
        "all_regions": all_regions,
        "region_info_list": region_info_list,
        "region_info_map": region_resolution["region_info_map"],
        "failed_recognition_count": failed_recognition_count,
        "failed_export_count": failed_export_count,
        "export_files": export_files,
    }
