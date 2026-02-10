"""
文件内容：读取DXF文件，识别视图轮廓并创建板料线
最后修改时间：2026-02-02
修改人：王霞、佟坤远
修改内容：
    添加对椭圆（ELLIPSE）和样条曲线（SPLINE）的支持（仅识别起点和终点）
"""

from __future__ import annotations
import ezdxf
import math
import os
import datetime
import numpy as np
import networkx as nx
import re
import argparse
import itertools
import sys
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import Counter
import json

@dataclass
class ViewInfo:
    """视图信息"""
    name: str
    entity: any
    bbox: Tuple[float, float, float, float]  # (x_min, y_min, x_max, y_max)
    area: float
    center: Tuple[float, float]
    vertices: List[Tuple[float, float]]
    layer: str
@dataclass
class LineInfo:
    """线段信息"""
    entity: any
    start: Tuple[float, float]
    end: Tuple[float, float]
    angle: float  # 角度，0-180度
    length: float
    layer: str

# ==============================全局变量============================
IS_POINT_OVERLAP_TOLERANCE = 1e-1  # 点重合容差

# ========================分中判断函数===============================
def check_need_centering(msp) -> bool:
    """
    判断DXF模型空间msp中的注释内容是否需要分中。
    如果注释中包含“分中加工”或“分中备料”，则返回True，否则返回False。
    """
    keywords = ["分中加工", "分中备料"]
    for entity in msp:
        if entity.dxftype() == "TEXT" or entity.dxftype() == "MTEXT":
            text = entity.plain_text() if hasattr(entity, "plain_text") else entity.text
            if any(kw in text for kw in keywords):
                return True
    return False


# ===================================================================
# ========================提取并解析lwt===============================
def read_lwt_from_csv(csv_path: str, filename: str) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    """
    从CSV读取该零件的L、W、T及相关信息
    :param csv_path: CSV文件路径
    :param filename: 当前文件名
    :return: (L, W, T, 是否具有LWT值)
    """
    try:
        if not os.path.exists(csv_path):
            # print(f"Warning: CSV file not found: {csv_path}")
            return None, None, None, "CSV未找到"

        # 尝试不同编码读取CSV
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(csv_path, encoding='gbk')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='gb18030')
        
        # 尝试匹配文件名，去除扩展名进行比较
        base_name = os.path.splitext(os.path.basename(filename))[0]
        
        # 假设CSV中的列名为：'零件名', 'L', 'W', 'T', '是否缺失LWT值', '是否有多个加工说明'
        # 清理列名空格
        df.columns = df.columns.str.strip()      
        if '零件名' not in df.columns:
             return None, None, None, "CSV中无零件名列"

        matched_row = df[df['零件名'].astype(str).str.strip() == base_name]
        
        if matched_row.empty:
            # 尝试直接匹配（万一CSV里带扩展名）
            matched_row = df[df['零件名'].astype(str).str.strip() == os.path.basename(filename)]
            
        if matched_row.empty:
            return None, None, None, "CSV中未找到匹配行"
            
        row = matched_row.iloc[0]       
        def get_float(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                return None
        l_val = get_float(row.get('L'))
        w_val = get_float(row.get('W'))
        t_val = get_float(row.get('T'))       
        has_lwt = str(row.get('是否具有LWT值', ''))
        return l_val, w_val, t_val, has_lwt
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None, None, None, f"读取错误: {str(e)}"

def parse_lwt_info(csv_info, note_info):
    """
    解析L/W/T信息，对比来自csv和注释的信息，决定最终使用哪种信息
    :param csv_info: 来自CSV的信息，格式为 (L, W, T, has_lwt)
    :param note_info: 来自注释的信息，格式为list或字符串
    :return: 解析后的msg, 解析后的L/W/T字典
    """
    l_val, w_val, t_val, has_lwt = csv_info
    msg = ''
    # CSV未找到、CSV中无零件名列、未找到匹配行
    if has_lwt in ['CSV未找到', 'CSV中无零件名列', 'CSV中未找到匹配行']:
        if note_info and isinstance(note_info, dict):
            msg = f"{has_lwt}，改为从注释中提取L/W/T信息"
            return msg, note_info
        else:
            msg = f"{has_lwt}，且注释中无有效L/W/T信息，跳过处理"
            return msg, None
    # 存在多个加工说明：
    if note_info == 'MULTIPLE_LWT':
        msg = f"文件中存在多个LWT匹配项，跳过处理"
        return msg, None
    # 注释中包括“备料图”关键字：
    if note_info == 'SKIP_KEYWORD_DETECTED':
        msg = f"注释中检测到备料图关键字，跳过处理"
        return msg, None
    # 无LWT信息：
    if has_lwt == '否' and not note_info:
        msg = f"CSV和注释中均未找到L/W/T信息，跳过处理"
        return msg, None
    elif has_lwt == '是' and note_info and isinstance(note_info, dict):
        # 判断两个信息中的lwt是否一致
        if abs(l_val - note_info.get("L")) > 0.01 or abs(w_val - note_info.get("W")) > 0.01 or abs(t_val - note_info.get("T")) > 0.01:
            msg = f"CSV和注释中的L/W/T信息不一致，跳过处理"
            return msg, None
        else:
            return msg, {'L': l_val, 'W': w_val, 'T': t_val}
    elif has_lwt == '是' and l_val and w_val and t_val and (not note_info or not isinstance(note_info, dict)):
        return msg, {'L': l_val, 'W': w_val, 'T': t_val}
    elif has_lwt == '否' and note_info and isinstance(note_info, dict):
        return msg, note_info
    else:
        return '解析LWT遇到未知错误，跳过处理', None
    
def get_notes(file_path):
    """
    提取并输出LWT的值 (返回字典 {'L': float, 'W': float, 'T': float})
    """

    def parse_lwt(text_value: str) -> Optional[Dict[str, float]]:
        """解析 L/W/T 字符串，返回数值字典"""
        if not text_value:
            return None       
        result = {}
        # 查找数值和紧随其后的单位标志 (L, W, T)
        # 兼容格式: 32.00T, 110.0L, 87.0W 等，中间可能有分隔符或空格
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*([LWT])', text_value, re.IGNORECASE)    
        for val_str, unit in matches:
            try:
                val = float(val_str)
                unit_upper = unit.upper()
                result[unit_upper] = val
            except ValueError:
                pass           
        if not result:
            return None
        return result
    
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        # 定义正则模式：用于定位包含 L/W/T 组合的字符串
        # 匹配 L/W/T 的组合，不限顺序，分隔符支持 * 或 x
        n_num = r'\d+(?:\.\d+)?'  # 数值
        s_sep = r'\s*[x\*]+\s*'   # 分隔符
        
        # 构造 6 种排列组合
        p_list = []
        for p1, p2, p3 in [('L','W','T'), ('L','T','W'), ('W','L','T'), 
                           ('W','T','L'), ('T','L','W'), ('T','W','L')]:
            p_list.append(rf'{n_num}\s*{p1}{s_sep}{n_num}\s*{p2}{s_sep}{n_num}\s*{p3}')
        
        pattern = '|'.join(p_list)        
        found_notes = [] 
        # 遍历所有文本实体
        for entity in msp.query('TEXT MTEXT'):
            text_content = ""
            if entity.dxftype() == 'TEXT':
                text_content = entity.dxf.text
            elif entity.dxftype() == 'MTEXT':
                text_content = entity.text           
            # 清理文本（去除换行符等）
            text_content = text_content.replace('\n', ' ').strip()           
            # --- 检测备料图标记 ---
            if "备料图" in text_content:
                print(f"  [提示] 发现 '备料图' 标记，标记跳过")
                return "SKIP_KEYWORD_DETECTED"
            # 检查是否匹配模式
            match = re.search(pattern, text_content, re.IGNORECASE)           
            if match:
                note_str = match.group(0)
                parsed_dict = parse_lwt(note_str)
                if parsed_dict:
                    parsed_dict['raw'] = note_str # 保存原始字符串作为参考
                    
                    found_notes.append(parsed_dict)        
        # 判断是否发现多个 LWT
        if len(found_notes) > 1:
            print(f"  [提示] 发现 {len(found_notes)} 个匹配 L/W/T 格式的注释，判定为模糊标注")
            return "MULTIPLE_LWT"
        # 如果找到唯一的 LWT
        if found_notes:
            return found_notes[0]           
        print("  未找到匹配 L/W/T 格式的注释")
        return None
    except Exception as e:
        print(f"  提取注释失败: {e}")
        return None


# ===================================================================
# ===========================寻找坐标点相关============================
def find_ordinate_points(doc):
    """
    遍历指定图层，查找所有坐标标注点
    """
    msp = doc.modelspace()
    dimension_entities = list(msp.query('DIMENSION'))
    zero_points = extract_and_validate_zero_point(dimension_entities)
    if not zero_points:
        print("未找到有效零点坐标标注")
    else:
        print(">>过滤后的零点标注:", zero_points)
    return zero_points

def filter_zero_points_with_two_zeros(zero_points):
    """
    Args : zero_points (list): 点的列表，每个点是一个包含 x, y, z 坐标的元组。
    Returns : list: 仅包含重复率大于等于 2 的点的列表。
    """
    rounded_points = [(round(x, 3), round(y, 3), round(z, 3)) for x, y, z in zero_points]
    # 统计每个点的出现次数
    point_counts = Counter(rounded_points)
    # 保留重复率大于等于 2 的点
    filtered_points = [point for point, count in point_counts.items() if count >= 2]
    return filtered_points

def extract_and_validate_zero_point(dimension_entities: list):
    zero_points = []
    for entity in dimension_entities:
        # 遍历所有图层，不再限制特定图层
        # if hasattr(entity.dxf, 'actual_measurement'):
        #     print(entity.dxf.actual_measurement)
        if hasattr(entity.dxf, 'actual_measurement') and entity.dxf.actual_measurement == 0.0:
            point = get_dimension_point(entity)
            if point:
                zero_points.append(point)
    # print(">>找到的零点标注:", zero_points)
    zero_points = filter_zero_points_with_two_zeros(zero_points)
    return zero_points

def get_dimension_point(entity):
    try:
        return (entity.dxf.defpoint.x, entity.dxf.defpoint.y, entity.dxf.defpoint.z)
    except AttributeError:
        return None
    
def are_points_same(points):
    return all(round_point(point) == round_point(points[0]) for point in points)

def round_point(point):
    return tuple(round(coord, 2) for coord in point)


# ===================================================================
# ====================判断闭合区域用到的工具===========================
def is_points_in_matched_region(points: List[Tuple[float, float]], regions, tolerance=IS_POINT_OVERLAP_TOLERANCE) -> bool:
    """
    判断一组点是否全部在指定闭合区域内（包含边界），允许一定容差
    :param points: 点列表 [(x1, y1), (x2, y2), ...]
    :param regions: 闭合区域列表
    :param tolerance: 容差
    :return: True/False
    """
    count = len(regions)
    if count == 0:
        return False  # 没有区域可供判断
    
    for p in points:
        x, y = p
        in_counter = 0
        for r in regions:
            min_x, min_y, max_x, max_y = r.bbox        
            if (min_x - tolerance < x < max_x + tolerance
                and min_y - tolerance < y < max_y + tolerance):
                in_counter += 1
        if in_counter < count:
            return False  # 存在不在所有区域内的点
    return True

def get_spline_points(spline):
    """
    获取样条曲线的起点、终点列表
    :param spline: ezdxf SPLINE实体
    :return: 点列表 [(x1, y1), (x2, y2), ...]
    """
    cps = []
    try:
        if hasattr(spline, 'control_points'):
            cps = [tuple(map(float, p)) for p in spline.control_points]
    except Exception:
        cps = []
	# fit points
    fps = []
    try:
        if hasattr(spline, 'fit_points'):
            fps = [tuple(map(float, p)) for p in spline.fit_points]
    except Exception:
        fps = []

    # 尝试确定起点/终点：优先使用拟合点，其次使用控制点
    start = end = None
    if fps:
        start = fps[0]
        end = fps[-1]
    elif cps:
        start = cps[0]
        end = cps[-1]
    point_list = []
    if start is not None and end is not None:
        point_list = [(start[0], start[1]), (end[0], end[1])]

    return point_list

def get_ellipse_points(ellipse):
    """
    获取椭圆的起点、终点列表
    :param ellipse: ezdxf ELLIPSE实体
    :return: 点列表 [(x1, y1), (x2, y2), ...]
    """
    start = end = None
    def to_tuple(v):
        try:
            return (float(v[0]), float(v[1]), float(v[2]))
        except Exception:
            return (float(v.x), float(v.y), float(v.z))

    def add(u, v):
        return (u[0] + v[0], u[1] + v[1], u[2] + v[2])

    def mul(u, s):
        return (u[0] * s, u[1] * s, u[2] * s)

    def cross(u, v):
        return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])

    def norm(u):
        return math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])

    C = to_tuple(ellipse.dxf.center)
    A = to_tuple(ellipse.dxf.major_axis)
    a = norm(A)
    if a == 0:
        raise ValueError("ellipse major axis has zero length")

    ratio = float(getattr(ellipse.dxf, 'ratio', 1.0))
    b = a * ratio

    # 外挤向量（法向量），用于构造椭圆平面上的次轴方向
    N = to_tuple(getattr(ellipse.dxf, 'extrusion', (0, 0, 1)))
    minor_dir = cross(N, A)
    minor_norm = norm(minor_dir)
    if minor_norm == 0:
        # 退化：在 XY 平面上使用旋转90度作为次轴方向
        minor_dir = (-A[1], A[0], 0.0)
        minor_norm = norm(minor_dir)
        if minor_norm == 0:
            # 最后退化，使用 (0,0,0)
            minor_dir = (0.0, 0.0, 0.0)

    start_param = float(getattr(ellipse.dxf, 'start_param', 0.0))
    end_param = float(getattr(ellipse.dxf, 'end_param', 2 * math.pi))

    def point_at(t):
        major_term = mul(A, math.cos(t))
        if minor_norm != 0:
            minor_term = mul(minor_dir, (b / minor_norm) * math.sin(t))
        else:
            minor_term = (0.0, 0.0, 0.0)
        return add(add(C, major_term), minor_term)

    start_pt = point_at(start_param)
    end_pt = point_at(end_param)
    return [(start_pt[0], start_pt[1]), (end_pt[0], end_pt[1])]

def merge_edges(edges: List[Tuple[Tuple[float, float], Tuple[float, float]]], tolerance=IS_POINT_OVERLAP_TOLERANCE) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    拼接在同一条直线上并有共同端点或有重合区域的edge
    :param edges: 列表，保存线的起点和终点 [((x1, y1), (x2, y2)), ...]
    :param tolerance: 合并的容差
    :return: 拼接后的edges列表
    """
    if not edges:
        return []

    # 1. Group edges by line equation
    # 按照 (ux, uy, dist) 分组
    line_groups = {} 

    for p1, p2 in edges:
        x1, y1 = p1
        x2, y2 = p2
        
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        
        if length < 1e-9:
            continue # 忽略极短的线段
            
        # 归一化方向向量
        ux = dx / length
        uy = dy / length
        
        # 规范化方向：保证在 [0, pi) 范围内
        # 即保证 uy > 0, 或者 if uy=0 then ux > 0
        if uy < -1e-9 or (abs(uy) < 1e-9 and ux < -1e-9):
            ux = -ux
            uy = -uy
            
        # 计算原点到直线的有向距离 (叉积: x1*uy - y1*ux)
        # 该距离对于同一条直线上的点应该是常数
        dist = x1 * uy - y1 * ux
        
        # 使用简单的遍历查找来处理浮点数容差，避免直接用float做key
        found_group = False
        for key in line_groups.keys():
            k_ux, k_uy, k_dist = key
            
            # 检查方向是否平行 (点积接近1)
            dot = ux * k_ux + uy * k_uy
            if abs(dot) > 0.9999: 
                # 检查是否共线 (距离差在容差内)
                if abs(dist - k_dist) < tolerance:
                    line_groups[key].append((p1, p2))
                    found_group = True
                    break
        
        if not found_group:
             line_groups[(ux, uy, dist)] = [(p1, p2)]

    merged_edges = []
    
    for key, group_edges in line_groups.items():
        ux, uy, dist = key
        
        # 2. 投影到 1D 参数 t
        # p = t * U + dist * V (V is rotated U)
        # t = p . U
        intervals = []
        for p1, p2 in group_edges:
            t1 = p1[0] * ux + p1[1] * uy
            t2 = p2[0] * ux + p2[1] * uy
            intervals.append(sorted((t1, t2)))
            
        # 3. 合并 1D 区间
        intervals.sort(key=lambda x: x[0])
        
        if not intervals:
            continue
            
        merged_intervals = []
        current_start, current_end = intervals[0]
        
        for next_start, next_end in intervals[1:]:
            # 如果重叠或首尾相接 (gap < tolerance)
            if next_start <= current_end + tolerance:
                current_end = max(current_end, next_end)
            else:
                merged_intervals.append((current_start, current_end))
                current_start, current_end = next_start, next_end
        merged_intervals.append((current_start, current_end))
        
        # 4. 重建 2D 线段
        # x = t * ux + dist * uy
        # y = t * uy - dist * ux
        for t_start, t_end in merged_intervals:
            p_start = (t_start * ux + dist * uy, t_start * uy - dist * ux)
            p_end = (t_end * ux + dist * uy, t_end * uy - dist * ux)
            merged_edges.append((p_start, p_end))
            
    return merged_edges

def _is_point_in_region(x, y, matched_region):
    # 检查点 (x, y) 是否在 matched_region 中
    for region in matched_region:
        min_x, min_y, max_x, max_y = region.bbox
        if min_x - coordinate_point_tolerance < x < max_x + coordinate_point_tolerance and min_y - coordinate_point_tolerance < y < max_y + coordinate_point_tolerance:
            return True
    return False

def _is_polyline_in_matched_region(poly, matched_region):
    # 获取 POLYLINE 的所有点
    if poly.dxftype() == 'LWPOLYLINE':
        points = poly.get_points(format='xy')
    else:
        try:
            points = list(poly.points())
        except:
            return True  # 如果无法获取点，默认认为在 matched_region 中

    # 检查每个点是否在 matched_region 中
    for point in points:
        x, y = point[0], point[1]  # 取前两个坐标
        if _is_point_in_region(x, y, matched_region):
            return True
    return False

def _is_line_in_matched_region(line, matched_region):
    # 获取 LINE 的起点和终点
    start = (line.dxf.start.x, line.dxf.start.y)
    end = (line.dxf.end.x, line.dxf.end.y)
    
    # 检查起点和终点是否在 matched_region 中
    if (_is_point_in_region(start[0], start[1], matched_region)
        or _is_point_in_region(end[0], end[1], matched_region)):
        return True
    return False

def _get_arc_discretized_points(arc) -> List[Tuple[float, float]]:
    """
    将圆弧离散化为点序列
    为了精确计算面积和边界框，将圆弧近似为多段短直线
    """
    c = arc.dxf.center
    r = arc.dxf.radius
    start_angle = arc.dxf.start_angle
    end_angle = arc.dxf.end_angle
    
    # 处理跨越0度的情况
    if end_angle <= start_angle:
        end_angle += 360.0
        
    span = end_angle - start_angle
    
    # 估算分段数：每10度一段，或者基于精度
    # 这里的策略：每 10 度一段，且至少 4 段（如果是大圆弧），或者根据跨度决定
    segments = max(2, int(span / 10))
    if segments > 50: segments = 50 # 限制上限防止过密
    
    points = []
    for i in range(segments + 1):
        angle_deg = start_angle + (span * i / segments)
        angle_rad = math.radians(angle_deg)
        x = c.x + r * math.cos(angle_rad)
        y = c.y + r * math.sin(angle_rad)
        points.append((x, y))
        
    return points

def _is_arc_in_matched_region(arc_points, matched_region):
    for point in arc_points:
        x, y = point
        # 检查点是否在 matched_region 中
        if _is_point_in_region(x, y, matched_region):
            return True
    return False

def is_point_in_polygon(point: Tuple[float, float], 
                        polygon: List[Tuple[float, float]]) -> bool:
    """判断点是否在多边形内部（射线法）"""
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        
        # 改进：更鲁棒的射线法判断
        # 判断点是否在边的Y范围之间
        if ((p1y > y) != (p2y > y)):
            # 计算交点的X坐标
            xinters = (p2x - p1x) * (y - p1y) / (p2y - p1y) + p1x
            
            # 射线向右发射，如果点在交点左侧，则计数
            if x < xinters:
                inside = not inside
                
        p1x, p1y = p2x, p2y
    
    return inside

def is_region_inside(inner: ViewInfo, outer: ViewInfo) -> bool:
    """
    判断一个区域是否在另一个区域内部（包含嵌套或部分重合）
    """
    # 1. 边界框检查（宽松筛选，允许一定的误差）
    inner_bbox = inner.bbox
    outer_bbox = outer.bbox
    tolerance = 5.0 # 扩大容差，处理边缘重合的情况
    
    bbox_inside = (
        inner_bbox[0] >= outer_bbox[0] - tolerance and  # x_min
        inner_bbox[1] >= outer_bbox[1] - tolerance and  # y_min
        inner_bbox[2] <= outer_bbox[2] + tolerance and  # x_max
        inner_bbox[3] <= outer_bbox[3] + tolerance      # y_max
    )
    
    if not bbox_inside:
        return False
    
    # 2. 中心点检查（准确判断）
    # 即使中心点不在（例如凹形状），只要面积比例悬殊且BBox包含，极大概率是嵌套细节
    
    # 如果面积相比外轮廓很小 (< 50%) 且 BBox 在内部，直接视为嵌套
    # 这样可以处理形状奇特导致中心点在外部的情况
    area_ratio = inner.area / outer.area
    if area_ratio < 0.5:
            # 如果中心在内部，肯定是
            if is_point_in_polygon(inner.center, outer.vertices):
                return True
            
            # 如果中心不在，检查所有顶点是否大部分在BBox范围内（已由步骤1保证）
            # 进一步检查：是否所有顶点都在外轮廓多边形内（或边界上）
            # 采样检查顶点
            inside_count = 0
            total_check = 0
            step = max(1, len(inner.vertices) // 20) # 采样20个点
            
            for i in range(0, len(inner.vertices), step):
                pt = inner.vertices[i]
                # 这里使用简单的点在多边形内判断
                if is_point_in_polygon(pt, outer.vertices):
                    inside_count += 1
                total_check += 1
            
            # 如果超过一半的顶点在内部，视为嵌套
            if total_check > 0 and (inside_count / total_check) > 0.5:
                return True

    return is_point_in_polygon(inner.center, outer.vertices)

def extract_polyline_info(polyline) -> Optional[ViewInfo]:
    """提取多段线信息"""
    try:
        vertices = []
        if polyline.dxftype() == 'LWPOLYLINE':
            # LWPOLYLINE: 点是元组 (x, y, ...)
            for point in polyline:
                vertices.append((point[0], point[1]))
        else:
            # POLYLINE: vertices 是 DXFVertex 对象列表
            for vertex in polyline.vertices:
                vertices.append((vertex.dxf.location.x, vertex.dxf.location.y))
        
        if len(vertices) < 3:
            return None
        
        # 计算边界框
        x_coords = [v[0] for v in vertices]
        y_coords = [v[1] for v in vertices]
        bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
        
        # 计算中心点
        center_x = sum(x_coords) / len(x_coords)
        center_y = sum(y_coords) / len(y_coords)
        
        # 计算面积（使用鞋带公式）
        area = 0
        n = len(vertices)
        for i in range(n):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        area = abs(area) / 2
        
        return ViewInfo(
            name=f"Region_{len(vertices)}pts",
            entity=polyline,
            bbox=bbox,
            area=area,
            center=(center_x, center_y),
            vertices=vertices,
            layer=polyline.dxf.layer
        )
    except Exception as e:
        print(f"  提取多段线信息失败: {e}")
        return None

def remove_duplicate_lines(lines):
    """
    添加一个函数对lines去重
    :param lines: 说明
    """
    unique_lines = []
    for line in lines:
        s = (line.dxf.start.x, line.dxf.start.y)
        e = (line.dxf.end.x, line.dxf.end.y)
        is_duplicate = False
        for unique_line in unique_lines:
            us = (unique_line.dxf.start.x, unique_line.dxf.start.y)
            ue = (unique_line.dxf.end.x, unique_line.dxf.end.y)
            if (abs(s[0] - us[0]) < 1e-3 and abs(s[1] - us[1]) < 1e-3 and
                abs(e[0] - ue[0]) < 1e-3 and abs(e[1] - ue[1]) < 1e-3):
                is_duplicate = True
                break
        if not is_duplicate:
            unique_lines.append(line)
    return unique_lines

# 图论方法识别闭合区域
def find_closed_regions_by_graph_theory_methods(G, min_area):
    """
    通过图论方法寻找闭合区域。

    参数：
        G (networkx.Graph): 输入的图。
        min_area (float): 最小闭合区域的面积。
    返回：
        list[ViewInfo]: 闭合区域的列表。
    """
    # remove nodes with degree < 2 iteratively
    core_g = nx.k_core(G, k=2) 
    if len(core_g.nodes) < 3:
        return []

    cycles = nx.cycle_basis(core_g)

    regions = []
    for cycle in cycles:
        if len(cycle) < 3:
            continue

        # 获取顶点坐标
        vertices = []
        for node_id in cycle:
            if node_id in G.nodes:  # use original G to get pos
                pos = G.nodes[node_id]['pos']
                vertices.append(pos)

        # 计算属性
        # 计算面积
        area = 0
        n = len(vertices)
        x_coords = []
        y_coords = []
        for i in range(n):
            x_coords.append(vertices[i][0])
            y_coords.append(vertices[i][1])
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        area = abs(area) / 2

        if area < min_area:
            continue

        center_x = sum(x_coords) / n
        center_y = sum(y_coords) / n
        bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

        regions.append(ViewInfo(
            name=f"Loop_{len(cycle)}",
            entity=None,  # 虚拟实体
            bbox=bbox,
            area=area,
            center=(center_x, center_y),
            vertices=vertices,
            layer="Constructed"
        ))

    return regions

# 贪心算法寻找闭合区域
def find_closed_regions_by_greedy_angle(edges, min_area) -> List[ViewInfo]:
    """
    使用贪心最小转角策略，从所有线段出发构建可能的闭合回路。
    目标：补充那些由相邻多条线段组合但未被标记为闭合的区域（尤其是矩形/多边形轮廓被拆成多段单独线段的情况）。
    算法概述：
    - 对每条未访问的边作为起点，尝试沿着与当前边形成最小转角的相连边前进，直到回到起点或失败
    - 若构造出合法闭合回路，计算面积并作为区域返回（过滤最小面积）
    - 最后去重相似回路
    参数：
        edges (list of (start_pt, end_pt)): 输入的线段列表
        min_area (float): 过滤掉的最小闭合区域面积
    """

    def key(pt):
        # 使用粗略网格化以匹配微小误差的端点，保留2位小数(与后面的1e-2容差匹配)
        return (round(pt[0], 3), round(pt[1], 3))

    adj = {}  # key(pt) -> list of (neighbor_pt, original_pt)
    for s, e in edges:
        ks = key(s); ke = key(e)
        adj.setdefault(ks, set()).add(e)
        adj.setdefault(ke, set()).add(s)

    # 辅助：向量与角度计算
    def vec(a, b):
        return (b[0]-a[0], b[1]-a[1])

    def angle_between(v1, v2):
        # 返回 0..180 的夹角（度）
        ax, ay = v1; bx, by = v2
        la = math.hypot(ax, ay); lb = math.hypot(bx, by)
        if la < 1e-3 or lb < 1e-3:
            return 180.0
        dot = ax*bx + ay*by
        cosv = max(-1.0, min(1.0, dot / (la*lb)))
        return math.degrees(math.acos(cosv))

    # 贪心从每条边两端尝试构造回路
    found_loops = []
    visited_edges = set()

    # 标准化边的表示用于去重（有向）
    def edge_id(a, b):
        return (round(a[0],3), round(a[1],3), round(b[0],3), round(b[1],3))

    for s, e in edges:
        for start_dir in [(s,e), (e,s)]:
            a0, a1 = start_dir
            eid0 = edge_id(a0, a1)
            if eid0 in visited_edges:
                continue

            path = [a0, a1]
            visited_local = set([eid0])
            max_steps = 2000
            steps = 0
            success = False

            while steps < max_steps:
                steps += 1
                cur = path[-1]
                prev = path[-2]
                kcur = key(cur)
                neighbors = adj.get(kcur, set())

                # 构造候选向量并选择与入射向量转角最小的下一个点（排除回到上一点）
                in_vec = vec(prev, cur)
                best = None
                best_ang = 361.0
                tolerance = IS_POINT_OVERLAP_TOLERANCE
                for nb in neighbors:
                    # 排除与上一点相同
                    if abs(nb[0]-prev[0]) < tolerance and abs(nb[1]-prev[1]) < tolerance:
                        continue
                    cand_vec = vec(cur, nb)
                    ang = angle_between(in_vec, cand_vec)
                    if ang < best_ang:
                        best_ang = ang
                        best = nb

                if best is None:
                    break

                # 若回到起点且路径长度 >=3 则闭合
                if abs(best[0]-path[0][0]) < tolerance and abs(best[1]-path[0][1]) < tolerance and len(path) >= 3:
                    # 闭合成功
                    success = True
                    break

                # 防止循环重复点
                if any(abs(best[0]-p[0])<tolerance and abs(best[1]-p[1])<tolerance for p in path):
                    break

                # 继续延伸
                path.append(best)
                visited_local.add(edge_id(prev, cur))

            if success:
                # 计算面积并过滤
                verts = path[:]
                n = len(verts)
                area = 0
                xs = [v[0] for v in verts]
                ys = [v[1] for v in verts]
                for i in range(n):
                    x1, y1 = verts[i]
                    x2, y2 = verts[(i+1)%n]
                    area += x1*y2 - x2*y1
                area = abs(area)/2
                if area >= min_area:
                    center_x = sum(xs)/n
                    center_y = sum(ys)/n
                    bbox = (min(xs), min(ys), max(xs), max(ys))
                    found_loops.append(ViewInfo(
                        name=f"GreedyLoop_{len(verts)}",
                        entity=None,
                        bbox=bbox,
                        area=area,
                        center=(center_x, center_y),
                        vertices=verts,
                        layer="Greedy"
                    ))
                    # 标记访问过的边
                    for i in range(len(verts)-1):
                        visited_edges.add(edge_id(verts[i], verts[i+1]))

    # 去重：按中心和面积去重
    unique = []
    for r in found_loops:
        dup = False
        for u in unique:
            dist = math.hypot(r.center[0]-u.center[0], r.center[1]-u.center[1])
            if dist < 1.0 and abs(r.area - u.area) / max(u.area, 1.0) < 0.1:
                dup = True
                break
        if not dup:
            unique.append(r)

    return unique



coordinate_point_tolerance = 0.05 

# ===================================================================
# ====================生成板料线的主类=================================
class MaterialLineProjector:
    def __init__(self, dxf_path: str, lwt_info: any = None, log_file_dir: str = None):
        """
        初始化投影器
        :param lwt_info: 包含 L, W, T 信息的字典，或控制字符串 (如 "SKIP_KEYWORD_DETECTED")
        """
        self.doc = ezdxf.readfile(dxf_path)
        self.msp = self.doc.modelspace()
        self.lwt_info = lwt_info # 存储板料信息字典
        self.log_file_dir = log_file_dir      
        self.need_centering = check_need_centering(self.msp) 
        # 配置参数
        self.config = {
            'min_area': 200,  # 最小面积阈值
            'max_area_ratio': 10,  # 最大面积比（过滤过大区域）
            'angle_tolerance': 5,  # 角度容差（度）
            'alignment_tolerance': 0.3,  # 对齐容差（比例）
            'material_layer_color': 241,  # 红色 (Red)
            'material_linetype': 'DASHED',
            'new_layer_prefix': 'PROJ_',
            'radius_threshold': 2.0,  # 最小等腰直角三角形边长阈值  
            'tolerance': 0.01,  # 判断是否相同的容差
            'material_line_tolerance': 0.6,  # 板料线与注释长度的容差 # 坐标标注点容差
            'classify_area_tolerance': 5.0,  # 面积分类容差
            'overlap_area_tolerance': 1e-2,  # 面积容差
        }        
        # 存储结果
        self.views = {}  # 识别的视图
        self.material_lines = []  # 板料线
        self.projected_lines = []  # 投影的线
        self.is_valid_material_line = False
        self._ensure_resources()
    def _ensure_resources(self):
        """确保必要的资源（线型、图层）存在"""
        # 确保线型存在
        lt_name = self.config['material_linetype']
        if lt_name not in self.doc.linetypes:
            try:
                # 定义 DASHED 线型: 0.5 draw, -0.25 gap
                self.doc.linetypes.new(lt_name, dxfattribs={
                    'description': 'Dashed',
                    'pattern': [0.5, -0.25],
                })
            except Exception as e:
                print(f"警告: 创建线型失败 {e}, 将使用 CONTINUOUS")
                self.config['material_linetype'] = 'CONTINUOUS'      

    def find_view_contours_with_filtering(self) -> List[ViewInfo]:
        """
        查找面积前4的闭合区域（排除嵌套）
        支持：闭合多段线、首尾相连的直线/弧线
        """        
        all_regions = []
        l, w, t = float(self.lwt_info.get('L', 0)), float(self.lwt_info.get('W', 0)), float(self.lwt_info.get('T', 0))
        
        matched_regions = []
        # --- 方法A: 查找现有的闭合多段线 ---
        polylines = self.msp.query('LWPOLYLINE POLYLINE')
        
        for polyline in polylines:
            region = None
            is_closed = False

            if polyline.dxftype() == 'LWPOLYLINE':
                # 检查 closed 标志
                if polyline.closed:
                    is_closed = True
                # 检查几何闭合 (首尾点重合)
                elif len(polyline) > 2:
                    start_pt = polyline[0]
                    end_pt = polyline[-1]
                    dist = math.sqrt((start_pt[0]-end_pt[0])**2 + (start_pt[1]-end_pt[1])**2)
                    if dist < 1e-2:
                        is_closed = True

            elif polyline.dxftype() == 'POLYLINE':
                if polyline.is_closed:
                    is_closed = True
                else:
                    try:
                        pts = list(polyline.points())
                        if len(pts) > 2:
                            start_pt = pts[0]
                            end_pt = pts[-1]
                            dist = math.sqrt((start_pt[0]-end_pt[0])**2 + (start_pt[1]-end_pt[1])**2)
                            if dist < 1:
                                is_closed = True
                    except:
                        pass
            
            if is_closed:
                region = extract_polyline_info(polyline)
                if region:
                    x_range = region.bbox[2] - region.bbox[0]
                    y_range = region.bbox[3] - region.bbox[1]
                    length_tolerance = self.config['material_line_tolerance']
                    area_tolerance = 1e-2
                    region_area = region.area
                    if (abs(x_range - l) < length_tolerance and abs(y_range - w) < length_tolerance) and abs(region_area / (l * w) - 1) < area_tolerance or \
                       (abs(x_range - l) < length_tolerance and abs(y_range - t) < length_tolerance) and abs(region_area / (l * t) - 1) < area_tolerance or \
                       (abs(x_range - t) < length_tolerance and abs(y_range - w) < length_tolerance) and abs(region_area / (t * w) - 1) < area_tolerance:
                        matched_regions.append(region)
                    # 闭合多段线在dim层且为蓝色，就继续
                    elif polyline.dxf.layer.lower() == 'dim' and polyline.dxf.color == 5:
                        continue
                    else:
                        all_regions.append(region)

        # 对matched_regions进行去重，中心点和面积都非常接近的只保留一个
        unique_matched = []
        for region in matched_regions:
            is_duplicate = False
            for u in unique_matched:
                dist = math.hypot(region.center[0] - u.center[0], region.center[1] - u.center[1])
                area_diff = abs(region.area - u.area) / max(u.area, 1.0)
                if dist < 1e-2 and area_diff < 1e-3:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_matched.append(region)
        print(f"  多段线方法识别出 {len(unique_matched)} 个闭合区域匹配板料面积")
        if len(unique_matched) >= 4:
            return unique_matched[:4]

        # 去除在已识别区域内的区域
        all_regions = [r for r in all_regions if not _is_polyline_in_matched_region(r.entity, unique_matched)]
        
        # 通过图论和贪心算法获得更多闭合区域（排除已识别区域内的线段）
        remind_regions = self._find_closed_loops_from_lines(unique_matched)
        if remind_regions:
            all_regions.extend(remind_regions)

        # 1.5 统一过滤微小区域（关键修正）
        if all_regions:
            max_area_by_lwt = max(l*w, l*t, w*t) * 1.1 # 三视图的最大面积
            max_area = max(r.area for r in all_regions)
            # 过滤掉面积小于 min_area 或 小于最大面积 1% 的区域
            # 这样可以防止微小的孔洞或杂线被当成视图
            min_rel_ratio = 0.01 # 1%
            min_area_threshold = max(self.config['min_area'], max_area * min_rel_ratio) 
            print(f"  过滤微小区域: 最大面积={max_area:.0f}, 动态阈值={min_area_threshold:.0f} (1%)")
            filtered_regions = []
            for r in all_regions:
                if max_area_by_lwt > r.area > min_area_threshold:
                    filtered_regions.append(r)
                else:
                    pass # print(f"    丢弃微小区域: Area={r.area:.0f}")
            all_regions = filtered_regions

        # 2. 按面积降序排序
        all_regions.sort(key=lambda r: r.area, reverse=True)

        # 2.5 全局去重：中心点和面积都非常接近的只保留一个
        unique_regions = []
        for region in all_regions:
            is_duplicate = False
            for u in unique_regions:
                dist = math.hypot(region.center[0] - u.center[0], region.center[1] - u.center[1])
                area_diff = abs(region.area - u.area) / max(u.area, 1.0)
                if dist < 1e-2 and area_diff < self.config['overlap_area_tolerance']:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_regions.append(region)

        print(f"  图论和贪心总计提取到 {len(unique_regions)} 个闭合区域（去重后）")
        # 依次打印这些区域
        # for region in unique_regions:
        #     print(f"    区域: Area={region.area:.0f}, Center={region.center}, BBox={region.bbox}")

        selected_regions = []
        # 3. 筛选前4个非嵌套区域(去掉通过闭合多段线识别到的区域数量)
        for region in unique_regions:
            if len(selected_regions) >= 4 - len(unique_matched):
                break
            # 检查是否在已选区域内部
            is_inside_any = False
            for selected in selected_regions:
                if is_region_inside(region, selected):
                    is_inside_any = True
                    break
            # 简单去重：如果两个区域中心非常接近且面积接近，视为同一个
            for selected in selected_regions:
                dist = math.sqrt((region.center[0]-selected.center[0])**2 + (region.center[1]-selected.center[1])**2)
                area_diff = abs(region.area - selected.area) / selected.area
                if dist < 10.0 and area_diff < 0.1: # 阈值可调
                    is_inside_any = True # 视为重复
                    break
            if not is_inside_any:
                selected_regions.append(region)
                print(f"  选中区域: Area={region.area:.0f}, "
                      f"x_range = [{region.bbox[0], region.bbox[2]}, y_range = [{region.bbox[1], region.bbox[3]}]]")
            else:
                pass # print(f"  跳过嵌套或重复区域")   

        for region in unique_matched:
            selected_regions.append(region)
        return selected_regions
    
    # 通过图论和贪心算法获得更多闭合区域（排除已识别区域内的线段）
    def _find_closed_loops_from_lines(self, matched_regions: List[ViewInfo]) -> List[ViewInfo]:
        """
        通过图论和贪心算法获得更多闭合区域（排除已识别区域内的线段）
        param matched_regions: 已识别的区域列表，用于排除区域内的线段
        return: 识别出的闭合区域列表
        """
        try:
            import networkx as nx
        except ImportError:
            print("警告: 缺少 networkx 库，无法进行拓扑分析。请运行 pip install networkx")
            return []
        
        G = nx.Graph() # 图论的图
        pos_map = {}  # 坐标 -> 节点ID
        next_node_id = 0
        
        def get_node_id(x, y):
            nonlocal next_node_id
            # 简单的网格化以处理浮点误差
            key = (round(x, 3), round(y, 3)) 
            if key not in pos_map:
                pos_map[key] = next_node_id
                G.add_node(next_node_id, pos=(x, y))
                next_node_id += 1
            return pos_map[key]
        
        # 为贪心识别边，保存边的起点和终点
        edges = [] # 未拼接的边

        # 获取所有不在 matched_regions 内的LINE, ARC, POLYLINE(不闭合)
        # 1. 收集所有 LINE
        original_lines = self.msp.query('LINE')
        lines = []
        l, w, t = float(self.lwt_info.get('L', 0)), float(self.lwt_info.get('W', 0)), float(self.lwt_info.get('T', 0))
        for line in original_lines:
            # 检查 LINE 是否在 matched_region 中或其边上
            if not _is_line_in_matched_region(line, matched_regions):
                # 线的类型为DASHED且长度不接近板料边长，则跳过
                # 如果line的类型是DASHED，则计算line的长度，如果line的长度不接近LWT任意一个长度，则跳过
                if line.dxf.linetype == 'DASHED':
                    line_length = math.hypot(line.dxf.end.x - line.dxf.start.x, line.dxf.end.y - line.dxf.start.y)
                    lwt_lengths = [self.lwt_info.get(key) for key in ['L', 'W', 'T'] if self.lwt_info.get(key) is not None]
                    if not any(abs(line_length - lwt_length) < self.config['material_line_tolerance'] for lwt_length in lwt_lengths):
                        continue
                lines.append(line)        

        # 对lines进行去重
        lines = remove_duplicate_lines(lines)
        print(f"处理 {len(lines)} 条 LINE 实体用于闭合区域识别")
        for line in lines:
            s = (line.dxf.start.x, line.dxf.start.y)
            e = (line.dxf.end.x, line.dxf.end.y)
            edges.append((s, e))
            u = get_node_id(s[0], s[1])
            v = get_node_id(e[0], e[1])
            if u != v:
                length = math.sqrt((s[0] - e[0])**2 + (s[1] - e[1])**2)
                G.add_edge(u, v, weight=length, entity=None)  # 合并后的线段没有具体实体                
        
        # 2. 收集不闭合的 LWPOLYLINE 和 POLYLINE (炸开成边)
        polylines = self.msp.query('LWPOLYLINE POLYLINE')
        for poly in polylines:
            # 检查 POLYLINE 是否在 matched_regions 中或其边上
            if not _is_polyline_in_matched_region(poly, matched_regions):
                is_closed = False
                pts = []
                
                if poly.dxftype() == 'LWPOLYLINE':
                    is_closed = poly.closed
                    pts = poly.get_points(format='xy')
                else: # POLYLINE
                    is_closed = poly.is_closed
                    try:
                        pts = list(poly.points())
                    except:
                        continue
                
                if not is_closed:
                    # 检查几何闭合
                    if len(pts) > 2:
                        s = pts[0]
                        e = pts[-1]
                        if math.hypot(s[0]-e[0], s[1]-e[1]) < 1e-2:
                            continue # 已经在前面处理过了
                    
                    # 优化：检查多段线是否共线。如果所有点都在起终点连线上，则简化为单条线段
                    is_all_collinear = True
                    if len(pts) > 2:
                        p0 = pts[0]
                        pn = pts[-1]
                        dx = pn[0] - p0[0]
                        dy = pn[1] - p0[1]
                        dist_sq = dx*dx + dy*dy
                        if dist_sq < 1e-4:
                            is_all_collinear = False # 长度极短或重叠点
                        else:
                            for k in range(1, len(pts)-1):
                                pk = pts[k]
                                # 点到直线距离。分子为叉积，分母为底边长
                                area2 = abs((pk[0]-p0[0])*dy - (pk[1]-p0[1])*dx)
                                if (area2**2 / dist_sq) > 1e-2: # 距离阈值 0.1
                                    is_all_collinear = False
                                    break
                    
                    if is_all_collinear and len(pts) >= 2:
                        # 简化：只取起终点组成的直线段
                        simplified_segments = [((pts[0][0], pts[0][1]), (pts[-1][0], pts[-1][1]))]
                    else:
                        # 不共线或点数少：保留所有原始段
                        simplified_segments = []
                        for i in range(len(pts)-1):
                            simplified_segments.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))

                    for p1, p2 in simplified_segments:
                        edges.append((p1, p2))
                        u = get_node_id(p1[0], p1[1])
                        v = get_node_id(p2[0], p2[1])
                        if u != v:
                            length = math.hypot(p1[0]-p2[0], p1[1]-p2[1])
                            G.add_edge(u, v, weight=length, entity=poly)

        # 合并所有在一条直线上的边
        merged_edges = merge_edges(edges)

        # 3. 收集所有 ARC (离散化处理)
        arcs = self.msp.query('ARC')
        for arc in arcs:
            pts = _get_arc_discretized_points(arc)
            # 检查 ARC 是否在 matched_region 中或其边上
            if not _is_arc_in_matched_region(pts, matched_regions):
                for i in range(len(pts) - 1):
                    p1 = pts[i]
                    p2 = pts[i+1]
                    edges.append((p1, p2))
                    merged_edges.append((p1, p2))  # 只加入离散化后的线段元组，避免Arc对象
                    u = get_node_id(p1[0], p1[1])
                    v = get_node_id(p2[0], p2[1])
                    if u != v:
                        length = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
                        G.add_edge(u, v, weight=length, entity=arc)

        # 4. 收集所有 SPLINE 和 ELLIPSE (起点和终点)
        splines = self.msp.query('SPLINE')
        print(f"  处理 {len(splines)} 个 SPLINE 实体")
        for spline in splines:
            points = get_spline_points(spline)
            # 检查 SPLINE 是否在 matched_region 中或其边上
            if not is_points_in_matched_region(points, matched_regions):
                for i in range(len(points) - 1):
                    p1 = points[i]
                    p2 = points[i+1]
                    edges.append((p1, p2))
                    merged_edges.append((p1, p2))  # 只加入离散化后的线段元组，避免Spline对象
                    u = get_node_id(p1[0], p1[1])
                    v = get_node_id(p2[0], p2[1])
                    if u != v:
                        length = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
                        G.add_edge(u, v, weight=length, entity=spline)
        ellipses = self.msp.query('ELLIPSE')
        for ellipse in ellipses:
            points = get_ellipse_points(ellipse)
            # 检查 ELLIPSE 是否在 matched_region 中或其边上
            if not is_points_in_matched_region(points, matched_regions):
                for i in range(len(points) - 1):
                    p1 = points[i]
                    p2 = points[i+1]
                    edges.append((p1, p2))
                    merged_edges.append((p1, p2))  # 只加入离散化后的线段元组，避免Ellipse对象
                    u = get_node_id(p1[0], p1[1])
                    v = get_node_id(p2[0], p2[1])
                    if u != v:
                        length = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
                        G.add_edge(u, v, weight=length, entity=ellipse)

        result_regions = []
        # 5. 查找闭合回路 (Cycle Basis)
        # 5.1 通过图论算法:# 拓扑构建（合并散碎线段）
        regions_found_by_graph_theory = find_closed_regions_by_graph_theory_methods(G, self.config['min_area'])
        if regions_found_by_graph_theory:
            result_regions.extend(regions_found_by_graph_theory)
            print(f"  图论方法识别出 {len(regions_found_by_graph_theory)} 个闭合区域")
            # for r in regions_found_by_graph_theory:
            #     print(f"    图论闭合区域: Area={r.area:.0f}, "
            #           f"x_range = [{r.bbox[0], r.bbox[2]}, y_range = [{r.bbox[1], r.bbox[3]}]]")
        else:
            print("  图论方法未识别出闭合区域")

        # 5.2 通过贪心算法（遍历未拼接的边）
        if edges != []:
            regions_found_by_greedy_1 = find_closed_regions_by_greedy_angle(edges, self.config['min_area'])
            if regions_found_by_greedy_1:
                result_regions.extend(regions_found_by_greedy_1)
                print(f"  贪心方法（遍历未拼接的边）识别出 {len(regions_found_by_greedy_1)} 个闭合区域")
                # for r in regions_found_by_greedy_1:
                #     print(f"    贪心闭合区域: Area={r.area:.0f}, "
                #           f"x_range = [{r.bbox[0], r.bbox[2]}, y_range = [{r.bbox[1], r.bbox[3]}]]")
            else:
                print("  贪心方法（遍历未拼接的边）未识别出闭合区域")
        # 5.2 通过贪心算法（遍历拼接过的边）
        if merged_edges != []:
            regions_found_by_greedy_2 = find_closed_regions_by_greedy_angle(merged_edges, self.config['min_area'])
            if regions_found_by_greedy_2:
                result_regions.extend(regions_found_by_greedy_2)
                print(f"  贪心方法（遍历拼接过的边）识别出 {len(regions_found_by_greedy_2)} 个闭合区域")
                for r in regions_found_by_greedy_2:
                    print(f"    贪心闭合区域: Area={r.area:.0f}, "
                          f"x_range = [{r.bbox[0], r.bbox[2]}, y_range = [{r.bbox[1], r.bbox[3]}]]")
            else:
                print("  贪心方法（遍历拼接过的边）未识别出闭合区域")

        return result_regions
     
    def _identify_view_by_lwt(self, region: ViewInfo):
        """
        根据LWT信息判断闭合区域的视图类型（模糊匹配）
        判据：
        1. 对应L和W -> 主视图
        2. x差值对应T -> 侧视图
        3. y差值对应T -> 正视图
        """
        if not self.lwt_info:
            return None
            
        l = self.lwt_info.get('L')
        w = self.lwt_info.get('W')
        t = self.lwt_info.get('T')
        
        if l is None or w is None or t is None:
            return None
            
        dx = region.bbox[2] - region.bbox[0]
        dy = region.bbox[3] - region.bbox[1]
        
        tolerance = 10.0
        
        result = []
        # 1. 主视图判断 (L x W)
        if (abs(dx - l) < tolerance and abs(dy - w) < tolerance) or \
           (abs(dx - w) < tolerance and abs(dy - l) < tolerance):
           result.append('main_view')
           
        # 2. 侧视图判断 (x差值对应T)
        # if abs(dx - t) < tolerance and abs(dy - w) < tolerance:
        if abs(dx - t) < tolerance:
            result.append('side_view')
            
        # 3. 正视图判断 (y差值对应T)
        # if abs(dy - t) < tolerance and abs(dx - l) < tolerance:
        if abs(dy - t) < tolerance:
            result.append('front_view')
            
        return result

    def identify_views_with_alignment(self, regions: List[ViewInfo]):
        """
        识别视图（基于LWT和位置关系）
        """
        num_regions = len(regions)
        if num_regions == 0:
            raise ValueError("未找到任何闭合区域")

        self.views = {}
        self.unrecognized_regions = []

        # 遍历所有闭合区域，尝试基于LWT信息识别
        for region in regions:
            view_types = self._identify_view_by_lwt(region)
            # view_type 存在且未被识别过（self.views 中没有该类型）
            if view_types != []:
                for view_type in view_types:
                    if view_type not in self.views:
                        self.views[view_type] = []
                    self.views[view_type].append(region)
            else:
                self.unrecognized_regions.append(region)

        # 筛选视图，按左上角点位置排序，主视图选择匹配的视图中最左上角，侧视图选择最右侧的，正视图选择最下侧的
        main_view, side_view, front_view = None, None, None
        if 'main_view' not in self.views:
            return False
        print(f"  识别到主视图数量: {len(self.views['main_view'])}")
        self.views['main_view'].sort(key=lambda r: (r.bbox[0], -r.bbox[1]))  # 按 x_min 从小到大排序，再按 y_min 从大到小排序
        main_view = self.views['main_view'][0]
        print(f"主视图区域x_range={main_view.bbox[0], main_view.bbox[2]}")
        if 'side_view' in self.views:
            for view in self.views['side_view'][:]:
                if view == main_view:
                    self.views['side_view'].remove(view)
                elif view.bbox[0] < main_view.bbox[2]:  # 侧视图应在主视图右侧
                    self.views['side_view'].remove(view)
            if len(self.views['side_view']) == 0:
                del self.views['side_view']
            else:
                self.views['side_view'].sort(key=lambda r: r.bbox[0], reverse=True)  # 按 x_min 从大到小排序
                side_view = self.views['side_view'][0]
        if 'front_view' in self.views:
            for view in self.views['front_view'][:]:
                if view == main_view:
                    self.views['front_view'].remove(view)
                elif view.bbox[3] > main_view.bbox[1]:  # 正视图应在主视图下方
                    self.views['front_view'].remove(view)
            if len(self.views['front_view']) == 0:
                del self.views['front_view']
            else:
                self.views['front_view'].sort(key=lambda r: r.bbox[1])  # 按 y_min 从小到大排序
                front_view = self.views['front_view'][0]

        try:
            for key, view in self.views.items():
                if side_view:
                    if side_view in view and side_view != view[0]:
                        view.remove(side_view)
                if front_view:
                    if front_view in view and front_view != view[0]:
                        view.remove(front_view)
        except Exception as e:
            print(f'{e}')

        return True
    
    def _calculate_line_angle(self, start: Tuple[float, float], 
                            end: Tuple[float, float]) -> float:
        """计算线的角度（0-180度）"""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        if abs(dx) < 1e-2:  # 垂直线
            return 90.0
        
        angle_rad = math.atan2(abs(dy), abs(dx))
        angle_deg = math.degrees(angle_rad)
        
        # 处理水平线
        if abs(dy) < 1e-2:
            return 0.0 if dx > 0 else 180.0
        
        return angle_deg
    
    def generate_material_lines_from_bbox(self):
        """
        通过闭合区域的边界框生成板料线
        """
        main_views = self.views.get('main_view', [])
        side_views = self.views.get('side_view', [])
        front_views = self.views.get('front_view', [])
               
        # 使用相同的板料线图层名称
        material_layer_name = f"{self.config['new_layer_prefix']}MATERIAL"
        if material_layer_name not in self.doc.layers:
            self.doc.layers.new(name=material_layer_name, dxfattribs={
                    'color': self.config['material_layer_color'],
                    'linetype': self.config['material_linetype']
                    })

        main_view = main_views[0]
        mx_min, my_min, mx_max, my_max = main_view.bbox

        # 1. 生成主视图板料线
        p1 = (mx_min, my_min)
        p2 = (mx_max, my_min)
        p3 = (mx_max, my_max)
        p4 = (mx_min, my_max)
        self._draw_box(p1, p2, p3, p4, material_layer_name)
        # 更新main_view的region信息为板料线区域
        self.views['main_view'][0] = ViewInfo(
                name='main_view_material',
                entity=None,
                bbox=(mx_min, my_min, mx_max, my_max),
                area=(mx_max - mx_min) * (my_max - my_min),
                center=((mx_min + mx_max) / 2, (my_min + my_max) / 2),
                vertices=[p1, p2, p3, p4],
                layer='material_layer'
                )

        # 2. 生成侧视图板料线
        # y范围 = 主视图y范围 (my_min, my_max)
        # x范围 = 侧视图x范围
        if side_views:
            side_view = side_views[0]
            sx_min, sy_min, sx_max, sy_max = side_view.bbox
                
            p1 = (sx_min, my_min)
            p2 = (sx_max, my_min)
            p3 = (sx_max, my_max)
            p4 = (sx_min, my_max)
                
            self._draw_box(p1, p2, p3, p4, material_layer_name)
            # 更新side_view的region信息为板料线区域
            self.views['side_view'][0] = ViewInfo(
                    name='side_view_material',
                    entity=None,
                    bbox=(sx_min, my_min, sx_max, my_max),
                    area=(sx_max - sx_min) * (my_max - my_min),
                    center=((sx_min + sx_max) / 2, (my_min + my_max) / 2),
                    vertices=[p1, p2, p3, p4],
                    layer='material_layer'
                    )

        # 3. 生成正视图板料线
        # x范围 = 主视图x范围 (mx_min, mx_max)
        # y范围 = 正视图y范围
        if front_views:
            front_view = front_views[0]
            fx_min, fy_min, fx_max, fy_max = front_view.bbox

            p1 = (mx_min, fy_min)
            p2 = (mx_max, fy_min)
            p3 = (mx_max, fy_max)
            p4 = (mx_min, fy_max)
                
            self._draw_box(p1, p2, p3, p4, material_layer_name)
            # 更新front_view的region信息为板料线区域
            self.views['front_view'][0] = ViewInfo(
                name='front_view_material',
                entity=None,
                bbox=(mx_min, fy_min, mx_max, fy_max),
                area=(mx_max - mx_min) * (fy_max - fy_min),
                center=((mx_min + mx_max) / 2, (fy_min + fy_max) / 2),
                vertices=[p1, p2, p3, p4],
                layer='material_layer'
                )
        
    def _draw_box(self, p1, p2, p3, p4, layer_name):
        points = [p1, p2, p3, p4, p1] # 闭合
        self.msp.add_lwpolyline(points, dxfattribs={
            'layer': layer_name,
            'color': self.config['material_layer_color'], 
            'linetype': self.config['material_linetype'],
            'closed': True
        })

    def _write_log(self, message: str):
        """写入错误日志"""
        try:
            if self.log_file_dir:
                log_file = os.path.join(self.log_file_dir, os.path.basename(self.doc.filename))
                log_file = os.path.splitext(log_file)[0] + ".log"
                if not os.path.exists(self.log_file_dir):
                    os.makedirs(self.log_file_dir)
            else:
                # 获取当前文件所在目录
                current_dir = os.path.dirname(os.path.abspath(__file__))
                log_dir = os.path.join(current_dir, "logs")

                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)

                log_file = os.path.splitext(os.path.basename(self.doc.filename))[0] + ".log"
                log_file = os.path.join(log_dir, log_file)

            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 假设我们可以获取到文件名，或者就记录消息
                f.write(f"[{timestamp}] {message}\n")
            print(f"  日志写入成功: {log_file}")
        except PermissionError as pe:
            print(f"  日志写入权限错误: {pe}")
        except Exception as e:
            print(f"  日志写入失败: {e}")

    def generate_ordinate_dimension(self, x_range, y_range, quadrant='左下角') :
        """
        生成指定点的坐标标注
        """
        try:
            # 如果不存在则创建图层 U1
            if 'U1' not in self.doc.layers:
                self.doc.layers.add(name='U1', color=7)  # 颜色 7 表示白色/按背景反色

            # 设置标注的图层、颜色与线型（示例图显示在 0 图层、连续线型）
            attribs = {
                'layer': self.config['new_layer_prefix'] + 'ORDINATE_DIMENSION',
                'color': 256,  # 256 表示 ByLayer
                'linetype': 'CONTINUOUS',
            }


            offset = 10.0
            # 依据象限决定引线与文字的偏移方向
            quadrant_offsets = {
                '右上角': ((offset, 0.0), (0.0, offset)),
                '左上角': ((-offset, 0.0), (0.0, offset)),
                '左下角': ((-offset, 0.0), (0.0, -offset)),
                '右下角': ((offset, 0.0), (0.0, -offset)),
                '中间分中': ((-offset, 0.0), (0.0, -offset)),
                '上侧分中': ((-offset, 0.0), (0.0, -offset)),
                '左侧分中': ((-offset, 0.0), (0.0, -offset)),
            }

            target_point = {
                '右上角': (x_range[1], y_range[1]),
                '左上角': (x_range[0], y_range[1]),
                '左下角': (x_range[0], y_range[0]),
                '右下角': (x_range[1], y_range[0]),
                '中间分中': ((x_range[0] + x_range[1]) / 2, (y_range[0] + y_range[1]) / 2),
                '上侧分中': ((x_range[0] + x_range[1]) / 2, y_range[1]),
                '左侧分中': (x_range[0], (y_range[0] + y_range[1]) / 2),
            }

            offset_vector_x, offset_vector_y = quadrant_offsets[quadrant]
            point = target_point[quadrant]

            # 添加 Y 方向坐标标注并显示 Y 坐标值
            dim_y = self.msp.add_ordinate_dim(
                feature_location=point,
                offset=offset_vector_y,
                dtype=1,
                text="0",
                dxfattribs=attribs
            )
            dim_y.render()  # 生成 Y 坐标标注

            # 添加 X 方向坐标标注并显示 X 坐标值
            dim_x = self.msp.add_ordinate_dim(
                feature_location=point,
                offset=offset_vector_x,
                dtype=0,
                text="0",
                dxfattribs=attribs
            )
            dim_x.render()  # 生成 X 坐标标注
            return point
        except Exception as e:
            print(f"Error creating DXF: {e}")
            return None

    def point_in_bbox(self, point, region):
        # 判断三视图区域内是否已有坐标标注点
            x, y = point[0], point[1]
            min_x , min_y, max_x, max_y = region.bbox
            return (min_x - coordinate_point_tolerance <= x <= max_x + coordinate_point_tolerance 
                    and min_y - coordinate_point_tolerance <= y <= max_y + coordinate_point_tolerance)
     
    def collect_circles(self, container,x_range=None, y_range=None) -> None:
        # 在指定图元容器中收集半径小于阈值的圆与其圆心
        small_circles: list[tuple[ezdxf.entities.Circle, tuple[float, float, float]]] = []
        for entity in container.query("CIRCLE"):
            radius = entity.dxf.radius
            if radius is None or radius >= self.config['radius_threshold']:
                continue
            center = entity.dxf.center
            if x_range is not None and not (x_range[0] <= center.x <= x_range[1]):
                continue
            if y_range is not None and not (y_range[0] <= center.y <= y_range[1]):
                continue
            small_circles.append((entity, (center[0], center[1], center[2])))
    def squared_distance(self, a: tuple[float, float, float], b: tuple[float, float, float]) :
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        dz = a[2] - b[2]
        return dx * dx + dy * dy + dz * dz
    def classify_quadrant(self, dx: float, dy: float) -> str:
        if dx > 0 and dy > 0:
            return "第一象限"
        if dx < 0 and dy > 0:
            return "第二象限"
        if dx < 0 and dy < 0:
            return "第三象限"
        elif dx > 0 and dy < 0:
            return "第四象限"
    
    def find_minimal_iso_triangle(self, region):

        bbox = region.bbox  # (min_x, min_y, max_x, max_y)
        x_range = (bbox[0], bbox[2])
        y_range = (bbox[1], bbox[3])

        # 在指定图元容器中收集半径小于阈值的圆与其圆心
        small_circles: list[tuple[ezdxf.entities.Circle, tuple[float, float, float]]] = []
        
        self.collect_circles(self.doc.modelspace(), x_range, y_range)
        for layout in self.doc.layouts:
            if layout.name == "Model":
                continue
            self.collect_circles(layout, x_range, y_range)
        for block in self.doc.blocks:
            self.collect_circles(block, x_range, y_range)

        minimal_area: float | None = None
        best_combinations: list[tuple[ezdxf.entities.Circle, ezdxf.entities.Circle, ezdxf.entities.Circle]] = []
        # 检查任意三个小圆圆心是否能组成等腰直角三角形并计算面积
        for triplet in itertools.combinations(small_circles, 3):
            (circle_a, center_a), (circle_b, center_b), (circle_c, center_c) = triplet
            d_ab = self.squared_distance(center_a, center_b)
            d_ac = self.squared_distance(center_a, center_c)
            d_bc = self.squared_distance(center_b, center_c)
            distances = sorted((d_ab, d_ac, d_bc))
            if distances[0] <= self.config['tolerance'] or distances[1] <= self.config['tolerance']:
                continue  # 忽略重合圆心
            if (
                abs(distances[0] - distances[1]) <= self.config['tolerance']
                and abs(distances[2] - (distances[0] + distances[1])) <= self.config['tolerance']
            ):
                area = 0.5 * distances[0]
                if minimal_area is None or area + self.config['tolerance'] < minimal_area:
                    minimal_area = area
                    best_combinations = [(circle_a, circle_b, circle_c)]
                elif minimal_area is not None and abs(area - minimal_area) <= self.config['tolerance']:
                    best_combinations.append((circle_a, circle_b, circle_c))
        multiple_minima = False
        orientations: set[str] = set()
        if minimal_area is not None:
            seen_keys: set[str] = set()
            for combo in best_combinations:
                circle_a, circle_b, circle_c = combo
                centers = [circle_a.dxf.center, circle_b.dxf.center, circle_c.dxf.center]
                dists = {
                    ("ab", self.squared_distance(centers[0], centers[1])),
                    ("ac", self.squared_distance(centers[0], centers[2])),
                    ("bc", self.squared_distance(centers[1], centers[2])),
                }
                pairs = list(dists)
                pairs.sort(key=lambda item: item[1])
                short_edges = pairs[:2]
                long_edge = pairs[2]
                if abs(short_edges[0][1] - short_edges[1][1]) <= self.config['tolerance'] and abs(
                    long_edge[1] - (short_edges[0][1] + short_edges[1][1])
                ) <= self.config['tolerance']:
                    if long_edge[0] == "ab":
                        right = centers[2]
                        h1, h2 = centers[0], centers[1]
                    elif long_edge[0] == "ac":
                        right = centers[1]
                        h1, h2 = centers[0], centers[2]
                    else:
                        right = centers[0]
                        h1, h2 = centers[1], centers[2]
                    midpoint = ((h1[0] + h2[0]) * 0.5, (h1[1] + h2[1]) * 0.5)
                    vector = (right[0] - midpoint[0], right[1] - midpoint[1])
                    orientations.add(self.classify_quadrant(vector[0], vector[1]))
                for circle in combo:
                    handle = circle.dxf.handle or str(id(circle))
                    if handle in seen_keys:
                        continue
                    seen_keys.add(handle)
            selected_total = len(seen_keys)
            multiple_minima = len(best_combinations) > 1
            return (
                len(small_circles),
                minimal_area,
                multiple_minima,
                tuple(sorted(orientations))
                )
        # 如果没有找到任何等腰直角三角形组合，返回默认值，防止 NoneType 解包错误
        return (len(small_circles), None, False, ())

    def determine_point_position_in_view(self, point, view_bbox):
        """
        判断点在视图的哪个象限（左上角、左下角、右上角、右下角）。
        """
        x, y = point[0], point[1]
        x_min, y_min, x_max, y_max = view_bbox

        if abs(x - x_min) < coordinate_point_tolerance:  # 左侧
            if abs(y - y_max) < coordinate_point_tolerance:  # 上方
                return "左上角"
            elif abs(y - y_min) < coordinate_point_tolerance:  # 下方
                return "左下角"
            elif abs(y - (y_min + y_max) / 2) < coordinate_point_tolerance:
                return "左侧分中"
            else:  # 错误
                return "(0,0)点位置有误"
        elif abs(x - x_max) < coordinate_point_tolerance:  # 右侧
            if abs(y - y_max) < coordinate_point_tolerance:  # 上方
                return "右上角"
            elif abs(y - y_min) < coordinate_point_tolerance:  # 下方
                return "右下角"
            else:  # 错误
                return "(0,0)点位置有误"
        elif abs(x - (x_min + x_max) / 2) < coordinate_point_tolerance:
            if abs(y - (y_min + y_max) / 2) < coordinate_point_tolerance:
                return "中间分中"
            elif abs(y - y_max) < coordinate_point_tolerance:
                return "上侧分中"
            else:
                return "(0,0)点位置有误"
        else:   
            return "(0,0)点位置有误"
            
    def ordinate_dimension_0_0(self, ordinate_points=None):
        """
        生成视图的（0,0）标注
        说明：该方法会在DXF文件中查找最小等腰直角三角形组合，并在其顶点方向标注原点位置(0,0)
        """
        # 创建成员变量0，0坐标字典
        self.ordinate_0_0 = {}
        main_view = self.views['main_view'][0]

        # 判断视图中是否已存在0，0标注，若没有0，0标注，判断是否有最小等腰直角三角形组合
        if ordinate_points != None:
            for point in ordinate_points:
                if self.point_in_bbox(point, main_view):
                    if 'main_view' in self.ordinate_0_0:
                        # 通过日志报错：该视图存在多个0，0坐标点
                        msg = f"main_view 存在多个 (0, 0) 坐标点，跳过处理"
                        return False, msg
                    else:
                        # 判断点在视图的哪个象限（左上角、左下角、右上角、右下角、中间分中、上侧分中、左侧分中）。
                        point_position = self.determine_point_position_in_view(point, main_view.bbox)
                        if point_position == '(0,0)点位置有误':
                            msg = f"main_view 中的 (0, 0) 坐标点位置有误，跳过处理"
                            return False, msg
                        self.ordinate_0_0['main_view'] = [point_position]

        # 若不存在0，0坐标，则查找最小等腰直角三角形组合
        if 'main_view' not in self.ordinate_0_0:
            area_num, minimal_area, multiple_minima, orientations = self.find_minimal_iso_triangle(main_view)
            # if minimal_area is not None and multiple_minima:
            #     msp = self.doc.modelspace()
            #     origin_exists = False
            #     for point in msp.query("POINT"):
            #         location = point.dxf.location
            #         if (
            #             abs(location.x) <= self.config['tolerance']
            #             and abs(location.y) <= self.config['tolerance']
            #             and abs(location.z) <= self.config['tolerance']
            #         ):
            #             origin_exists = True
            #             break
            # if not origin_exists:
            #     # 若存在面积相同的多组，使用左下角点标记作为提示
            #     msp.add_point((bbox[0], bbox[1], 0.0), dxfattribs={"layer": '0'}) 
            if minimal_area is None:
                print(f">>视图main_view：共找到 {area_num:.0f} 个半径小圈，但未检测到等腰直角三角形组合。")
            else:
                orientation_msg = "、".join(orientations) if orientations else "方向无法判定"
                print(
                f">>视图main_view：共找到 {area_num:.0f} 个半径小圈，最小等腰直角三角形面积为 {minimal_area:.6f}，指向象限：{orientation_msg}"
            )
        
            if multiple_minima:
                msg = f"视图 main_view ：存在多个最小等腰直角三角形组合，跳过处理"
                return False, msg
            elif orientations != ():
                orientation = ''
                if orientations[0] == "第一象限":
                    orientation = "右上角"
                elif orientations[0] == "第二象限":
                    orientation = "左上角"
                elif orientations[0] == "第三象限":
                    orientation = "左下角"
                elif orientations[0] == "第四象限":
                    orientation = "右下角"
                self.ordinate_0_0['main_view'] = [orientation, None]


        # 正确的0，0坐标点所在的方向对应为：
        # 主视图坐标方向：[侧视图坐标方向，正视图坐标方向]
        correct_orientations = {
            '右上角': ['左上角', '右上角'],
            '左上角': ['左上角', '左上角'],
            '左下角': ['左下角', '左上角'], 
            '右下角': ['左下角', '右上角'],
            '中间分中': ['左侧分中', '上侧分中']
        }

        # 对视图中已有的方向进行判断
        if self.need_centering:
                self.ordinate_0_0['main_view'] = ['中间分中']
        if 'main_view' not in self.ordinate_0_0:
            self.ordinate_0_0['main_view'] = ['左下角']
        if 'main_view' in self.ordinate_0_0:
            main_view_orientation = self.ordinate_0_0.get('main_view', [None])[0]
            print(f"主视图0，0坐标方向：{main_view_orientation}")
        
            # 最终生成0，0坐标标注
            for key, view in self.views.items():
                if key in self.views:
                    if key not in self.ordinate_0_0:
                        if key == 'side_view':
                            self.ordinate_0_0[key] = [correct_orientations[main_view_orientation][0]]
                        elif key == 'front_view':
                            self.ordinate_0_0[key] = [correct_orientations[main_view_orientation][1]]
                    self.ordinate_0_0[key].append(self.generate_ordinate_dimension(
                        (view[0].bbox[0], view[0].bbox[2]),
                        (view[0].bbox[1], view[0].bbox[3]),
                        self.ordinate_0_0[key][0]
                    ))
        
        return True, ''

    # ===================================================================
    # =================生成板料线和（0，0）标注的主程序=====================
    def run(self, output_path: str = "output_with_material.dxf", fail_file_path: str = "fail_file.dxf", json_0_0_dir = '') -> bool:
        """
        运行完整流程

        :param output_path: 输出DXF文件路径
        :param fail_file_path: 失败文件保存路径
        :param json_0_0_dir: 0，0坐标json文件保存路径
        """
        file_name = os.path.basename(self.doc.filename) if self.doc.filename else "Unknown_File"
        try:
            print("\n>>步骤1：查找所有闭合区域，通过多段线直接识别、图论和贪心算法")
            regions = self.find_view_contours_with_filtering()
            print(f"  步骤1共识别到 {len(regions)} 个闭合区域")
            
            if len(regions) < 1:
                print(f"错误：未找到任何有效闭合区域")
                self._write_log(f"{file_name}未找到任何有效闭合区域")
                # 未处理的图纸保存至fail_file文件夹
                self.doc.saveas(fail_file_path)
                return False           

            print("\n>>步骤2：对步骤1识别出的所有闭合区域进行判别，识别主视图、侧视图和正视图")
            self.identify_views_with_alignment(regions)
            # 对views进行检查
            if self.unrecognized_regions and len(self.views) < 3:
                min_x, min_y, max_x, max_y = self.unrecognized_regions[0].bbox
                region_width = max_x - min_x
                region_height = max_y - min_y
                l, w, t = [self.lwt_info['L'], self.lwt_info['W'], self.lwt_info['T']]
                msg = f"{file_name}：识别到无法匹配任何视图的闭合区域，闭合区域长宽为：{region_width} x {region_height}，板料线实际为：{l}x{w}x{t}，跳过处理"
                print(msg)
                self._write_log(msg)
                self.doc.saveas(fail_file_path)
                return False
            if not self.views or 'main_view' not in self.views:
                print(f"错误：未能识别主视图")
                self._write_log(f"{file_name}未能识别主视图")
                # 未处理的图纸保存至fail_file文件夹
                self.doc.saveas(fail_file_path)
                return False
            for key, view in self.views.items():
                if len(view) > 1 and abs(view[0].area - view[1].area) < self.config['overlap_area_tolerance']:
                    msg = f"{file_name}识别到多个 {key}，判定为多零件图，跳过处理"
                    print(msg)
                    self._write_log(msg)
                    self.doc.saveas(fail_file_path)
                    return False
                else:
                    tolerance = self.config['material_line_tolerance']  # 最小尺寸容差
                    # 进行精确匹配
                    region = view[0]
                    bbox = region.bbox  # (min_x, min_y, max_x, max_y)
                    region_width = bbox[2] - bbox[0]
                    region_height = bbox[3] - bbox[1]
                    l, w, t = [self.lwt_info['L'], self.lwt_info['W'], self.lwt_info['T']]
 
                    msg = '' 
                    if key == 'main_view':
                        if abs(region_width - l) > tolerance or abs(region_height - w) > tolerance:
                            msg = f"{file_name}[视图 {key}]：{region_width} 、{region_height}尺寸与L/W不匹配，L/W：{l}/{w}，跳过处理"
                    elif key == 'side_view':
                        if abs(region_width - t) > tolerance:
                            msg = f"{file_name}[视图 {key}]：{region_width}尺寸与T不匹配，T：{t}，跳过处理"    
                    else:  # front_view
                        if abs(region_height - self.lwt_info['T']) > tolerance:
                            msg = f"{file_name}[视图 {key}]：{region_height}尺寸与T不匹配，T：{t}，跳过处理"
                    if msg != '':
                        print(msg)
                        self._write_log(msg)
                        self.doc.saveas(fail_file_path)
                        return False
            

            print("\n>>步骤3：基于识别出的视图闭合区域边界生成板料线")
            self.generate_material_lines_from_bbox()     

            print("\n>>步骤4：寻找视图中已存在的0，0标注，并为不存在标注的视图创建0，0标注")
            ordinate_points = find_ordinate_points(self.doc)
            is_ordinate_success, msg = self.ordinate_dimension_0_0(ordinate_points)
            if is_ordinate_success is False:
                print(f"{file_name}:{msg}")
                self._write_log(f"{file_name}:{msg}")
                self.doc.saveas(fail_file_path)
                return False
            
            print("\n>>步骤5：把三个视图的0，0坐标输出到json文件里")
            json_0_0_file_name = os.path.join(json_0_0_dir, os.path.splitext(file_name)[0] + ".json")
            self.ordinate_0_0['main_view_bottom_left'] = (self.views['main_view'][0].bbox[0], self.views['main_view'][0].bbox[1])
            self.ordinate_0_0['main_view_top_right'] = (self.views['main_view'][0].bbox[2], self.views['main_view'][0].bbox[3])
            with open(json_0_0_file_name, 'w', encoding='utf-8') as json_file:
                json.dump(self.ordinate_0_0, json_file, ensure_ascii=False, indent=4)

                   
            # 步骤6：保存结果
            self.doc.saveas(output_path)   
            return True    
        except Exception as e:
            print(f"\n处理过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    

# ===================================================================
# ============================主程序=================================
# =======================处理单个dxf文件==============================
# ===================================================================
def process_single_dxf(dxf_file_path: str, output_dir: str, log_file_dir: str = None, csv_path: str = None, json_0_0_dir = '') -> bool:
    """
    封装的处理函数
    :param dxf_file_path: 输入DXF文件路径
    :param output_dir: 输出DXF文件夹路径
    :param log_file_dir: 日志文件夹路径
    :param csv_path: CSV文件路径（包含L/W/T信息）
    :param json_0_0_dir: 生成的0,0坐标JSON文件夹路径（传递给钻孔）
    :return: 是否成功（True/False）
    """
    # 检查输出目录是否存在，不存在则创建
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # 在输出目录下新建失败文件夹：fail_file
    fail_dir = os.path.join(output_dir, "fail_file")
    if not os.path.exists(fail_dir):
        os.makedirs(fail_dir)
    # 构建输出文件路径
    file_name = os.path.basename(dxf_file_path)
    output_file_path = os.path.join(output_dir, file_name)
    fail_file_path = os.path.join(fail_dir, file_name)
    projector = MaterialLineProjector(dxf_file_path, lwt_info=None, log_file_dir=log_file_dir)

    # 1. 提取注释
    # 1.1 从csv中读取当前文件的信息
    csv_info = read_lwt_from_csv(csv_path, file_name)
    print(f"从CSV中读取到的信息: {csv_info}")
    # 1.2 从注释中读取L/W/T信息
    lwt_value = get_notes(dxf_file_path)
    print(f"从注释中读取到的信息: {lwt_value}")
    # 解析两种信息：
    parse_msg, parse_lwt = parse_lwt_info(csv_info, lwt_value)
    if parse_msg != '':
        projector._write_log(f"{file_name}:{parse_msg}")
        print(parse_msg)
    if parse_lwt is None:
        projector.doc.saveas(fail_file_path)
        return False
    projector.lwt_info = parse_lwt

    # 2. 运行投影
    success = projector.run(output_file_path, fail_file_path, json_0_0_dir)
    return success


# ===================================================================
# ===========================使用示例=================================
if __name__ == "__main__":
    dxf_file = r"C:\Users\admin\Desktop\PU-06_M250297-P1.dxf"
    # 输出到文件夹
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "output")
    csv_path = r"C:\Users\admin\Desktop\project_environment\05_自动生成板料线\dxf图纸信息汇总表.csv"
    # 定义日志路径
    log_file = os.path.join(current_dir, "logs")
    # 定义0，0坐标json文件保存路径为输出文件夹下的json_0_0文件夹
    json_0_0_dir = os.path.join(output_dir, "json_0_0")
    
    if process_single_dxf(dxf_file, output_dir, log_file, csv_path, json_0_0_dir):
        print("处理成功！")
    else:
        print("处理失败")

