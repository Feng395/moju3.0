"""Feature 持久化 runtime。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from ...core.logging import get_logger
from ...core.settings import settings

logger = get_logger(__name__)

_SUBGRAPHS_HAS_XT_FILE_URL: bool | None = None

ConnectFactory = Callable[[], Any]
RedFaceLookup = Callable[..., list[dict[str, Any]]]

_FEATURE_UPSERT_SQL = """
    INSERT INTO features
    (subgraph_id, job_id, version, length_mm, width_mm, thickness_mm,
     top_view_wire_length, front_view_wire_length, side_view_wire_length,
     processing_instructions, metadata, abnormal_situation,
     quantity, material, heat_treatment, calculated_weight_kg, needs_heat_treatment, has_auto_material,
     boring_num, has_material_preparation, water_mill, tooth_hole, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (subgraph_id, version)
    DO UPDATE SET
        length_mm = EXCLUDED.length_mm,
        width_mm = EXCLUDED.width_mm,
        thickness_mm = EXCLUDED.thickness_mm,
        top_view_wire_length = EXCLUDED.top_view_wire_length,
        front_view_wire_length = EXCLUDED.front_view_wire_length,
        side_view_wire_length = EXCLUDED.side_view_wire_length,
        processing_instructions = EXCLUDED.processing_instructions,
        metadata = EXCLUDED.metadata,
        abnormal_situation = EXCLUDED.abnormal_situation,
        quantity = EXCLUDED.quantity,
        material = EXCLUDED.material,
        heat_treatment = EXCLUDED.heat_treatment,
        calculated_weight_kg = EXCLUDED.calculated_weight_kg,
        needs_heat_treatment = EXCLUDED.needs_heat_treatment,
        has_auto_material = EXCLUDED.has_auto_material,
        boring_num = EXCLUDED.boring_num,
        has_material_preparation = EXCLUDED.has_material_preparation,
        water_mill = EXCLUDED.water_mill,
        tooth_hole = EXCLUDED.tooth_hole,
        created_at = EXCLUDED.created_at
    RETURNING feature_id
"""

_PROCESSING_DETAIL_INIT_SQL = """
    INSERT INTO processing_cost_calculation_details
    (job_id, subgraph_id, calculated_at, created_at)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT DO NOTHING
"""


def _create_connection():
    """按需创建 psycopg2 连接，避免模块导入时立刻触发数据库依赖。"""
    import psycopg2

    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
    )


def _json_value(payload: Any):
    from psycopg2.extras import Json

    return Json(payload)


def _subgraphs_has_xt_file_url(cursor) -> bool:
    global _SUBGRAPHS_HAS_XT_FILE_URL

    if _SUBGRAPHS_HAS_XT_FILE_URL is not None:
        return _SUBGRAPHS_HAS_XT_FILE_URL

    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'subgraphs' AND column_name = 'xt_file_url'
        """
    )
    _SUBGRAPHS_HAS_XT_FILE_URL = cursor.fetchone() is not None
    return _SUBGRAPHS_HAS_XT_FILE_URL


def get_subgraphs_from_db(
    job_id: str,
    subgraph_id: str | None = None,
    *,
    connect_factory: ConnectFactory | None = None,
) -> list[dict[str, Any]]:
    """查询待识别子图，保持 legacy 返回结构不变。"""

    conn = None
    cursor = None
    try:
        conn = (connect_factory or _create_connection)()
        cursor = conn.cursor()

        has_xt_file_url = _subgraphs_has_xt_file_url(cursor)
        select_xt_column = ", xt_file_url" if has_xt_file_url else ""

        if subgraph_id:
            cursor.execute(
                f"""
                SELECT subgraph_id, part_code, subgraph_file_url{select_xt_column}
                FROM subgraphs
                WHERE job_id = %s AND subgraph_id = %s
                """,
                (job_id, subgraph_id),
            )
        else:
            cursor.execute(
                f"""
                SELECT subgraph_id, part_code, subgraph_file_url{select_xt_column}
                FROM subgraphs
                WHERE job_id = %s
                ORDER BY part_code
                """,
                (job_id,),
            )

        rows = cursor.fetchall()
        subgraphs = [
            {
                "subgraph_id": row[0],
                "part_code": row[1],
                "subgraph_file_url": row[2],
                "xt_file_url": row[3] if has_xt_file_url else None,
            }
            for row in rows
        ]
        logger.info("feature get_subgraphs finished: job_id=%s count=%s", job_id, len(subgraphs))
        return subgraphs
    except Exception as exc:
        logger.error("feature get_subgraphs failed: job_id=%s error=%s", job_id, exc, exc_info=True)
        return []
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def save_features_to_db(
    subgraph_id: str,
    job_id: str,
    features: dict[str, Any],
    *,
    connect_factory: ConnectFactory | None = None,
    minio_client: Any | None = None,
    red_face_lookup: RedFaceLookup | None = None,
    now_factory: Callable[[], datetime] = datetime.now,
) -> bool:
    """保存特征识别结果，并补齐 processing detail 与线割工艺字段。"""

    conn = None
    cursor = None
    try:
        conn = (connect_factory or _create_connection)()
        cursor = conn.cursor()

        processing_instructions = features.get("processing_instructions") or {}
        metadata: dict[str, Any] = {}
        wire_cut_details = list(features.get("wire_cut_details") or [])

        # 中文说明：滑块红色面查表仍沿用 legacy 规则，但调用权已经收回到 src runtime。
        part_code = str(features.get("part_code") or "").strip()
        if part_code and wire_cut_details and red_face_lookup is not None and minio_client is not None:
            wire_cut_details = red_face_lookup(
                part_code,
                wire_cut_details,
                minio_client=minio_client,
            )

        if wire_cut_details:
            metadata["wire_cut_details"] = wire_cut_details

        heat_treatment = features.get("heat_treatment")
        abnormal_situation = features.get("abnormal_situation")
        water_mill = features.get("water_mill")
        tooth_hole = features.get("tooth_hole")
        needs_heat_treatment = bool(str(heat_treatment).strip()) if heat_treatment is not None else False
        current_time = now_factory()

        values = (
            subgraph_id,
            job_id,
            1,
            features["length_mm"],
            features["width_mm"],
            features["thickness_mm"],
            features["top_view_wire_length"],
            features.get("front_view_wire_length", 0.0),
            features.get("side_view_wire_length", 0.0),
            _json_value(processing_instructions),
            _json_value(metadata) if metadata else None,
            _json_value(abnormal_situation) if abnormal_situation else None,
            features.get("quantity"),
            features.get("material"),
            heat_treatment,
            features.get("weight_kg"),
            needs_heat_treatment,
            features.get("has_auto_material", False),
            features.get("boring_num", 0),
            features.get("has_material_preparation"),
            _json_value(water_mill) if water_mill else None,
            _json_value(tooth_hole) if tooth_hole else None,
            current_time,
        )
        cursor.execute(_FEATURE_UPSERT_SQL, values)
        feature_row = cursor.fetchone()
        feature_id = feature_row[0] if feature_row else None

        cursor.execute(
            _PROCESSING_DETAIL_INIT_SQL,
            (job_id, subgraph_id, current_time, current_time),
        )

        wire_process_note = features.get("wire_process_note")
        wire_process = features.get("wire_process")
        if wire_process_note or wire_process:
            update_fields: list[str] = []
            update_values: list[Any] = []
            if wire_process_note:
                update_fields.append("wire_process_note = %s")
                update_values.append(wire_process_note)
            if wire_process:
                update_fields.append("wire_process = %s")
                update_values.append(wire_process)
            update_values.append(subgraph_id)

            cursor.execute(
                f"""
                UPDATE subgraphs
                SET {", ".join(update_fields)}
                WHERE subgraph_id = %s
                """,
                tuple(update_values),
            )

        conn.commit()
        logger.info("feature save_features finished: subgraph_id=%s feature_id=%s", subgraph_id, feature_id)
        return True
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        logger.error("feature save_features failed: subgraph_id=%s error=%s", subgraph_id, exc, exc_info=True)
        return False
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
