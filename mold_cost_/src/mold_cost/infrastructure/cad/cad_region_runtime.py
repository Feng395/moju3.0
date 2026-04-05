"""CAD 子图识别与导出计划 runtime。"""

from __future__ import annotations

import os
from typing import Any, Callable

from ...core.logging import get_logger

logger = get_logger(__name__)

RegionInfoResolver = Callable[[str, dict[str, Any]], tuple[str | None, str | None, str | None]]


def resolve_region_infos(
    *,
    all_regions: list[tuple[str, dict[str, Any]]],
    resolver: RegionInfoResolver,
) -> dict[str, Any]:
    """解析子图的编号、品名与零件编号，并处理重复 sub_code。"""

    region_info_list: list[dict[str, Any]] = []
    failed_recognition_count = 0
    used_sub_codes: dict[str, int] = {}

    for index, (region_id, region) in enumerate(all_regions, 1):
        try:
            sub_code, part_name, part_code = resolver(region_id, region)
            if not part_name:
                part_name = "未识别"
            if not part_code:
                part_code = region_id

            base_code = part_code if not sub_code or sub_code == region_id else sub_code
            if base_code in used_sub_codes:
                suffix = chr(ord("A") + used_sub_codes[base_code] - 1)
                final_sub_code = f"{base_code}{suffix}"
                used_sub_codes[base_code] += 1
                logger.info("CAD region runtime duplicate sub_code detected: %s -> %s", base_code, final_sub_code)
            else:
                final_sub_code = base_code
                used_sub_codes[base_code] = 1

            region_info_list.append(
                {
                    "region_id": region_id,
                    "region": region,
                    "sub_code": final_sub_code,
                    "part_name": part_name,
                    "part_code": part_code,
                    "index": index,
                }
            )
        except Exception as exc:
            failed_recognition_count += 1
            logger.error("CAD region runtime resolve failed: index=%s region_id=%s error=%s", index, region_id, exc)

    return {
        "region_info_list": region_info_list,
        "failed_recognition_count": failed_recognition_count,
        "region_info_map": {info["sub_code"]: info for info in region_info_list},
    }


def build_batch_export_list(*, region_info_list: list[dict[str, Any]], temp_dir: str) -> list[dict[str, Any]]:
    """根据 region_info 组装 batch export 参数。"""

    return [
        {
            "sub_code": info["sub_code"],
            "region": info["region"],
            "output_path": os.path.join(temp_dir, f"output_{info['sub_code']}.dxf"),
        }
        for info in region_info_list
    ]


def collect_export_files(
    *,
    region_info_list: list[dict[str, Any]],
    export_results: list[dict[str, Any]],
    minio_base_path: str,
) -> dict[str, Any]:
    """把导出结果归一化为后续上传/持久化阶段消费的文件清单。"""

    export_files: list[dict[str, Any]] = []
    failed_export_count = 0

    for info, result in zip(region_info_list, export_results):
        if result.get("success"):
            export_files.append(
                {
                    "sub_code": result["sub_code"],
                    "part_name": info["part_name"],
                    "part_code": info.get("part_code"),
                    "local_path": result["output_path"],
                    "minio_path": f"{minio_base_path}/{result['sub_code']}.dxf",
                    "index": info["index"],
                }
            )
            continue

        failed_export_count += 1
        logger.warning(
            "CAD region runtime export failed: sub_code=%s error=%s",
            result.get("sub_code"),
            result.get("error", "未知错误"),
        )

    return {
        "export_files": export_files,
        "failed_export_count": failed_export_count,
    }
