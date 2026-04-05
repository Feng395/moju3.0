"""Src-owned 板料线集成实现。"""

import os
from typing import Dict, List, Tuple, Optional

# 延迟导入，避免循环依赖
def _lazy_import_ezdxf():
    """延迟导入ezdxf"""
    import ezdxf
    return ezdxf

def _lazy_import_logger():
    """延迟导入logger"""
    from loguru import logger
    return logger


def _lazy_import_view_identifier():
    """视图识别器，暂时复用 feature 侧现有实现。"""
    try:
        from scripts.feature_recognition.view_identifier import ViewIdentifier
        return ViewIdentifier
    except ImportError:
        try:
            from feature_recognition.view_identifier import ViewIdentifier
            return ViewIdentifier
        except ImportError:
            return None


class MaterialLineIntegrator:
    """板料线集成器 - 为子图添加板料线"""
    
    def __init__(self, enable: bool = True):
        """
        初始化板料线集成器
        
        Args:
            enable: 是否启用板料线功能（默认True）
        """
        self.enable = enable
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        self.logger = _lazy_import_logger()
    
    def add_material_lines_to_subgraph(
        self, 
        dxf_path: str, 
        lwt: Dict[str, float], 
        sub_code: str,
        part_info: Optional[Dict] = None
    ) -> bool:
        """
        为单个子图DXF添加板料线
        
        Args:
            dxf_path: 子图DXF文件路径
            lwt: {'L': float, 'W': float, 'T': float}
            sub_code: 子图编号
            part_info: 零件信息（可选，包含position等）
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        if not self.enable:
            self.stats['skipped'] += 1
            return True
        
        self.stats['total'] += 1
        
        try:
            # 延迟导入ezdxf
            ezdxf = _lazy_import_ezdxf()
            
            # 1. 读取DXF
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()

            # 2. 查找视图并添加板料线
            lines_added = self._find_views_and_add_lines(
                msp, doc, lwt, sub_code, part_info
            )
            
            if lines_added > 0:
                # 3. 保存DXF（覆盖原文件）
                doc.saveas(dxf_path)
                self.logger.info(f"  ✅ {sub_code}: 添加 {lines_added} 个板料线")
                self.stats['success'] += 1
                return True
            else:
                self.logger.warning(f"  ⚠️ {sub_code}: 未找到匹配的视图，跳过板料线添加")
                self.stats['skipped'] += 1
                return True  # 不算失败，只是跳过
                
        except Exception as e:
            self.logger.error(f"  ❌ {sub_code}: 板料线添加失败 - {e}")
            self.stats['failed'] += 1
            return False
    
    def _collect_existing_material_line_bboxes(self, msp) -> List[Tuple[float, float, float, float]]:
        """收集已有板料线的边界框，用于局部去重而不是整图跳过"""
        existing_boxes = []
        for entity in msp.query('LINE LWPOLYLINE POLYLINE'):
            layer = entity.dxf.layer
            if 'MATERIAL_LINE' not in layer.upper():
                continue

            bbox = self._get_entity_bbox(entity)
            if bbox:
                existing_boxes.append(bbox)
        return existing_boxes

    def _get_entity_bbox(self, entity) -> Optional[Tuple[float, float, float, float]]:
        """获取LINE/LWPOLYLINE/POLYLINE实体边界框"""
        try:
            if entity.dxftype() == 'LINE':
                return (
                    min(entity.dxf.start[0], entity.dxf.end[0]),
                    min(entity.dxf.start[1], entity.dxf.end[1]),
                    max(entity.dxf.start[0], entity.dxf.end[0]),
                    max(entity.dxf.start[1], entity.dxf.end[1]),
                )

            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                points = list(entity.get_points(format='xy'))
                if not points:
                    return None
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                return (min(xs), min(ys), max(xs), max(ys))
        except Exception:
            return None

        return None

    def _bbox_overlap_ratio(
        self,
        bbox1: Tuple[float, float, float, float],
        bbox2: Tuple[float, float, float, float]
    ) -> float:
        """计算两个边界框的重叠比例，便于判断是否已经加过板料线"""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = max((bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1]), 1.0)
        area2 = max((bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1]), 1.0)
        return intersection / min(area1, area2)

    def _has_material_line_for_bbox(
        self,
        existing_boxes: List[Tuple[float, float, float, float]],
        bbox: Tuple[float, float, float, float],
        threshold: float = 0.85
    ) -> bool:
        """判断当前视图矩形附近是否已经有对应板料线"""
        for existing_bbox in existing_boxes:
            if self._bbox_overlap_ratio(existing_bbox, bbox) >= threshold:
                return True
        return False

    def _calculate_match_score(
        self,
        width: float,
        height: float,
        l: float,
        w: float,
        t: float
    ) -> float:
        """计算视图和目标L/W/T的匹配分数，越大越优先"""
        candidate_pairs = [
            ((l, w), 'top'),
            ((w, l), 'top'),
            ((t, w), 'side'),
            ((w, t), 'side'),
            ((l, t), 'front'),
            ((t, l), 'front'),
        ]

        best_score = float('-inf')
        for (target_w, target_h), _ in candidate_pairs:
            normalized_error = (
                abs(width - target_w) / max(target_w, 1.0) +
                abs(height - target_h) / max(target_h, 1.0)
            )
            best_score = max(best_score, 1000.0 - normalized_error * 500.0)
        return best_score
    
    def _find_views_and_add_lines(
        self, 
        msp, 
        doc, 
        lwt: Dict[str, float], 
        sub_code: str,
        part_info: Optional[Dict]
    ) -> int:
        """
        查找视图并添加板料线
        
        Returns:
            int: 添加的板料线数量
        """
        l, w, t = lwt['L'], lwt['W'], lwt['T']
        lines_added = 0
        
        # 计算动态容差
        tolerance_l = self._calculate_dynamic_tolerance(l)
        tolerance_w = self._calculate_dynamic_tolerance(w)
        tolerance_t = self._calculate_dynamic_tolerance(t)
        
        self.logger.debug(f"    尺寸: L={l:.1f}, W={w:.1f}, T={t:.1f}")
        self.logger.debug(f"    容差: L±{tolerance_l:.1f}, W±{tolerance_w:.1f}, T±{tolerance_t:.1f}")
        
        all_views = self._find_views_with_identifier(msp, l, w, t)
        if not all_views:
            polyline_views = self._find_polyline_views(
                msp, l, w, t, tolerance_l, tolerance_w, tolerance_t
            )
            line_views = self._find_line_rectangle_views(
                msp, l, w, t, tolerance_l, tolerance_w, tolerance_t
            )
            all_views = sorted(
                polyline_views + line_views,
                key=lambda view: view.get('match_score', 0.0),
                reverse=True
            )

        if not all_views:
            return 0
        
        # 3. 视图去重（每种类型只添加一次）
        view_types_added = set()
        existing_boxes = self._collect_existing_material_line_bboxes(msp)
        
        for view in all_views:
            view_type = view['view_type']
            bbox = view.get('normalized_bbox')
            if bbox is None:
                bbox = self._normalize_view_bbox(view_type, view['bbox'], l, w, t)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            # 去重
            if view_type in view_types_added:
                continue

            if self._has_material_line_for_bbox(existing_boxes, bbox):
                self.logger.info(f"    ℹ️ {sub_code}: {view_type} 已有板料线，跳过补加")
                view_types_added.add(view_type)
                continue
            
            # 添加板料线
            self._draw_material_box(
                msp, doc, bbox, 
                f"MATERIAL_LINE_{sub_code}_{view_type.upper()}"
            )
            
            view_types_added.add(view_type)
            existing_boxes.append(bbox)
            lines_added += 1
            
            self.logger.debug(
                f"    ✓ {view_type}: "
                f"{width:.1f}x{height:.1f}mm"
            )
        
        return lines_added

    def _normalize_view_bbox(
        self,
        view_type: str,
        bbox: Tuple[float, float, float, float],
        l: float,
        w: float,
        t: float
    ) -> Tuple[float, float, float, float]:
        """将候选框按目标尺寸居中回正，减少外接框偏瘦或偏高的问题。"""
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        target_size = self._get_expected_view_size(view_type, width, height, l, w, t)
        if target_size is None:
            return bbox

        target_width, target_height = target_size
        if target_width <= 0 or target_height <= 0:
            return bbox

        max_dimension_error = max(
            abs(width - target_width),
            abs(height - target_height)
        )
        tolerance = max(
            self._calculate_dynamic_tolerance(target_width),
            self._calculate_dynamic_tolerance(target_height),
            20.0
        )
        if max_dimension_error > tolerance:
            return bbox

        center_x, center_y = self._bbox_center(bbox)
        return (
            center_x - target_width / 2.0,
            center_y - target_height / 2.0,
            center_x + target_width / 2.0,
            center_y + target_height / 2.0,
        )

    def _get_expected_view_size(
        self,
        view_type: str,
        width: float,
        height: float,
        l: float,
        w: float,
        t: float
    ) -> Optional[Tuple[float, float]]:
        """根据当前候选框方向选择最接近的目标尺寸。"""
        dimension_pairs = {
            'top_view': [(l, w), (w, l)],
            'front_view': [(l, t), (t, l)],
            'side_view': [(w, t), (t, w)],
        }
        candidates = dimension_pairs.get(view_type, [])
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda pair: abs(width - pair[0]) + abs(height - pair[1])
        )

    def _align_bbox_to_top_projection(
        self,
        bbox: Tuple[float, float, float, float],
        top_bbox: Optional[Tuple[float, float, float, float]]
    ) -> Tuple[float, float, float, float]:
        """将右侧/下侧视图沿 top_view 的投影范围展开。"""
        if not top_bbox:
            return bbox

        center_x, center_y = self._bbox_center(bbox)
        top_center_x, top_center_y = self._bbox_center(top_bbox)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        offset_x = abs(center_x - top_center_x)
        offset_y = abs(center_y - top_center_y)

        if offset_x > offset_y * 1.1:
            return (
                center_x - width / 2.0,
                top_bbox[1],
                center_x + width / 2.0,
                top_bbox[3],
            )
        if offset_y > offset_x * 1.1:
            return (
                top_bbox[0],
                center_y - height / 2.0,
                top_bbox[2],
                center_y + height / 2.0,
            )
        return bbox

    def _find_views_with_identifier(
        self,
        msp,
        l: float,
        w: float,
        t: float
    ) -> List[Dict]:
        """复用 feature_recognition 的视图识别能力，支持平行线对兜底"""
        ViewIdentifier = _lazy_import_view_identifier()
        if ViewIdentifier is None:
            return []

        try:
            identifier = ViewIdentifier(tolerance=10.0)
            views, anomalies = identifier.identify_views(msp, l, w, t)
            if anomalies:
                self.logger.debug(f"    视图识别异常数: {len(anomalies)}")

            normalized = []
            for view_name, view_info in views.items():
                bounds = view_info.get('bounds')
                if not bounds:
                    continue

                bbox = (
                    float(bounds['min_x']),
                    float(bounds['min_y']),
                    float(bounds['max_x']),
                    float(bounds['max_y']),
                )
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                normalized.append({
                    'bbox': bbox,
                    'width': width,
                    'height': height,
                    'view_type': view_name,
                    'match_score': self._calculate_match_score(width, height, l, w, t),
                    'source': 'view_identifier',
                })

            if normalized:
                normalized = self._refine_views_by_layout(
                    identifier, msp, normalized, l, w, t
                )
                self.logger.debug(f"    视图识别器命中 {len(normalized)} 个视图")
                return sorted(
                    normalized,
                    key=lambda view: view.get('match_score', 0.0),
                    reverse=True
                )
        except Exception as e:
            self.logger.debug(f"    视图识别器调用失败，回退旧逻辑: {e}")

        return []

    def _relabel_views_by_layout(self, views: List[Dict]) -> List[Dict]:
        """按版式位置统一视图命名，避免 front/side 在不同模块中定义不一致"""
        if len(views) < 3:
            return views

        tolerance = 5.0
        avg_x = sum((view['bbox'][0] + view['bbox'][2]) / 2.0 for view in views) / len(views)
        avg_y = sum((view['bbox'][1] + view['bbox'][3]) / 2.0 for view in views) / len(views)

        left_top = []
        left_bottom = []
        right_top = []
        right_bottom = []

        for view in views:
            bbox = view['bbox']
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
            is_left = (cx < avg_x - tolerance) or (abs(cx - avg_x) <= tolerance)
            is_top = (cy > avg_y + tolerance) or (abs(cy - avg_y) <= tolerance)

            if is_left:
                if is_top:
                    left_top.append(view)
                else:
                    left_bottom.append(view)
            else:
                if is_top:
                    right_top.append(view)
                else:
                    right_bottom.append(view)

        relabeled = []

        if left_top:
            top_view = max(left_top, key=lambda item: item['width'] * item['height']).copy()
            top_view['view_type'] = 'top_view'
            relabeled.append(top_view)

        if left_bottom:
            front_view = max(left_bottom, key=lambda item: item['width'] * item['height']).copy()
            front_view['view_type'] = 'front_view'
            relabeled.append(front_view)

        if right_top:
            side_view = max(right_top, key=lambda item: item['width'] * item['height']).copy()
            side_view['view_type'] = 'side_view'
            relabeled.append(side_view)

        if len(relabeled) >= 3:
            return relabeled

        return views

    def _refine_views_by_layout(
        self,
        identifier,
        msp,
        views: List[Dict],
        l: float,
        w: float,
        t: float
    ) -> List[Dict]:
        """先按版式确定槽位，再在槽位内部挑选更精确的候选框。"""
        if len(views) < 2:
            return views

        view_dimensions = {
            'top_view': [(l, w), (w, l)],
            'front_view': [(l, t), (t, l)],
            'side_view': [(w, t), (t, w)],
        }

        try:
            raw_parallel_candidates = identifier._find_all_views_by_parallel_lines(
                msp,
                view_dimensions,
                []
            )
        except Exception:
            raw_parallel_candidates = {}

        anchors = self._build_layout_anchors(identifier, msp, views, raw_parallel_candidates)
        if not anchors:
            return views

        refined = []
        candidate_cache = {}
        top_bbox = None

        top_slot = self._select_top_slot(anchors, l, w, t)
        if top_slot and anchors.get(top_slot):
            top_candidates = self._get_slot_candidates(
                candidate_cache=candidate_cache,
                view_type='top_view',
                slot_name=top_slot,
                anchors=anchors,
                current_views=views,
                parallel_candidates=raw_parallel_candidates.get('top_view', []),
                l=l,
                w=w,
                t=t,
            )
            best_top = self._pick_best_candidate(top_candidates)
            if best_top:
                best_top = self._prefer_current_view_candidate(
                    view_type='top_view',
                    selected_candidate=best_top,
                    current_views=views,
                    l=l,
                    w=w,
                    t=t,
                )
                top_bbox = self._normalize_view_bbox(
                    'top_view',
                    best_top['bbox'],
                    l,
                    w,
                    t,
                )
                refined.append({
                    'bbox': best_top['bbox'],
                    'width': best_top['width'],
                    'height': best_top['height'],
                    'normalized_bbox': top_bbox,
                    'view_type': 'top_view',
                    'match_score': self._calculate_match_score(
                        best_top['width'],
                        best_top['height'],
                        l,
                        w,
                        t
                    ),
                    'source': best_top['source'],
                })

        non_top_assignment = self._assign_front_and_side_views(
            candidate_cache=candidate_cache,
            anchors=anchors,
            current_views=views,
            raw_parallel_candidates=raw_parallel_candidates,
            top_slot=top_slot,
            l=l,
            w=w,
            t=t,
        )
        for view_type in ('front_view', 'side_view'):
            best_candidate = non_top_assignment.get(view_type)
            if not best_candidate:
                continue
            best_candidate = self._prefer_current_view_candidate(
                view_type=view_type,
                selected_candidate=best_candidate,
                current_views=views,
                l=l,
                w=w,
                t=t,
            )
            normalized_bbox = self._normalize_view_bbox(
                view_type,
                best_candidate['bbox'],
                l,
                w,
                t,
            )
            normalized_bbox = self._align_bbox_to_top_projection(
                normalized_bbox,
                top_bbox,
            )
            refined.append({
                'bbox': best_candidate['bbox'],
                'width': best_candidate['width'],
                'height': best_candidate['height'],
                'normalized_bbox': normalized_bbox,
                'view_type': view_type,
                'match_score': self._calculate_match_score(
                    best_candidate['width'],
                    best_candidate['height'],
                    l,
                    w,
                    t
                ),
                'source': best_candidate['source'],
            })

        refined = self._repair_projected_views(
            msp=msp,
            views=refined,
            l=l,
            w=w,
            t=t,
        )

        if len(refined) >= 2:
            return refined

        return views

    def _repair_projected_views(
        self,
        msp,
        views: List[Dict],
        l: float,
        w: float,
        t: float,
    ) -> List[Dict]:
        """修复缺失或与其他视图重叠的三视图框。"""
        if len(views) < 2:
            return views

        by_type = {view['view_type']: dict(view) for view in views}
        normalized = {}
        for view_type, view in by_type.items():
            normalized[view_type] = view.get('normalized_bbox') or self._normalize_view_bbox(
                view_type,
                view['bbox'],
                l,
                w,
                t,
            )

        top_bbox = normalized.get('top_view')
        side_bbox = normalized.get('side_view')
        front_bbox = normalized.get('front_view')

        if top_bbox and side_bbox:
            needs_front_repair = (
                front_bbox is None or
                self._bbox_overlap_ratio(front_bbox, top_bbox) >= 0.6 or
                self._bbox_overlap_ratio(front_bbox, side_bbox) >= 0.6
            )
            if needs_front_repair:
                synthesized_front = self._synthesize_front_view_bbox(
                    msp=msp,
                    top_bbox=top_bbox,
                    side_bbox=side_bbox,
                    l=l,
                    w=w,
                    t=t,
                )
                if synthesized_front:
                    by_type['front_view'] = {
                        'bbox': synthesized_front,
                        'normalized_bbox': synthesized_front,
                        'width': synthesized_front[2] - synthesized_front[0],
                        'height': synthesized_front[3] - synthesized_front[1],
                        'view_type': 'front_view',
                        'match_score': self._calculate_match_score(
                            synthesized_front[2] - synthesized_front[0],
                            synthesized_front[3] - synthesized_front[1],
                            l,
                            w,
                            t,
                        ),
                        'source': 'projection_synth',
                    }
                    normalized['front_view'] = synthesized_front

        return sorted(
            by_type.values(),
            key=lambda view: view.get('match_score', 0.0),
            reverse=True,
        )

    def _synthesize_front_view_bbox(
        self,
        msp,
        top_bbox: Tuple[float, float, float, float],
        side_bbox: Tuple[float, float, float, float],
        l: float,
        w: float,
        t: float,
    ) -> Optional[Tuple[float, float, float, float]]:
        """由俯视图和侧视图投影回推正视图边界。"""
        expected_size = self._get_expected_view_size(
            'front_view',
            top_bbox[2] - top_bbox[0],
            side_bbox[2] - side_bbox[0],
            l,
            w,
            t,
        )
        if expected_size is None:
            return None

        target_width, target_height = expected_size
        top_center_x, top_center_y = self._bbox_center(top_bbox)
        side_center_x, side_center_y = self._bbox_center(side_bbox)

        # 常见排布: 俯视图与侧视图同行，正视图位于俯视图下方。
        if abs(side_center_x - top_center_x) >= abs(side_center_y - top_center_y):
            y_pair = self._find_projection_span(
                msp=msp,
                axis='y',
                fixed_range=(top_bbox[0], top_bbox[2]),
                limit=top_bbox[1],
                direction='below',
                target_span=target_height,
            )
            if y_pair:
                return (top_bbox[0], y_pair[0], top_bbox[2], y_pair[1])

            return (
                top_bbox[0],
                top_bbox[1] - target_height,
                top_bbox[2],
                top_bbox[1],
            )

        x_pair = self._find_projection_span(
            msp=msp,
            axis='x',
            fixed_range=(top_bbox[1], top_bbox[3]),
            limit=top_bbox[2],
            direction='right',
            target_span=target_width,
        )
        if x_pair:
            return (x_pair[0], top_bbox[1], x_pair[1], top_bbox[3])

        return (
            top_bbox[2],
            top_bbox[1],
            top_bbox[2] + target_width,
            top_bbox[3],
        )

    def _find_projection_span(
        self,
        msp,
        axis: str,
        fixed_range: Tuple[float, float],
        limit: float,
        direction: str,
        target_span: float,
    ) -> Optional[Tuple[float, float]]:
        """从局部实体坐标中寻找与目标跨度最接近的一组投影视图边界。"""
        coordinates = self._collect_projection_coordinates(
            msp=msp,
            axis=axis,
            fixed_range=fixed_range,
        )
        if len(coordinates) < 2:
            return None

        tolerance = max(self._calculate_dynamic_tolerance(target_span), 8.0)
        candidates = []
        for start in coordinates:
            for end in coordinates:
                if end <= start:
                    continue

                span = end - start
                if abs(span - target_span) > tolerance:
                    continue

                if direction == 'below' and end >= limit - 1.0:
                    continue
                if direction == 'right' and start <= limit + 1.0:
                    continue

                edge_hits = coordinates.count(start) + coordinates.count(end)
                gap_penalty = abs(span - target_span) * 10.0
                limit_penalty = abs(limit - end) if direction == 'below' else abs(start - limit)
                score = edge_hits * 100.0 - gap_penalty - limit_penalty
                candidates.append((score, start, end))

        if not candidates:
            return None

        _, start, end = max(candidates, key=lambda item: item[0])
        return (start, end)

    def _collect_projection_coordinates(
        self,
        msp,
        axis: str,
        fixed_range: Tuple[float, float],
    ) -> List[float]:
        coordinates: List[float] = []
        min_fixed, max_fixed = fixed_range

        def overlaps(entity_min: float, entity_max: float) -> bool:
            return not (entity_max < min_fixed or entity_min > max_fixed)

        for entity in msp.query('LINE LWPOLYLINE POLYLINE'):
            try:
                bbox = self._get_entity_bbox(entity)
                if not bbox:
                    continue

                fixed_min, fixed_max = (bbox[0], bbox[2]) if axis == 'y' else (bbox[1], bbox[3])
                if not overlaps(fixed_min, fixed_max):
                    continue

                if entity.dxftype() == 'LINE':
                    if axis == 'y':
                        coordinates.extend([float(entity.dxf.start[1]), float(entity.dxf.end[1])])
                    else:
                        coordinates.extend([float(entity.dxf.start[0]), float(entity.dxf.end[0])])
                    continue

                points = list(entity.get_points(format='xy'))
                if axis == 'y':
                    coordinates.extend(float(point[1]) for point in points)
                else:
                    coordinates.extend(float(point[0]) for point in points)
            except Exception:
                continue

        rounded = [round(value, 1) for value in coordinates]
        return sorted(rounded)

    def _build_layout_anchors(
        self,
        identifier,
        msp,
        views: List[Dict],
        raw_parallel_candidates: Dict[str, List[Dict]]
    ) -> Dict[str, Dict]:
        """从粗矩形里提取左上、左下、右上三个版式槽位。"""
        coarse_views = []

        try:
            rectangles = identifier._find_rectangles(msp)
        except Exception:
            rectangles = []

        for rect in rectangles or []:
            bounds = rect.get('bounds')
            if not bounds:
                continue
            coarse_views.append(self._make_view_candidate(
                bbox=(
                    float(bounds['min_x']),
                    float(bounds['min_y']),
                    float(bounds['max_x']),
                    float(bounds['max_y']),
                ),
                source='rectangle_anchor',
            ))

        coarse_views.extend([
            self._make_view_candidate(view['bbox'], source='view_identifier_anchor')
            for view in views
        ])

        for candidate_list in raw_parallel_candidates.values():
            for raw_candidate in candidate_list[:8]:
                bounds = raw_candidate.get('bounds')
                if not bounds:
                    continue
                coarse_views.append(self._make_view_candidate(
                    bbox=(
                        float(bounds['min_x']),
                        float(bounds['min_y']),
                        float(bounds['max_x']),
                        float(bounds['max_y']),
                    ),
                    source='parallel_anchor',
                ))

        if len(coarse_views) < 2:
            return {}

        grouped = self._group_candidates_by_layout(coarse_views)
        anchors = {}
        for slot_name, slot_candidates in grouped.items():
            if slot_candidates:
                anchors[slot_name] = max(
                    slot_candidates,
                    key=lambda item: item['width'] * item['height']
                )
        return anchors

    def _get_slot_candidates(
        self,
        candidate_cache: Dict[Tuple[str, str], List[Dict]],
        view_type: str,
        slot_name: str,
        anchors: Dict[str, Dict],
        current_views: List[Dict],
        parallel_candidates: List[Dict],
        l: float,
        w: float,
        t: float,
    ) -> List[Dict]:
        cache_key = (view_type, slot_name)
        if cache_key not in candidate_cache:
            anchor = anchors.get(slot_name)
            if not anchor:
                candidate_cache[cache_key] = []
            else:
                candidate_cache[cache_key] = self._collect_refinement_candidates(
                    view_type=view_type,
                    slot_name=slot_name,
                    anchor=anchor,
                    anchors=anchors,
                    current_views=current_views,
                    parallel_candidates=parallel_candidates,
                    l=l,
                    w=w,
                    t=t,
                )
        return candidate_cache[cache_key]

    def _select_top_slot(
        self,
        anchors: Dict[str, Dict],
        l: float,
        w: float,
        t: float
    ) -> Optional[str]:
        if anchors.get('left_top'):
            return 'left_top'

        best_slot = None
        best_score = None
        for slot_name, anchor in anchors.items():
            score = self._calculate_view_dimension_error(
                'top_view', anchor['width'], anchor['height'], l, w, t
            )
            if best_score is None or score < best_score:
                best_score = score
                best_slot = slot_name
        return best_slot

    def _assign_front_and_side_views(
        self,
        candidate_cache: Dict[Tuple[str, str], List[Dict]],
        anchors: Dict[str, Dict],
        current_views: List[Dict],
        raw_parallel_candidates: Dict[str, List[Dict]],
        top_slot: Optional[str],
        l: float,
        w: float,
        t: float,
    ) -> Dict[str, Dict]:
        slot_priority = ['left_bottom', 'right_top', 'right_bottom', 'left_top']
        available_slots = [
            slot_name for slot_name in slot_priority
            if slot_name in anchors and slot_name != top_slot
        ]

        best_assignment = {}
        best_score = None
        for front_slot in available_slots:
            front_candidates = self._get_slot_candidates(
                candidate_cache,
                'front_view',
                front_slot,
                anchors,
                current_views,
                raw_parallel_candidates.get('front_view', []),
                l,
                w,
                t,
            )
            best_front = self._pick_best_candidate(front_candidates)
            if not best_front:
                continue

            for side_slot in available_slots:
                if side_slot == front_slot:
                    continue
                side_candidates = self._get_slot_candidates(
                    candidate_cache,
                    'side_view',
                    side_slot,
                    anchors,
                    current_views,
                    raw_parallel_candidates.get('side_view', []),
                    l,
                    w,
                    t,
                )
                best_side = self._pick_best_candidate(side_candidates)
                if not best_side:
                    continue

                score = (
                    best_front['refine_score'] +
                    best_side['refine_score'] +
                    self._slot_usage_penalty(front_slot) +
                    self._slot_usage_penalty(side_slot)
                )
                if best_score is None or score < best_score:
                    best_score = score
                    best_assignment = {
                        'front_view': best_front,
                        'side_view': best_side,
                    }

        return best_assignment

    def _prefer_current_view_candidate(
        self,
        view_type: str,
        selected_candidate: Dict,
        current_views: List[Dict],
        l: float,
        w: float,
        t: float,
    ) -> Dict:
        current_candidate = next(
            (view for view in current_views if view.get('view_type') == view_type),
            None
        )
        if not current_candidate:
            return selected_candidate

        selected_error = self._calculate_view_dimension_error(
            view_type,
            selected_candidate['width'],
            selected_candidate['height'],
            l,
            w,
            t,
        )
        current_error = self._calculate_view_dimension_error(
            view_type,
            current_candidate['width'],
            current_candidate['height'],
            l,
            w,
            t,
        )
        expected_size = self._get_expected_view_size(
            view_type,
            current_candidate['width'],
            current_candidate['height'],
            l,
            w,
            t,
        )
        if expected_size is not None:
            tolerance = max(
                self._calculate_dynamic_tolerance(expected_size[0]),
                self._calculate_dynamic_tolerance(expected_size[1]),
                20.0,
            )
        else:
            tolerance = 20.0

        if (
            view_type in {'front_view', 'side_view'} and
            current_candidate.get('source') in {'view_identifier', 'view_identifier_anchor', 'rectangle_anchor'} and
            current_error <= selected_error + min(tolerance * 0.2, 5.0)
        ):
            return current_candidate

        if current_error <= selected_error:
            return current_candidate
        return selected_candidate

    @staticmethod
    def _slot_usage_penalty(slot_name: str) -> float:
        penalties = {
            'left_bottom': 0.0,
            'right_top': 0.0,
            'right_bottom': 40.0,
            'left_top': 80.0,
        }
        return penalties.get(slot_name, 100.0)

    @staticmethod
    def _pick_best_candidate(candidates: List[Dict]) -> Optional[Dict]:
        if not candidates:
            return None
        return min(candidates, key=lambda item: item['refine_score'])

    def _collect_refinement_candidates(
        self,
        view_type: str,
        slot_name: str,
        anchor: Dict,
        anchors: Dict[str, Dict],
        current_views: List[Dict],
        parallel_candidates: List[Dict],
        l: float,
        w: float,
        t: float,
    ) -> List[Dict]:
        """收集指定槽位内的细化候选框，并按尺寸与位置综合打分。"""
        candidates = []
        seen = set()

        def add_candidate(candidate_bbox, source: str):
            candidate = self._make_view_candidate(candidate_bbox, source)
            if not self._candidate_fits_slot(candidate, anchor):
                return
            key = tuple(round(value, 3) for value in candidate['bbox'])
            if key in seen:
                return
            seen.add(key)

            dim_error = self._calculate_view_dimension_error(
                view_type, candidate['width'], candidate['height'], l, w, t
            )
            center_distance = self._calculate_center_distance(
                candidate['bbox'], anchor['bbox']
            )
            overlap_penalty = 0.0
            overlap_ratio = self._bbox_overlap_ratio(candidate['bbox'], anchor['bbox'])
            if overlap_ratio < 0.15:
                overlap_penalty = (0.15 - overlap_ratio) * 200.0
            cross_slot_penalty = self._calculate_cross_slot_penalty(
                candidate, slot_name, anchors
            )
            source_penalty = self._source_preference_penalty(candidate.get('source', ''))
            candidate['refine_score'] = (
                dim_error * 10.0 +
                center_distance * 0.25 +
                overlap_penalty +
                cross_slot_penalty +
                source_penalty
            )
            candidates.append(candidate)

        add_candidate(anchor['bbox'], anchor['source'])

        for view in current_views:
            add_candidate(view['bbox'], view.get('source', 'view_identifier'))

        for raw_candidate in parallel_candidates:
            bounds = raw_candidate.get('bounds')
            if not bounds:
                continue
            add_candidate((
                float(bounds['min_x']),
                float(bounds['min_y']),
                float(bounds['max_x']),
                float(bounds['max_y']),
            ), 'parallel_lines')

        return candidates

    def _group_candidates_by_layout(self, candidates: List[Dict]) -> Dict[str, List[Dict]]:
        """按左上、左下、右上、右下对候选框分组。"""
        tolerance = 5.0
        avg_x = sum(self._bbox_center(item['bbox'])[0] for item in candidates) / len(candidates)
        avg_y = sum(self._bbox_center(item['bbox'])[1] for item in candidates) / len(candidates)
        grouped = {
            'left_top': [],
            'left_bottom': [],
            'right_top': [],
            'right_bottom': [],
        }

        for candidate in candidates:
            cx, cy = self._bbox_center(candidate['bbox'])
            is_left = (cx < avg_x - tolerance) or (abs(cx - avg_x) <= tolerance)
            is_top = (cy > avg_y + tolerance) or (abs(cy - avg_y) <= tolerance)

            if is_left and is_top:
                grouped['left_top'].append(candidate)
            elif is_left:
                grouped['left_bottom'].append(candidate)
            elif is_top:
                grouped['right_top'].append(candidate)
            else:
                grouped['right_bottom'].append(candidate)

        return grouped

    def _candidate_fits_slot(self, candidate: Dict, anchor: Dict) -> bool:
        """判断候选框是否位于当前槽位附近。"""
        ax1, ay1, ax2, ay2 = anchor['bbox']
        padding_x = max((ax2 - ax1) * 0.45, 25.0)
        padding_y = max((ay2 - ay1) * 0.45, 25.0)
        cx, cy = self._bbox_center(candidate['bbox'])
        return (
            ax1 - padding_x <= cx <= ax2 + padding_x and
            ay1 - padding_y <= cy <= ay2 + padding_y
        )

    def _calculate_cross_slot_penalty(
        self,
        candidate: Dict,
        slot_name: str,
        anchors: Dict[str, Dict]
    ) -> float:
        """候选框如果更靠近其他槽位，则提高惩罚，避免串槽。"""
        own_anchor = anchors.get(slot_name)
        if not own_anchor:
            return 0.0

        own_distance = self._calculate_center_distance(candidate['bbox'], own_anchor['bbox'])
        nearest_other = None
        for other_slot, other_anchor in anchors.items():
            if other_slot == slot_name:
                continue
            distance = self._calculate_center_distance(candidate['bbox'], other_anchor['bbox'])
            if nearest_other is None or distance < nearest_other:
                nearest_other = distance

        if nearest_other is None or own_distance <= nearest_other:
            return 0.0
        return (own_distance - nearest_other) * 0.5

    @staticmethod
    def _source_preference_penalty(source: str) -> float:
        penalties = {
            'rectangle_anchor': -25.0,
            'view_identifier': -20.0,
            'view_identifier_anchor': -18.0,
            'parallel_anchor': -8.0,
            'parallel_lines': 8.0,
        }
        return penalties.get(source, 0.0)

    def _calculate_view_dimension_error(
        self,
        view_type: str,
        width: float,
        height: float,
        l: float,
        w: float,
        t: float
    ) -> float:
        """计算候选框与目标视图尺寸的误差，越小越好。"""
        dimension_pairs = {
            'top_view': [(l, w), (w, l)],
            'front_view': [(l, t), (t, l)],
            'side_view': [(w, t), (t, w)],
        }
        candidates = dimension_pairs.get(view_type, [])
        if not candidates:
            return float('inf')

        return min(
            abs(width - expected_w) + abs(height - expected_h)
            for expected_w, expected_h in candidates
        )

    @staticmethod
    def _make_view_candidate(
        bbox: Tuple[float, float, float, float],
        source: str
    ) -> Dict:
        width = float(bbox[2] - bbox[0])
        height = float(bbox[3] - bbox[1])
        return {
            'bbox': tuple(float(value) for value in bbox),
            'width': width,
            'height': height,
            'source': source,
        }

    @staticmethod
    def _bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        return (
            (bbox[0] + bbox[2]) / 2.0,
            (bbox[1] + bbox[3]) / 2.0,
        )

    def _calculate_center_distance(
        self,
        bbox1: Tuple[float, float, float, float],
        bbox2: Tuple[float, float, float, float]
    ) -> float:
        cx1, cy1 = self._bbox_center(bbox1)
        cx2, cy2 = self._bbox_center(bbox2)
        return ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
    
    def _find_polyline_views(
        self, 
        msp, 
        l: float, w: float, t: float,
        tol_l: float, tol_w: float, tol_t: float
    ) -> List[Dict]:
        """查找闭合多段线视图"""
        views = []
        
        for entity in msp.query('LWPOLYLINE POLYLINE'):
            if entity.dxftype() == 'LWPOLYLINE' and entity.closed:
                try:
                    points = list(entity.get_points(format='xy'))
                    if not points:
                        continue
                    
                    # 计算边界框
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    bbox = (min(xs), min(ys), max(xs), max(ys))
                    
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    area = width * height
                    
                    # 过滤太小的区域
                    if area < 100:
                        continue
                    
                    # 匹配视图类型
                    view_type = self._match_view_type(
                        width, height, l, w, t, tol_l, tol_w, tol_t
                    )
                    
                    if view_type:
                        views.append({
                            'bbox': bbox,
                            'width': width,
                            'height': height,
                            'view_type': view_type,
                            'match_score': self._calculate_match_score(width, height, l, w, t),
                            'source': 'polyline'
                        })
                        
                except Exception:
                    continue
        
        return views
    
    def _find_line_rectangle_views(
        self, 
        msp, 
        l: float, w: float, t: float,
        tol_l: float, tol_w: float, tol_t: float
    ) -> List[Dict]:
        """查找LINE组成的矩形视图"""
        views = []
        
        # 按图层分组LINE
        lines_by_layer = {}
        for entity in msp.query('LINE'):
            layer = entity.dxf.layer
            if layer not in lines_by_layer:
                lines_by_layer[layer] = []
            lines_by_layer[layer].append(entity)
        
        # 对每个图层识别矩形
        for layer, lines in lines_by_layer.items():
            if len(lines) < 4:
                continue
            
            # 分类为水平线和垂直线
            horizontal = []
            vertical = []
            
            for line in lines:
                dx = abs(line.dxf.end[0] - line.dxf.start[0])
                dy = abs(line.dxf.end[1] - line.dxf.start[1])
                
                if dx > dy * 10:
                    horizontal.append(line)
                elif dy > dx * 10:
                    vertical.append(line)
            
            if len(horizontal) >= 2 and len(vertical) >= 2:
                # 计算边界框
                xs = []
                ys = []
                for line in horizontal + vertical:
                    xs.extend([line.dxf.start[0], line.dxf.end[0]])
                    ys.extend([line.dxf.start[1], line.dxf.end[1]])
                
                bbox = (min(xs), min(ys), max(xs), max(ys))
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                area = width * height
                
                # 过滤不合理的尺寸
                if 10 < width < 5000 and 10 < height < 5000 and area > 100:
                    # 匹配视图类型
                    view_type = self._match_view_type(
                        width, height, l, w, t, tol_l, tol_w, tol_t
                    )
                    
                    if view_type:
                        views.append({
                            'bbox': bbox,
                            'width': width,
                            'height': height,
                            'view_type': view_type,
                            'match_score': self._calculate_match_score(width, height, l, w, t),
                            'source': 'line_rectangle',
                            'layer': layer
                        })
        
        return views
    
    def _match_view_type(
        self, 
        width: float, height: float,
        l: float, w: float, t: float,
        tol_l: float, tol_w: float, tol_t: float
    ) -> Optional[str]:
        """
        匹配视图类型
        
        Returns:
            '主视图' | '侧视图' | '俯视图' | None
        """
        # 主视图 (L×W)
        if (abs(width - l) < tol_l and abs(height - w) < tol_w) or \
           (abs(width - w) < tol_w and abs(height - l) < tol_l):
            return '主视图'
        
        # 侧视图 (T×W)
        elif (abs(width - t) < tol_t and abs(height - w) < tol_w) or \
             (abs(width - w) < tol_w and abs(height - t) < tol_t):
            return '侧视图'
        
        # 俯视图 (L×T)
        elif (abs(width - l) < tol_l and abs(height - t) < tol_t) or \
             (abs(width - t) < tol_t and abs(height - l) < tol_l):
            return '俯视图'
        
        return None
    
    def _draw_material_box(
        self, 
        msp, 
        doc, 
        bbox: Tuple[float, float, float, float], 
        layer_name: str
    ):
        """绘制CAD标准板料线"""
        x1, y1, x2, y2 = bbox
        
        # 确保DASHED线型存在
        linetype = 'DASHED'
        if linetype not in doc.linetypes:
            try:
                doc.linetypes.new(linetype, dxfattribs={
                    'description': 'Dashed line',
                    'pattern': [6.0, -3.0]
                })
            except Exception:
                linetype = 'CONTINUOUS'
        
        # 创建图层
        if layer_name not in doc.layers:
            doc.layers.new(layer_name, dxfattribs={
                'color': 252,  # CAD标准252号色
                'linetype': linetype
            })
        
        # 绘制闭合矩形
        points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
        msp.add_lwpolyline(points, dxfattribs={
            'layer': layer_name,
            'color': 252,
            'linetype': linetype,
            'closed': True
        })
    
    @staticmethod
    def _calculate_dynamic_tolerance(dimension: float, relative_error: float = 0.05) -> float:
        """
        计算动态容差
        
        Args:
            dimension: 目标尺寸
            relative_error: 相对误差（默认5%）
        
        Returns:
            容差值
        """
        min_tolerance = 2.0
        max_tolerance = 20.0
        tolerance = dimension * relative_error
        return max(min_tolerance, min(tolerance, max_tolerance))
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()
    
    def print_stats(self):
        """打印统计信息"""
        self.logger.info("=" * 60)
        self.logger.info("📊 板料线添加统计")
        self.logger.info("=" * 60)
        self.logger.info(f"   总计: {self.stats['total']} 个子图")
        self.logger.info(f"   成功: {self.stats['success']} 个")
        self.logger.info(f"   跳过: {self.stats['skipped']} 个")
        self.logger.info(f"   失败: {self.stats['failed']} 个")
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['success'] / self.stats['total']) * 100
            self.logger.info(f"   成功率: {success_rate:.1f}%")
        
        self.logger.info("=" * 60)
