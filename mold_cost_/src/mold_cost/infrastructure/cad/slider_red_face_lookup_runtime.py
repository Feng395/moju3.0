"""滑块红色面查表 runtime。"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from ...core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_MINIO_PATH = os.getenv("SLIDER_FEATURE_DB_MINIO_PATH", "slider/feature_database.json")
_DB_CACHE: dict[str, dict[str, Any]] = {}


def _parse_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """兼容历史两种 feature_database.json 格式，并统一为 wire_cut_details 结构。"""

    normalized: dict[str, Any] = {}
    first_val = next(iter(raw.values()), None) if raw else None
    if isinstance(first_val, dict) and "wire_cut_details" in first_val:
        for code, data in raw.items():
            normalized[code.lower()] = data
        return normalized

    for code, data in raw.get("sliders", {}).items():
        face_count = data.get("feature_face_count", 0)
        faces = data.get("feature_faces", [])
        total_area = round(sum(face.get("area", 0.0) for face in faces), 3)
        single_area = round(total_area / face_count, 3) if face_count else 0.0
        normalized[code.lower()] = {
            "wire_cut_details": [
                {
                    "code": "滑块",
                    "cone": "f",
                    "view": "front_view",
                    "area_num": face_count,
                    "instruction": f"{face_count} -红色面",
                    "slider_angle": 0,
                    "total_length": total_area,
                    "is_additional": False,
                    "matched_count": face_count,
                    "single_length": single_area,
                    "expected_count": face_count,
                    "matched_line_ids": [],
                    "overlapping_length": 0.0,
                }
            ]
        }
    return normalized


def _download_feature_db(minio_client, minio_path: str, save_path: str) -> bool:
    """兼容 src/legacy MinIO 客户端不同下载接口。"""

    if hasattr(minio_client, "download_file"):
        return bool(minio_client.download_file(minio_path, save_path))
    if hasattr(minio_client, "get_file"):
        return bool(minio_client.get_file(minio_path, save_path))
    raise AttributeError("minio_client does not support download_file/get_file")


def _load_from_minio(minio_path: str, minio_client) -> dict[str, Any]:
    """下载并缓存 feature_database.json。"""

    if minio_path in _DB_CACHE:
        return _DB_CACHE[minio_path]

    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    temp_file.close()
    try:
        if not _download_feature_db(minio_client, minio_path, temp_file.name):
            logger.warning("下载滑块红色面数据库失败: %s", minio_path)
            return {}

        with open(temp_file.name, "r", encoding="utf-8") as file:
            normalized = _parse_raw(json.load(file))
        _DB_CACHE[minio_path] = normalized
        return normalized
    except Exception as exc:
        logger.warning("加载滑块红色面数据库失败: path=%s error=%s", minio_path, exc)
        return {}
    finally:
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass


def _find_entry(db: dict[str, Any], part_code: str) -> dict[str, Any] | None:
    key = part_code.lower().strip()
    if key in db:
        return db[key]
    for db_key, value in db.items():
        if db_key.startswith(key) or key.startswith(db_key):
            return value
    return None


def apply_red_face_lookup(
    part_code: str,
    wire_cut_details: list[dict[str, Any]],
    *,
    minio_client=None,
    minio_db_path: str | None = None,
) -> list[dict[str, Any]]:
    """按零件号补齐滑块红色面信息。"""

    if not part_code or minio_client is None:
        return wire_cut_details

    db = _load_from_minio(minio_db_path or _DEFAULT_MINIO_PATH, minio_client)
    if not db:
        return wire_cut_details

    entry = _find_entry(db, part_code)
    if not entry:
        return wire_cut_details

    db_wire_cut_details = entry.get("wire_cut_details", [])
    if not db_wire_cut_details:
        return wire_cut_details

    slider_detail = db_wire_cut_details[0]
    area_num = slider_detail.get("area_num", 0)
    total_length = slider_detail.get("total_length", 0.0)
    single_length = slider_detail.get("single_length", 0.0)
    if area_num == 0:
        return wire_cut_details

    updated_details: list[dict[str, Any]] = []
    patched = False
    for detail in wire_cut_details:
        if "滑" not in str(detail.get("instruction", "")):
            updated_details.append(detail)
            continue

        patched = True
        new_detail = dict(detail)
        new_detail["code"] = "滑块"
        new_detail["view"] = "front_view"
        new_detail["area_num"] = area_num
        new_detail["total_length"] = total_length
        new_detail["single_length"] = single_length
        new_detail["matched_count"] = area_num
        new_detail["expected_count"] = area_num
        updated_details.append(new_detail)

    if patched:
        return updated_details

    return updated_details + [
        {
            "code": "滑块",
            "cone": "f",
            "view": "front_view",
            "area_num": area_num,
            "instruction": f"{area_num} -红色面",
            "slider_angle": 0,
            "total_length": total_length,
            "is_additional": True,
            "matched_count": area_num,
            "single_length": single_length,
            "expected_count": area_num,
            "matched_line_ids": [],
            "overlapping_length": 0.0,
        }
    ]


def invalidate_cache(minio_path: str | None = None) -> None:
    """清理进程内缓存，供上传新数据库后立即失效。"""

    if minio_path:
        _DB_CACHE.pop(minio_path, None)
        return
    _DB_CACHE.clear()
