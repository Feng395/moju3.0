#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高精度L/W/T提取器
通过多重验证和上下文分析提高提取精度
"""

import os
import re
import ezdxf
import pandas as pd
from typing import Dict, List, Optional, Tuple
from collections import Counter
import math

class PrecisionLWTExtractor:
    def __init__(self, dxf_path: str, enable_triple_filter: bool = False):
        self.dxf_path = dxf_path
        self.enable_triple_filter = enable_triple_filter
        self.doc = ezdxf.readfile(dxf_path)
        self.msp = self.doc.modelspace()
        self.lwt_candidates = []
        
    def extract_with_context(self) -> List[Dict]:
        """
        带上下文信息的L/W/T提取
        """
        print("开始高精度L/W/T提取...")
        
        # 1. 提取所有文本实体及其位置信息
        text_entities = self._get_all_text_entities()
        print(f"发现 {len(text_entities)} 个文本实体")
        
        # 2. 识别L/W/T候选项
        lwt_candidates = self._identify_lwt_candidates(text_entities)
        print(f"识别出 {len(lwt_candidates)} 个L/W/T候选项")
        
        # 3. 上下文验证
        validated_lwt = self._validate_with_context(lwt_candidates)
        print(f"上下文验证后保留 {len(validated_lwt)} 个有效L/W/T")
        
        # 4. 几何验证
        final_lwt = self._geometric_validation(validated_lwt)
        print(f"几何验证后最终保留 {len(final_lwt)} 个L/W/T")
        
        # 5. 可选的三重条件筛选
        if self.enable_triple_filter:
            print("🔍 启用三重条件筛选...")
            before_count = len(final_lwt)
            final_lwt = self._apply_triple_condition_filter(final_lwt)
            after_count = len(final_lwt)
            
            print(f"📊 三重条件筛选结果:")
            print(f"   筛选前: {before_count} 个候选项")
            print(f"   筛选后: {after_count} 个候选项")
            if before_count > 0:
                print(f"   过滤率: {((before_count - after_count) / before_count * 100):.1f}%")
        
        return final_lwt
    
    def _get_all_text_entities(self) -> List[Dict]:
        """
        获取所有文本实体及其位置信息
        """
        entities = []
        
        for entity in self.msp.query('TEXT MTEXT'):
            text_content = ""
            position = None
            
            if entity.dxftype() == 'TEXT':
                text_content = entity.dxf.text
                position = (entity.dxf.insert.x, entity.dxf.insert.y)
            elif entity.dxftype() == 'MTEXT':
                text_content = entity.text
                position = (entity.dxf.insert.x, entity.dxf.insert.y)
            
            if text_content and position:
                entities.append({
                    'text': text_content.replace('\n', ' ').strip(),
                    'position': position,
                    'entity': entity,
                    'type': entity.dxftype()
                })
        
        return entities
    
    def _identify_lwt_candidates(self, text_entities: List[Dict]) -> List[Dict]:
        """
        识别L/W/T候选项，使用更严格的模式
        """
        candidates = []
        
        # 更严格的L/W/T模式
        patterns = [
            # 标准格式: 数值+单位+分隔符+数值+单位+分隔符+数值+单位
            r'(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])',
            # 带括号格式: (L×W×T)
            r'\(\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])\s*\)',
            # 材料规格格式: 板材 L×W×T
            r'板材?\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])',
        ]
        
        for entity in text_entities:
            text = entity['text']
            
            # 跳过明显不是尺寸标注的文本
            if self._is_non_dimension_text(text):
                continue
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    lwt_dict = self._parse_match_groups(match.groups())
                    if lwt_dict and self._is_valid_lwt_values(lwt_dict):
                        candidates.append({
                            'lwt': lwt_dict,
                            'raw_text': text,
                            'matched_text': match.group(0),
                            'position': entity['position'],
                            'entity': entity['entity'],
                            'confidence': self._calculate_confidence(text, match.group(0))
                        })
        
        return candidates
    
    def _is_non_dimension_text(self, text: str) -> bool:
        """
        判断是否为非尺寸标注文本
        """
        # 排除关键词
        exclude_keywords = [
            '图号', '比例', '日期', '设计', '审核', '标准化', '会签', '批准',
            '材料', '热处理', '表面处理', '重量', '备注', '说明',
            '版本', '修改', '页码', '共', '页', '第', '张',
            '公司', '厂', '部门', '车间', '工艺', '检验'
        ]
        
        for keyword in exclude_keywords:
            if keyword in text:
                return True
        
        # 排除纯字母或纯符号
        if re.match(r'^[A-Za-z\s\-_]+$', text) or re.match(r'^[\W\s]+$', text):
            return True
        
        return False
    
    def _parse_match_groups(self, groups: Tuple) -> Optional[Dict[str, float]]:
        """
        解析正则匹配组，提取L/W/T值
        """
        if len(groups) != 6:
            return None
        
        try:
            lwt_dict = {}
            for i in range(0, 6, 2):
                value = float(groups[i])
                unit = groups[i+1].upper()
                lwt_dict[unit] = value
            
            # 确保包含L、W、T三个值
            if set(lwt_dict.keys()) == {'L', 'W', 'T'}:
                return lwt_dict
        except (ValueError, IndexError):
            pass
        
        return None
    
    def _is_valid_lwt_values(self, lwt_dict: Dict[str, float]) -> bool:
        """
        验证L/W/T值的合理性
        """
        l, w, t = lwt_dict['L'], lwt_dict['W'], lwt_dict['T']
        
        # 基本范围检查
        if not (0.1 <= l <= 10000 and 0.1 <= w <= 10000 and 0.1 <= t <= 1000):
            return False
        
        # 比例合理性检查
        max_val = max(l, w, t)
        min_val = min(l, w, t)
        if max_val / min_val > 10000:  # 比例不应过于悬殊
            return False
        
        # 厚度通常是最小值
        if t > max(l, w) * 2:  # 厚度不应超过长宽的2倍
            return False
        
        return True
    
    def _calculate_confidence(self, full_text: str, matched_text: str) -> float:
        """
        计算匹配置信度
        """
        confidence = 0.5  # 基础置信度
        
        # 包含关键词提高置信度
        positive_keywords = ['板材', '钢板', '材料', '规格', '尺寸', 'L', 'W', 'T']
        for keyword in positive_keywords:
            if keyword in full_text:
                confidence += 0.1
        
        # 格式规整性
        if '×' in matched_text or '*' in matched_text:
            confidence += 0.1
        
        # 括号包围
        if matched_text.startswith('(') and matched_text.endswith(')'):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _validate_with_context(self, candidates: List[Dict]) -> List[Dict]:
        """
        基于上下文验证L/W/T候选项
        """
        validated = []
        
        for candidate in candidates:
            # 置信度过滤
            if candidate['confidence'] < 0.6:
                continue
            
            # 位置合理性检查
            if self._is_reasonable_position(candidate['position']):
                validated.append(candidate)
        
        return validated
    
    def _is_reasonable_position(self, position: Tuple[float, float]) -> bool:
        """
        检查位置是否合理（不在图框边缘等）
        """
        x, y = position
        
        # 获取图纸边界
        all_entities = list(self.msp)
        if not all_entities:
            return True
        
        # 简单的边界检查（可以根据实际情况调整）
        return True  # 暂时返回True，可以根据需要添加更复杂的逻辑
    
    def _geometric_validation(self, candidates: List[Dict]) -> List[Dict]:
        """
        几何验证：检查L/W/T值是否与图形几何匹配
        """
        # 获取所有闭合区域
        closed_regions = self._find_closed_regions()
        
        validated = []
        for candidate in candidates:
            lwt = candidate['lwt']
            
            # 查找匹配的几何区域
            matching_regions = self._find_matching_regions(lwt, closed_regions)
            
            if matching_regions:
                candidate['matching_regions'] = matching_regions
                validated.append(candidate)
        
        return validated
    
    def _find_closed_regions(self) -> List[Dict]:
        """
        查找闭合区域（简化版本）
        """
        regions = []
        
        # 查找矩形和多边形
        for entity in self.msp.query('LWPOLYLINE POLYLINE'):
            if hasattr(entity, 'is_closed') and entity.is_closed:
                try:
                    # 获取边界框
                    points = list(entity.vertices())
                    if len(points) >= 3:
                        x_coords = [p[0] for p in points]
                        y_coords = [p[1] for p in points]
                        
                        min_x, max_x = min(x_coords), max(x_coords)
                        min_y, max_y = min(y_coords), max(y_coords)
                        
                        width = max_x - min_x
                        height = max_y - min_y
                        
                        if width > 1 and height > 1:  # 过滤太小的区域
                            regions.append({
                                'entity': entity,
                                'bbox': (min_x, min_y, max_x, max_y),
                                'width': width,
                                'height': height,
                                'area': width * height
                            })
                except Exception as e:
                    continue
        
        return regions
    
    def _find_matching_regions(self, lwt: Dict[str, float], regions: List[Dict]) -> List[Dict]:
        """
        查找与L/W/T值匹配的几何区域
        """
        l, w, t = lwt['L'], lwt['W'], lwt['T']
        tolerance = 5.0  # 容差
        
        matching = []
        for region in regions:
            rw, rh = region['width'], region['height']
            
            # 检查是否匹配L×W
            if ((abs(rw - l) <= tolerance and abs(rh - w) <= tolerance) or
                (abs(rw - w) <= tolerance and abs(rh - l) <= tolerance)):
                matching.append(region)
        
        return matching
    
    def _apply_triple_condition_filter(self, candidates: List[Dict]) -> List[Dict]:
        """
        三重条件筛选：子图编号 + PCS + 加工说明
        """
        try:
            filtered_candidates = []
            
            for candidate in candidates:
                try:
                    # 安全的文本提取
                    text = candidate.get('raw_text', '')
                    if not text:
                        continue
                    
                    # 条件1：检查子图编号
                    has_subgraph, subgraph_id = self._has_subgraph_id(text)
                    
                    # 条件2：检查PCS（已确认，因为来自PCS文本）
                    has_pcs = 'PCS' in text.upper()
                    
                    # 条件3：检查加工说明
                    has_processing, keywords = self._has_processing_info(text)
                    
                    if has_subgraph and has_pcs and has_processing:
                        # 增强候选项信息
                        candidate['subgraph_id'] = subgraph_id
                        candidate['processing_keywords'] = keywords
                        candidate['triple_condition_score'] = 1.0
                        filtered_candidates.append(candidate)
                        
                except Exception as e:
                    print(f"⚠️ 处理候选项时出错: {e}")
                    continue
            
            return filtered_candidates
            
        except Exception as e:
            print(f"❌ 三重条件筛选失败，回退到原始结果: {e}")
            return candidates  # 回退策略
    
    def _has_subgraph_id(self, text: str) -> tuple:
        """检查是否包含子图编号"""
        patterns = [
            r'[A-Z]\d+[-_]\d+',           # A1-1, B2-3 等
            r'[A-Z]\d+',                  # A1, B2, C3 等
            r'\d+[-_]\d+',                # 1-1, 2-3 等
            r'ps[-_]?\d+',                # ps-1, ps1, ps_2 等
            r'PS[-_]?\d+',                # PS-1, PS1, PS_2 等
            r'[A-Z]{2,3}[-_]?\d+',        # DIE-1, TOP-2 等
            r'M\d+[-_]P\d+',              # M250286-P2 等
        ]
        
        try:
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return True, match.group(0)
        except Exception as e:
            print(f"⚠️ 子图编号匹配出错: {e}")
        
        return False, ""
    
    def _has_processing_info(self, text: str) -> tuple:
        """检查是否包含加工说明或注释"""
        keywords = [
            '45#', 'CR12MOV', 'SECC', 'P20', 'SKD11', 'SKH51',  # 材料
            'HRC', 'HB', 'HV',                                    # 硬度
            '淬火', '回火', '调质', '退火',                        # 热处理
            '镀', '氧化', '发黑', '喷砂',                          # 表面处理
            '精加工', '粗加工', '半精加工',                        # 加工精度
            '车', '铣', '钻', '磨', '刨', '镗',                    # 加工方法
            '公差', '配合', '基准',                               # 技术要求
            'Ra', 'Rz',                                          # 表面粗糙度
            '备注', '说明', '注意', '要求'                         # 通用说明
        ]
        
        try:
            found_keywords = []
            text_upper = text.upper()
            
            for keyword in keywords:
                if keyword.upper() in text_upper:
                    found_keywords.append(keyword)
            
            # 检查L*W*T信息（也算作加工说明）
            if re.search(r'\d+(?:\.\d+)?L\*\d+(?:\.\d+)?W\*\d+(?:\.\d+)?T', text, re.IGNORECASE):
                found_keywords.append('LWT尺寸')
            
            # 检查几何尺寸
            if re.search(r'[φΦ]\s*\d+', text) or re.search(r'R\s*\d+', text):
                found_keywords.append('几何尺寸')
            
            return len(found_keywords) > 0, found_keywords
            
        except Exception as e:
            print(f"⚠️ 加工说明匹配出错: {e}")
            return False, []

def analyze_with_precision(dxf_file_path: str, enable_triple_filter: bool = False):
    """
    使用高精度提取器分析DXF文件
    
    Args:
        dxf_file_path: DXF文件路径
        enable_triple_filter: 是否启用三重条件筛选
    
    Returns:
        提取结果列表
    """
    extractor = PrecisionLWTExtractor(dxf_file_path, enable_triple_filter=enable_triple_filter)
    results = extractor.extract_with_context()
    
    if not results:
        print("未找到有效的L/W/T信息")
        return None
    
    print(f"\n高精度提取结果:")
    print("-" * 80)
    
    for i, result in enumerate(results):
        lwt = result['lwt']
        print(f"零件 {i+1:2d}: L={lwt['L']:6.1f}, W={lwt['W']:6.1f}, T={lwt['T']:5.1f}")
        print(f"         置信度: {result['confidence']:.2f}")
        print(f"         原始文本: {result['raw_text'][:50]}...")
        print(f"         匹配文本: {result['matched_text']}")
        if 'matching_regions' in result:
            print(f"         匹配区域: {len(result['matching_regions'])} 个")
        if 'subgraph_id' in result:
            print(f"         子图编号: {result['subgraph_id']}")
        if 'processing_keywords' in result:
            print(f"         加工说明: {', '.join(result['processing_keywords'][:3])}")
        print()
    
    print(f"总计识别: {len(results)} 个L/W/T")
    print(f"三重条件筛选: {'启用' if enable_triple_filter else '禁用'}")
    
    return results

if __name__ == "__main__":
    dxf_file = r"D:\my_project\cadagent\sheet_line\M250286-P8-20260203.dxf"
    results = analyze_with_precision(dxf_file)