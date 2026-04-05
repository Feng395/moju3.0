"""DXF 特征分析 runtime。"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)
# 中文说明：以下依赖仍来自 legacy scripts，这里通过惰性加载把编排入口收口到 src。
ezdxf = None
extract_all_texts = None
extract_dimensions = None
parse_processing_instructions_from_texts = None
parse_frame_texts_from_extracted = None
parse_material_info_from_texts = None
check_auto_material_from_texts = None
extract_material_preparation = None
ViewWireCalculator = None
calculate_red_line_length = None
calculate_boring_num = None
detect_chamfers = None
detect_oil_tank = None
detect_bevel = None
detect_grinding_faces = None
should_calculate_water_mill = None
get_water_mill_data = None
detect_hanging_table = None
detect_tooth_hole = None
SliderCalculator = None


def _load_dependencies() -> None:
    """按需装载 legacy 特征识别依赖，避免模块导入即拉起重型脚本。"""
    # 中文说明：避免模块导入阶段直接拉起 ezdxf 与整套特征识别依赖。
    global ezdxf
    global extract_all_texts
    global extract_dimensions
    global parse_processing_instructions_from_texts
    global parse_frame_texts_from_extracted
    global parse_material_info_from_texts
    global check_auto_material_from_texts
    global extract_material_preparation
    global ViewWireCalculator
    global calculate_red_line_length
    global calculate_boring_num
    global detect_chamfers
    global detect_oil_tank
    global detect_bevel
    global detect_grinding_faces
    global should_calculate_water_mill
    global get_water_mill_data
    global detect_hanging_table
    global detect_tooth_hole
    global SliderCalculator

    if ezdxf is None:
        import ezdxf as _ezdxf

        ezdxf = _ezdxf
    if extract_all_texts is None:
        from scripts.feature_recognition.text_extractor import extract_all_texts as _extract_all_texts

        extract_all_texts = _extract_all_texts
    if extract_dimensions is None:
        from scripts.feature_recognition.dimension_extractor import extract_dimensions as _extract_dimensions

        extract_dimensions = _extract_dimensions
    if parse_processing_instructions_from_texts is None:
        from scripts.feature_recognition.processing_instruction_extractor import (
            parse_processing_instructions_from_texts as _parse_processing_instructions_from_texts,
        )

        parse_processing_instructions_from_texts = _parse_processing_instructions_from_texts
    if parse_frame_texts_from_extracted is None:
        from scripts.feature_recognition.frame_text_extractor import (
            parse_frame_texts_from_extracted as _parse_frame_texts_from_extracted,
        )

        parse_frame_texts_from_extracted = _parse_frame_texts_from_extracted
    if parse_material_info_from_texts is None or check_auto_material_from_texts is None:
        from scripts.feature_recognition.material_info_extractor import (
            check_auto_material_from_texts as _check_auto_material_from_texts,
            parse_material_info_from_texts as _parse_material_info_from_texts,
        )

        parse_material_info_from_texts = _parse_material_info_from_texts
        check_auto_material_from_texts = _check_auto_material_from_texts
    if extract_material_preparation is None:
        from scripts.feature_recognition.material_preparation_extractor import (
            extract_material_preparation as _extract_material_preparation,
        )

        extract_material_preparation = _extract_material_preparation
    if ViewWireCalculator is None:
        from scripts.feature_recognition.view_wire_calculator import ViewWireCalculator as _ViewWireCalculator

        ViewWireCalculator = _ViewWireCalculator
    if calculate_red_line_length is None:
        from scripts.feature_recognition.wire_length_calculator import (
            calculate_red_line_length as _calculate_red_line_length,
        )

        calculate_red_line_length = _calculate_red_line_length
    if calculate_boring_num is None:
        from scripts.feature_recognition.boring_calculator import calculate_boring_num as _calculate_boring_num

        calculate_boring_num = _calculate_boring_num
    if detect_chamfers is None:
        from scripts.feature_recognition.chamfer_detector import detect_chamfers as _detect_chamfers

        detect_chamfers = _detect_chamfers
    if detect_oil_tank is None:
        from scripts.feature_recognition.oil_tank_detector import detect_oil_tank as _detect_oil_tank

        detect_oil_tank = _detect_oil_tank
    if detect_bevel is None:
        from scripts.feature_recognition.bevel_detector import detect_bevel as _detect_bevel

        detect_bevel = _detect_bevel
    if detect_grinding_faces is None:
        from scripts.feature_recognition.grinding_detector import detect_grinding_faces as _detect_grinding_faces

        detect_grinding_faces = _detect_grinding_faces
    if should_calculate_water_mill is None or get_water_mill_data is None:
        from scripts.feature_recognition.water_mill_calculator import (
            get_water_mill_data as _get_water_mill_data,
            should_calculate_water_mill as _should_calculate_water_mill,
        )

        should_calculate_water_mill = _should_calculate_water_mill
        get_water_mill_data = _get_water_mill_data
    if detect_hanging_table is None:
        from scripts.feature_recognition.hanging_table_detector import detect_hanging_table as _detect_hanging_table

        detect_hanging_table = _detect_hanging_table
    if detect_tooth_hole is None:
        from scripts.feature_recognition.tooth_hole_detector import detect_tooth_hole as _detect_tooth_hole

        detect_tooth_hole = _detect_tooth_hole
    if SliderCalculator is None:
        from scripts.feature_recognition.slider_calculator import SliderCalculator as _SliderCalculator

        SliderCalculator = _SliderCalculator


def analyze_dxf_features(dxf_file_path: str) -> dict[str, Any] | None:
    """分析单个 DXF，并返回供 src 链路消费的统一特征结果。"""

    try:
        # 中文说明：runtime 负责组织调用顺序、归一化输出，算法细节暂时继续复用 legacy 实现。
        _load_dependencies()
        doc = ezdxf.readfile(dxf_file_path)
        msp = doc.modelspace()
        all_text_data = extract_all_texts(msp)
        all_texts = all_text_data["texts"]

        length_mm, width_mm, thickness_mm = extract_dimensions(doc)
        dimension_anomalies = _build_dimension_anomalies(length_mm, width_mm, thickness_mm)

        processing_instructions_old, instruction_full_texts = parse_processing_instructions_from_texts(all_texts)
        frame_texts = parse_frame_texts_from_extracted(all_text_data, doc)
        material_info = parse_material_info_from_texts(all_texts)
        has_auto_material = check_auto_material_from_texts(all_texts)
        has_material_preparation = extract_material_preparation(all_texts)
        processing_instructions = {
            frame_id: [text["content"] for text in texts]
            for frame_id, texts in frame_texts.items()
        }

        view_wire_lengths, wire_cut_anomalies, wire_cut_details, views, view_anomalies = _analyze_views(
            doc=doc,
            msp=msp,
            all_texts=all_texts,
            processing_instructions_old=processing_instructions_old,
            length_mm=length_mm,
            width_mm=width_mm,
            thickness_mm=thickness_mm,
            has_auto_material=has_auto_material,
            has_material_preparation=has_material_preparation,
        )

        boring_num = calculate_boring_num(wire_cut_details)
        wire_process_note = _extract_wire_process_note(all_texts)
        wire_process = _map_wire_process(wire_process_note)

        abnormal_situation: dict[str, Any] = {}
        if dimension_anomalies:
            abnormal_situation["dimension_anomalies"] = dimension_anomalies
        if view_anomalies:
            abnormal_situation["view_anomalies"] = view_anomalies
        if wire_cut_anomalies:
            abnormal_situation["wire_cut_anomalies"] = wire_cut_anomalies

        chamfer_counts = detect_chamfers(all_texts, instruction_full_texts)
        oil_tank = detect_oil_tank(all_texts, doc)
        bevel = detect_bevel(all_texts, doc, views)
        grinding_faces = detect_grinding_faces(doc, length_mm, width_mm, thickness_mm)
        if grinding_faces == 0 and not all([length_mm, width_mm, thickness_mm]):
            grinding_faces = fallback_grinding_detection(processing_instructions, doc)

        need_water_mill = should_calculate_water_mill(has_material_preparation, has_auto_material)
        hanging_table = 0
        thread_ends = 0
        if need_water_mill:
            thread_ends = 1
            hanging_table = detect_hanging_table(all_texts, doc, length_mm, width_mm, thickness_mm)

        water_mill_data = get_water_mill_data(
            hanging_table=hanging_table,
            c1_c2_chamfer=chamfer_counts["c1_c2_chamfer"],
            c3_c5_chamfer=chamfer_counts["c3_c5_chamfer"],
            r1_r2_chamfer=chamfer_counts["r1_r2_chamfer"],
            r3_r5_chamfer=chamfer_counts["r3_r5_chamfer"],
            oil_tank=oil_tank,
            thread_ends=thread_ends,
            bevel=bevel,
            grinding=grinding_faces,
        )
        tooth_hole = detect_tooth_hole(
            all_texts=all_texts,
            processing_instructions=processing_instructions,
            has_auto_material=has_auto_material,
            heat_treatment=material_info.get("heat_treatment"),
            msp=msp,
            views=views,
        )

        # 中文说明：这里统一做字段整形，保证 gateway / service 消费的数据结构稳定。
        return {
            "length_mm": float(round(length_mm, 2)) if length_mm else 0.0,
            "width_mm": float(round(width_mm, 2)) if width_mm else 0.0,
            "thickness_mm": float(round(thickness_mm, 2)) if thickness_mm else 0.0,
            "top_view_wire_length": float(round(view_wire_lengths["top_view_wire_length"], 2)),
            "front_view_wire_length": float(round(view_wire_lengths["front_view_wire_length"], 2)),
            "side_view_wire_length": float(round(view_wire_lengths["side_view_wire_length"], 2)),
            "processing_instructions": processing_instructions,
            "quantity": material_info.get("quantity"),
            "material": material_info.get("material"),
            "heat_treatment": material_info.get("heat_treatment"),
            "weight_kg": (
                float(round(material_info.get("weight_kg"), 3))
                if material_info.get("weight_kg") is not None
                else None
            ),
            "has_auto_material": has_auto_material,
            "abnormal_situation": abnormal_situation or None,
            "wire_cut_details": wire_cut_details,
            "boring_num": boring_num,
            "wire_process_note": wire_process_note,
            "wire_process": wire_process,
            "has_material_preparation": has_material_preparation,
            "water_mill": water_mill_data,
            "tooth_hole": tooth_hole,
        }
    except Exception as exc:
        logger.error("Failed to analyze DXF features: %s", exc, exc_info=True)
        return None


def _build_dimension_anomalies(length_mm: float | None, width_mm: float | None, thickness_mm: float | None):
    missing = []
    if not length_mm:
        missing.append("长度")
    if not width_mm:
        missing.append("宽度")
    if not thickness_mm:
        missing.append("厚度")
    if not missing:
        return []
    return [{
        "type": "dimension_missing",
        "description": f"零件尺寸缺失: {', '.join(missing)}",
        "missing_dimensions": missing,
    }]


def _analyze_views(
    *,
    doc,
    msp,
    all_texts: list[str],
    processing_instructions_old,
    length_mm,
    width_mm,
    thickness_mm,
    has_auto_material: bool,
    has_material_preparation: bool,
):
    view_wire_lengths = {
        "top_view_wire_length": 0.0,
        "front_view_wire_length": 0.0,
        "side_view_wire_length": 0.0,
        "unmatched_red_lines": [],
    }
    wire_cut_anomalies: list[dict[str, Any]] = []
    wire_cut_details: list[dict[str, Any]] = []
    views = None
    view_anomalies: list[dict[str, Any]] = []

    try:
        l = length_mm or 0
        w = width_mm or 0
        t = thickness_mm or 0
        view_calculator = ViewWireCalculator(tolerance=5.0)
        view_result = view_calculator.calculate_wire_lengths_by_views(doc, l, w, t, processing_instructions_old, all_texts)
        view_wire_lengths.update({
            "top_view_wire_length": view_result["top_view_wire_length"],
            "front_view_wire_length": view_result["front_view_wire_length"],
            "side_view_wire_length": view_result["side_view_wire_length"],
            "unmatched_red_lines": view_result.get("unmatched_red_lines", []),
        })
        wire_cut_anomalies = view_result.get("wire_cut_anomalies", [])
        wire_cut_details = view_result.get("wire_cut_details", [])
        views = view_result.get("views")

        if views:
            missing_views = []
            if not views.get("top_view"):
                missing_views.append("俯视图")
            if not views.get("front_view"):
                missing_views.append("正视图")
            if not views.get("side_view"):
                missing_views.append("侧视图")
            if missing_views:
                view_anomalies.append({
                    "type": "view_recognition_failed",
                    "description": f"视图识别异常: {', '.join(missing_views)}未识别到",
                    "missing_views": missing_views,
                })

        try:
            slider_calculator = SliderCalculator()
            wire_cut_details, slider_anomaly, length_adjustment = slider_calculator.calculate_slider_process(
                msp=msp,
                views=views,
                wire_cut_details=wire_cut_details,
                unmatched_red_lines=view_wire_lengths.get("unmatched_red_lines", []),
                length=l,
                width=w,
                thickness=t,
            )
            if slider_anomaly:
                view_anomalies.append(slider_anomaly)
                if length_adjustment:
                    view_wire_lengths["top_view_wire_length"] += length_adjustment
                wire_cut_anomalies = [
                    item for item in wire_cut_anomalies if item.get("type") != "unmatched_red_lines"
                ]
        except Exception:
            logger.warning("Slider process calculation failed", exc_info=True)

        try:
            from scripts.feature_recognition.wire_plate_overlap_filter import WirePlateOverlapFilter

            overlap_filter = WirePlateOverlapFilter(overlap_tolerance=0.5)
            wire_cut_details, view_length_adjustments = overlap_filter.filter_overlapping_wire_cuts(
                doc,
                wire_cut_details,
                views,
                has_auto_material,
                has_material_preparation,
            )
            for view_field, adjustment in view_length_adjustments.items():
                if adjustment:
                    view_wire_lengths[view_field] += adjustment
        except Exception:
            logger.warning("Wire/plate overlap filtering failed", exc_info=True)
    except Exception:
        logger.warning("View-based wire length calculation failed; using fallback", exc_info=True)
        view_wire_lengths["top_view_wire_length"] = calculate_red_line_length(doc)

    return view_wire_lengths, wire_cut_anomalies, wire_cut_details, views, view_anomalies


def _extract_wire_process_note(all_texts: list[str]) -> str | None:
    wire_pattern = re.compile(r"[^\s]*丝割[^\s]*")
    for text in all_texts:
        match = wire_pattern.search(text)
        if match:
            return match.group(0)
    return None


def _map_wire_process(wire_process_note: str | None) -> str | None:
    if not wire_process_note:
        return None
    mapping = {
        "慢丝割一刀": "slow_cut",
        "慢丝割一修一": "slow_and_one",
        "慢丝割一修二": "slow_and_two",
        "慢丝割一修三": "slow_and_three",
        "中丝割一修一": "middle_and_one",
        "快丝割一刀": "fast_cut",
    }
    return mapping.get(wire_process_note)


def fallback_grinding_detection(processing_instructions, doc) -> int:
    """尺寸缺失时的研磨面兜底识别。"""

    try:
        all_texts = []
        for frame_texts in processing_instructions.values():
            all_texts.extend(frame_texts)

        text_result = extract_grinding_from_text_patterns(all_texts)
        if text_result > 0:
            return text_result

        standard_result = infer_grinding_from_standard_descriptions(all_texts)
        if standard_result > 0:
            return standard_result

        msp = doc.modelspace()
        symbol_count = count_grinding_symbols_simple(msp)
        if symbol_count >= 2:
            return estimate_by_symbol_count(symbol_count, all_texts)
        return 0
    except Exception:
        logger.warning("Fallback grinding detection failed", exc_info=True)
        return 0


def extract_grinding_from_text_patterns(texts: list[str]) -> int:
    patterns = [
        r"(\d+)\s*面\s*研磨",
        r"研磨\s*(\d+)\s*面",
        r"磨\s*(\d+)\s*面",
        r"(\d+)\s*面.*磨",
    ]
    for text in texts:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
    return 0


def infer_grinding_from_standard_descriptions(texts: list[str]) -> int:
    standard_patterns = [
        (r"D\s*:\s*\d+\s*-\s*研磨基准边[：:]\s*深度凸[：:]\s*侧壁凸", 4),
        (r"研磨基准边.*深度凸.*侧壁凸", 4),
        (r"全周.*研磨", 6),
        (r"两面.*研磨", 2),
        (r"四面.*研磨", 4),
        (r"六面.*研磨", 6),
        (r"研磨.*基准.*边", 4),
    ]
    for text in texts:
        for pattern, faces in standard_patterns:
            if re.search(pattern, text):
                return faces
    return 0


def count_grinding_symbols_simple(msp) -> int:
    target_blocks = ["XYMFH-A", "XYMFH", "XYMFH-A0", "研磨标记", "磨削标记"]
    grinding_count = 0

    for entity in msp.query("INSERT"):
        try:
            if entity.dxf.name in target_blocks:
                grinding_count += 1
        except Exception:
            continue

    polylines = list(msp.query("POLYLINE")) + list(msp.query("LWPOLYLINE"))
    for polyline in polylines:
        try:
            points = list(polyline.get_points("xy"))
            if 6 <= len(points) <= 20 and is_likely_grinding_symbol(points):
                grinding_count += 1
        except Exception:
            continue
    return grinding_count


def is_likely_grinding_symbol(points) -> bool:
    if len(points) < 6:
        return False

    y_changes = 0
    for i in range(1, len(points) - 1):
        y1, y2, y3 = points[i - 1][1], points[i][1], points[i + 1][1]
        if (y2 > y1 and y2 > y3) or (y2 < y1 and y2 < y3):
            y_changes += 1
    return y_changes >= 3


def estimate_by_symbol_count(symbol_count: int, texts: list[str]) -> int:
    text_content = " ".join(texts)
    has_standard = "研磨基准边" in text_content
    has_full_perimeter = "全周" in text_content
    has_depth_side = "深度凸" in text_content and "侧壁凸" in text_content

    if has_standard or has_depth_side:
        if 2 <= symbol_count <= 6:
            return 4
        if symbol_count > 6:
            return 6
    if has_full_perimeter and symbol_count >= 4:
        return 6
    if symbol_count == 2:
        return 2
    if symbol_count in {3, 4}:
        return 4
    if symbol_count >= 5:
        return 6
    return 0
