"""滑块红色面写回 runtime。"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any, Callable

from ...core.logging import get_logger
from ...core.settings import settings

logger = get_logger(__name__)

# 中文说明：这里与 legacy/NX 脚本保持同一套红色索引，避免识别口径漂移。
_NX_RED_COLORS = {6, 36, 186, 211}

ConnectFactory = Callable[[], Any]
RedFaceExtractor = Callable[[str], dict[str, Any] | None]


def _create_connection(db_config: dict[str, Any] | None = None):
    """按需创建 psycopg2 连接，默认回落到统一 settings。"""
    import psycopg2

    config = db_config or {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "user": settings.DB_USER,
        "password": settings.DB_PASSWORD,
        "database": settings.DB_NAME,
    }
    return psycopg2.connect(**config)


def _json_value(payload: Any):
    from psycopg2.extras import Json

    return Json(payload)


def _extract_red_face_stats_nxopen(xt_file_path: str) -> dict[str, Any] | None:
    """使用 NXOpen 提取 .x_t 文件中的红色面面积与数量。"""
    try:
        import NXOpen

        session = NXOpen.Session.GetSession()

        open_result = session.Parts.Open(xt_file_path)
        work_part = open_result[0] if isinstance(open_result, tuple) else open_result
        session.Parts.SetDisplay(work_part, False, False)
        session.Parts.SetWork(work_part)
        work_part = session.Parts.Work

        measure_mgr = work_part.MeasureManager
        units = work_part.UnitCollection
        area_unit = units.FindObject("SquareMilliMeter")
        length_unit = units.FindObject("MilliMeter")

        face_details: list[dict[str, Any]] = []
        total_area = 0.0

        for body in work_part.Bodies:
            for face in body.GetFaces():
                try:
                    if face.Color not in _NX_RED_COLORS:
                        continue

                    result = measure_mgr.NewFaceProperties(area_unit, length_unit, 0.01, [face])
                    area = round(result.Area, 3) if hasattr(result, "Area") else 0.0
                    perimeter = round(result.Perimeter, 3) if hasattr(result, "Perimeter") else 0.0
                    face_details.append(
                        {
                            "area": area,
                            "perimeter": perimeter,
                            "color": face.Color,
                        }
                    )
                    total_area += area
                except Exception:
                    continue

        try:
            session.Parts.CloseAll(NXOpen.BasePart.CloseWholeTree.False_, None)
        except Exception:
            pass

        red_face_count = len(face_details)
        if red_face_count == 0:
            logger.info("文件中未找到红色面: %s", xt_file_path)
            return None

        return {
            "red_face_count": red_face_count,
            "total_area": round(total_area, 3),
            "single_length": round(total_area / red_face_count, 3),
            "face_details": face_details,
        }
    except ImportError:
        logger.warning("NXOpen 不可用，跳过红色面提取")
        return None
    except Exception as exc:
        logger.error("NXOpen 提取红色面失败: %s", exc)
        return None


def _build_slider_wire_cut_entry(red_face_stats: dict[str, Any]) -> dict[str, Any]:
    """根据红色面统计结果构建滑块线割条目。"""
    red_face_count = red_face_stats["red_face_count"]
    total_area = red_face_stats["total_area"]
    single_length = red_face_stats["single_length"]

    return {
        "code": "滑块",
        "cone": "f",
        "view": "front_view",
        "area_num": red_face_count,
        "instruction": f"{red_face_count} -红色面",
        "slider_angle": 0,
        "total_length": total_area,
        "is_additional": False,
        "matched_count": red_face_count,
        "single_length": single_length,
        "expected_count": red_face_count,
        "matched_line_ids": [],
        "overlapping_length": 0.0,
    }


def _download_xt_file(minio_client, xt_file_url: str, save_path: str) -> bool:
    """兼容不同 MinIO 客户端接口。"""
    if hasattr(minio_client, "get_file"):
        return bool(minio_client.get_file(xt_file_url, save_path))
    if hasattr(minio_client, "download_file"):
        return bool(minio_client.download_file(xt_file_url, save_path))
    raise AttributeError("minio_client does not support get_file/download_file")


def _merge_slider_entry(metadata: dict[str, Any], slider_entry: dict[str, Any]) -> dict[str, Any]:
    """把滑块红色面结果合并回 metadata.wire_cut_details。"""
    wire_cut_details = list(metadata.get("wire_cut_details") or [])
    updated = False
    for detail in wire_cut_details:
        if "滑" not in str(detail.get("instruction", "")):
            continue

        detail["code"] = "滑块"
        detail["view"] = "front_view"
        detail["total_length"] = slider_entry["total_length"]
        detail["area_num"] = slider_entry["area_num"]
        detail["matched_count"] = slider_entry["area_num"]
        detail["single_length"] = slider_entry["single_length"]
        detail["expected_count"] = slider_entry["area_num"]
        updated = True

    if not updated:
        wire_cut_details.append(slider_entry)

    return {
        **metadata,
        "wire_cut_details": wire_cut_details,
    }


def _update_features_metadata(
    subgraph_id: str,
    job_id: str,
    slider_entry: dict[str, Any],
    *,
    db_config: dict[str, Any] | None = None,
    connect_factory: ConnectFactory | None = None,
) -> bool:
    """写回 features.metadata.wire_cut_details。"""
    conn = None
    cursor = None
    try:
        conn = (connect_factory or (lambda: _create_connection(db_config)))()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT metadata FROM features WHERE subgraph_id = %s AND job_id = %s",
            (subgraph_id, job_id),
        )
        row = cursor.fetchone()
        if not row:
            logger.warning("未找到 features 记录: subgraph_id=%s, job_id=%s", subgraph_id, job_id)
            return False

        metadata = row[0] or {}
        merged_metadata = _merge_slider_entry(metadata, slider_entry)

        cursor.execute(
            "UPDATE features SET metadata = %s WHERE subgraph_id = %s AND job_id = %s",
            (_json_value(merged_metadata), subgraph_id, job_id),
        )
        conn.commit()
        logger.info(
            "滑块红色面写入成功: subgraph_id=%s 红色面=%s个 总面积=%smm²",
            subgraph_id,
            slider_entry["area_num"],
            slider_entry["total_length"],
        )
        return True
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        logger.error("写入滑块红色面失败: subgraph_id=%s error=%s", subgraph_id, exc, exc_info=True)
        return False
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def update_slider_red_face_data(
    subgraph_id: str,
    job_id: str,
    xt_file_url: str,
    db_config: dict[str, Any] | None = None,
    minio_client=None,
    *,
    connect_factory: ConnectFactory | None = None,
    extract_red_face_stats: RedFaceExtractor | None = None,
) -> bool:
    """下载 .x_t、提取红色面并写回 features metadata。"""
    logger.info("开始处理滑块红色面: subgraph_id=%s xt=%s", subgraph_id, xt_file_url)

    temp_dir = tempfile.mkdtemp(prefix="slider_xt_")
    temp_name = os.path.basename(xt_file_url) or f"{subgraph_id}.x_t"
    xt_local_path = os.path.join(temp_dir, temp_name)
    using_temp_file = True

    try:
        if os.path.isabs(xt_file_url) and os.path.exists(xt_file_url):
            xt_local_path = xt_file_url
            using_temp_file = False
        elif minio_client is None:
            logger.error("无法获取 .x_t 文件（无 minio_client 且非本地路径）: %s", xt_file_url)
            return False
        elif not _download_xt_file(minio_client, xt_file_url, xt_local_path):
            logger.error("下载 .x_t 文件失败: %s", xt_file_url)
            return False

        red_face_stats = (extract_red_face_stats or _extract_red_face_stats_nxopen)(xt_local_path)
        if not red_face_stats:
            logger.warning("未提取到红色面数据，跳过写入: %s", xt_local_path)
            return False

        slider_entry = _build_slider_wire_cut_entry(red_face_stats)
        return _update_features_metadata(
            subgraph_id,
            job_id,
            slider_entry,
            db_config=db_config,
            connect_factory=connect_factory,
        )
    finally:
        if using_temp_file and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
