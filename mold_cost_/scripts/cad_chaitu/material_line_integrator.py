#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
板料线集成模块
为拆图生成的子图DXF文件添加板料线
"""

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
            
            # 2. 检查是否已存在板料线（避免重复添加）
            if self._has_material_lines(msp):
                self.logger.info(f"  ℹ️ {sub_code}: 已存在板料线，跳过添加")
                self.stats['skipped'] += 1
                return True
            
            # 3. 查找视图并添加板料线
            lines_added = self._find_views_and_add_lines(
                msp, doc, lwt, sub_code, part_info
            )
            
            if lines_added > 0:
                # 4. 保存DXF（覆盖原文件）
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
    
    def _has_material_lines(self, msp) -> bool:
        """检查是否已存在板料线"""
        for entity in msp.query('LINE LWPOLYLINE POLYLINE'):
            layer = entity.dxf.layer
            if 'MATERIAL_LINE' in layer.upper():
                return True
        return False
    
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
        
        # 1. 查找闭合多段线视图
        polyline_views = self._find_polyline_views(
            msp, l, w, t, tolerance_l, tolerance_w, tolerance_t
        )
        
        # 2. 查找LINE组成的矩形视图
        line_views = self._find_line_rectangle_views(
            msp, l, w, t, tolerance_l, tolerance_w, tolerance_t
        )
        
        # 合并所有视图
        all_views = polyline_views + line_views
        
        if not all_views:
            return 0
        
        # 3. 视图去重（每种类型只添加一次）
        view_types_added = set()
        
        for view in all_views:
            view_type = view['view_type']
            bbox = view['bbox']
            
            # 去重
            if view_type in view_types_added:
                continue
            
            # 添加板料线
            self._draw_material_box(
                msp, doc, bbox, 
                f"MATERIAL_LINE_{sub_code}_{view_type.upper()}"
            )
            
            view_types_added.add(view_type)
            lines_added += 1
            
            self.logger.debug(
                f"    ✓ {view_type}: "
                f"{view['width']:.1f}x{view['height']:.1f}mm"
            )
        
        return lines_added
    
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
