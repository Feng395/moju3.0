"""Src-owned 切割轮廓检测实现。"""

import math
import re
from collections import defaultdict
from typing import Dict, List, Tuple


class RelaxedCuttingDetector:
    """放宽的切割轮廓检测器"""

    def __init__(self):
        self.cutting_colors = set(range(1, 256))
        self.BYLAYER_COLOR = 256
        self.geometric_entities = {"LINE", "CIRCLE", "ARC", "LWPOLYLINE", "POLYLINE", "SPLINE", "ELLIPSE"}
        self.exclude_layer_patterns = [
            r"^text$",
            r"^dimension$",
            r"^dim$",
            r"^annotation$",
            r"^center$",
            r"^construction$",
            r"^hidden$",
            r"^dashed$",
        ]

    def detect_cutting_contours_in_region(self, bounds: Dict, entities: List, layer_colors: Dict) -> Dict:
        """检测区域内切割轮廓"""
        region_entities = self._get_entities_in_bounds(entities, bounds)
        red_entities = []
        for entity in region_entities:
            if self._should_exclude_entity(entity):
                continue
            color = entity.get("entity_color", self.BYLAYER_COLOR)
            if color == self.BYLAYER_COLOR:
                color = layer_colors.get(entity.get("layer", ""), self.BYLAYER_COLOR)
            entity["final_color"] = color

            if self._is_geometric_entity_relaxed(entity):
                red_entities.append(entity)

        analysis = self._generate_cutting_analysis(red_entities)
        reference_indexes = self._identify_reference_points(red_entities)
        analysis["reference_points"] = reference_indexes
        analysis["reference_count"] = len(reference_indexes)
        return analysis

    def _get_entities_in_bounds(self, entities: List[Dict], bounds: Dict) -> List[Dict]:
        """获取区域内实体"""
        results = []
        min_x, max_x = bounds["min_x"], bounds["max_x"]
        min_y, max_y = bounds["min_y"], bounds["max_y"]
        for info in entities:
            center = info.get("center")
            if center is None:
                continue
            center_x, center_y = center
            if min_x <= center_x <= max_x and min_y <= center_y <= max_y:
                results.append(info)
        return results

    def _should_exclude_entity(self, entity_info: Dict) -> bool:
        """排除不需要的实体"""
        layer = (entity_info.get("layer") or "").lower()
        for pattern in self.exclude_layer_patterns:
            if re.match(pattern, layer, re.IGNORECASE):
                return True
        return False

    def _is_geometric_entity_relaxed(self, entity_info: Dict) -> bool:
        """放宽的几何实体判断"""
        if entity_info.get("type", "") not in self.geometric_entities:
            return False

        color = entity_info.get("final_color", self.BYLAYER_COLOR)
        if color not in self.cutting_colors and color != self.BYLAYER_COLOR:
            return False

        linetype = (entity_info.get("linetype", "ByLayer") or "").lower()
        excluded_linetypes = {"hidden", "dashed", "center"}
        return linetype not in excluded_linetypes

    def _get_contour_types(self, contours: List[Dict]) -> Dict[str, int]:
        """轮廓类型统计"""
        distribution = defaultdict(int)
        for contour in contours:
            distribution[contour.get("type", "UNKNOWN")] += 1
        return dict(distribution)

    def _generate_cutting_analysis(self, contours: List[Dict]) -> Dict:
        """生成切割分析结果"""
        analysis = {
            "summary": "未检测到切割轮廓",
            "contour_count": 0,
            "total_cutting_length": 0.0,
            "avg_length": 0.0,
            "min_length": 0.0,
            "max_length": 0.0,
            "type_distribution": {},
        }
        if not contours:
            return analysis

        perimeters = [contour.get("perimeter", 0.0) for contour in contours if contour.get("perimeter", 0.0) > 0.0]
        total_length = sum(perimeters)
        analysis["contour_count"] = len(contours)
        analysis["total_cutting_length"] = total_length
        analysis["type_distribution"] = self._get_contour_types(contours)
        if perimeters:
            analysis["avg_length"] = total_length / len(perimeters)
            analysis["min_length"] = min(perimeters)
            analysis["max_length"] = max(perimeters)
            analysis["summary"] = f"检测到{analysis['contour_count']}个切割轮廓，总长度{total_length:.2f}mm"
        else:
            analysis["summary"] = f"检测到{analysis['contour_count']}个切割轮廓，但未获取到有效长度数据"
        return analysis

    def _identify_reference_points(self, red_entities: List[Dict]) -> List[int]:
        """识别基准点"""
        circles = [index for index, entity in enumerate(red_entities) if entity.get("type") == "CIRCLE"]
        if len(circles) < 3:
            return []
        for i in range(len(circles)):
            for j in range(i + 1, len(circles)):
                for k in range(j + 1, len(circles)):
                    indexes = [circles[i], circles[j], circles[k]]
                    entities = [red_entities[index] for index in indexes]
                    perimeters = [entity.get("perimeter", 0.0) for entity in entities]
                    if not perimeters or any(perimeter <= 0 for perimeter in perimeters):
                        continue
                    if not all(abs(perimeters[0] - perimeter) < 0.5 for perimeter in perimeters[1:]):
                        continue
                    centers = [entity.get("center", (0.0, 0.0)) for entity in entities]
                    if self._is_equal_right_triangle(centers):
                        return indexes
        return []

    def _is_equal_right_triangle(self, centers: List[Tuple[float, float]]) -> bool:
        """判断是否为等腰直角三角形（基准点验证）"""
        if len(centers) != 3:
            return False
        distances = []
        for first in range(3):
            for second in range(first + 1, 3):
                x1, y1 = centers[first]
                x2, y2 = centers[second]
                distances.append(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
        distances.sort()
        if len(distances) != 3:
            return False
        tolerance = 0.5
        equal_sides = abs(distances[0] - distances[1]) < tolerance
        hypotenuse = distances[2]
        return equal_sides and abs(hypotenuse - distances[0] * 1.414) < tolerance
