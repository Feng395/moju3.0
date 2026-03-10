#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版三重条件处理器 - 消除冗余逻辑，提升性能
在不影响其他流程的前提下优化第三个系统
"""

import os
import re
import sys
import io

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ezdxf
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import time
from triple_condition_config import TripleConditionConfig

class OptimizedTripleConditionProcessor:
    """优化版三重条件处理器"""
    
    # 类级别常量 - 消除重复定义
    LWT_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])',
        r'\(\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])\s*\)',
        r'板材?\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])\s*[x\*×]\s*(\d+(?:\.\d+)?)\s*([LWT])',
    ]
    
    SUBGRAPH_PATTERNS = [
        # 高优先级：明确的子图编号模式
        r'[A-Z]{2,}[-_]?\d+',         # PU-15, DIE-1, TOP-2, PS-1 等（2个或更多字母）
        r'[A-Z]\d+[-_]\d+',           # A1-1, B2-3 等（字母-数字-数字）
        r'M\d+[-_]P\d+',              # M250286-P2 等（特殊格式）
        r'\d+[-_]\d+',                # 1-1, 2-3 等（纯数字组合）
        # 低优先级：单字母+数字（需要排除几何标注）
        r'(?![rRcCφΦ])[A-Z]\d+',      # A1, B2等，但排除r12, R12, c350, C410, φ20, Φ30
    ]
    
    # 几何标注模式（用于排除）
    GEOMETRY_PATTERNS = [
        r'[rR]\d+(?:\.\d+)?',         # r12, R25.5 等圆弧半径
        r'[cCφΦ]\d+(?:\.\d+)?',       # c350, C410, φ20, Φ30 等圆/孔直径
        r'M\d+(?:\.\d+)?(?:x\d+(?:\.\d+)?)?',  # M6, M8x1.25 等螺纹
        r'∠\d+(?:\.\d+)?',            # ∠45 等角度
        r'\d+(?:\.\d+)?°',            # 45° 等角度
    ]
    
    PROCESSING_KEYWORDS = [
        # 材料
        '45#', 'CR12MOV', 'SECC', 'P20', 'SKD11', 'SKH51', 'SKD61',
        'Q235', 'Q345', 'S45C', 'S50C', 'SUJ2', 'SUS304', 'SUS316',
        # 硬度
        'HRC', 'HB', 'HV', 'HRA',
        # 热处理
        '淬火', '回火', '调质', '退火', '正火', '渗碳', '氮化',
        # 表面处理
        '镀', '氧化', '发黑', '喷砂', '抛光', '电镀', '阳极氧化',
        '镀锌', '镀铬', '镀镍', '喷涂', '烤漆',
        # 加工精度
        '精加工', '粗加工', '半精加工', '超精加工',
        # 加工方法
        '车', '铣', '钻', '磨', '刨', '镗', '拉', '滚',
        '线切割', '电火花', 'EDM', 'CNC',
        # 技术要求
        '公差', '配合', '基准', '同轴度', '垂直度', '平行度',
        '圆度', '圆柱度', '平面度', '直线度',
        # 表面粗糙度
        'Ra', 'Rz', 'Ry', 'Rq',
        # 通用说明
        '备注', '说明', '注意', '要求', '特殊要求', '技术要求'
    ]
    
    # 配置参数 - 从配置文件读取
    DEFAULT_DIMENSIONS = {
        'ps': {'L': 100.0, 'W': 80.0, 'T': 10.0},
        'default': {'L': 120.0, 'W': 90.0, 'T': 12.0},
        'large': {'L': 200.0, 'W': 150.0, 'T': 20.0},
        'small': {'L': 50.0, 'W': 40.0, 'T': 5.0}
    }
    
    def __init__(self, dxf_path: str):
        self.dxf_path = dxf_path
        self.doc = ezdxf.readfile(dxf_path)
        self.msp = self.doc.modelspace()
        
        # 性能优化：预编译正则表达式
        self._compiled_lwt_patterns = [re.compile(p, re.IGNORECASE) for p in self.LWT_PATTERNS]
        self._compiled_subgraph_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUBGRAPH_PATTERNS]
        self._compiled_geometry_patterns = [re.compile(p, re.IGNORECASE) for p in self.GEOMETRY_PATTERNS]
        self._compiled_geometry_pattern = re.compile(r'[φΦ]\s*\d+|R\s*\d+')
        self._compiled_number_pattern = re.compile(r'\d+(?:\.\d+)?')
        
        # 缓存机制
        self._text_cache = {}
        self._lwt_cache = {}
        self._subgraph_cache = {}
        self._processing_cache = {}
        
        # 视图中心位置缓存（用于改进position参数）
        self._last_view_center = None
        
        # 统计信息
        self.stats = {
            'total_texts': 0,
            'pcs_texts': 0,
            'triple_candidates': 0,
            'processing_time': 0,
            'cache_hits': 0
        }
    
    def apply_triple_condition_strategy(self) -> List[Dict]:
        """
        优化版三重条件策略：一次遍历完成所有处理
        """
        start_time = time.time()
        
        print("=" * 80)
        print("优化版三重条件策略处理")
        print("=" * 80)
        
        # 一次遍历完成所有处理 - 核心优化
        processing_candidates = self._single_pass_processing()
        
        # ✅ 新增：零件去重机制
        print(f"🔍 去重前候选项数量: {len(processing_candidates)}")
        processing_candidates = self._deduplicate_candidates(processing_candidates)
        print(f"✅ 去重后候选项数量: {len(processing_candidates)}")
        
        # 统计信息
        self.stats['processing_time'] = time.time() - start_time
        self._print_performance_stats()
        
        return processing_candidates
    
    def _deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """
        零件去重：移除L×W×T和位置相同的重复候选项
        
        去重策略：
        1. 比较L×W×T（容差2mm）
        2. 比较位置（距离<100mm）
        3. 如果两个候选项满足上述条件，认为是重复
        4. 保留置信度更高的一个
        """
        if len(candidates) <= 1:
            return candidates
        
        unique_candidates = []
        lwt_tolerance = 2.0  # L×W×T容差2mm
        position_tolerance = 100.0  # 位置容差100mm
        
        for candidate in candidates:
            lwt = candidate.get('lwt', {})
            position = candidate.get('position', (0, 0))
            confidence = candidate.get('confidence', 0)
            
            # 检查是否与已有候选项重复
            is_duplicate = False
            for unique_candidate in unique_candidates:
                unique_lwt = unique_candidate.get('lwt', {})
                unique_position = unique_candidate.get('position', (0, 0))
                unique_confidence = unique_candidate.get('confidence', 0)
                
                # 比较L×W×T
                lwt_match = (
                    abs(lwt.get('L', 0) - unique_lwt.get('L', 0)) < lwt_tolerance and
                    abs(lwt.get('W', 0) - unique_lwt.get('W', 0)) < lwt_tolerance and
                    abs(lwt.get('T', 0) - unique_lwt.get('T', 0)) < lwt_tolerance
                )
                
                # 比较位置
                distance = ((position[0] - unique_position[0])**2 + 
                           (position[1] - unique_position[1])**2)**0.5
                position_match = distance < position_tolerance
                
                if lwt_match and position_match:
                    is_duplicate = True
                    # 如果当前候选项置信度更高，替换已有的
                    if confidence > unique_confidence:
                        print(f"  >> 替换重复候选项: L={lwt['L']:.1f}, W={lwt['W']:.1f}, T={lwt['T']:.1f}, "
                              f"置信度 {unique_confidence:.2f} → {confidence:.2f}")
                        unique_candidates.remove(unique_candidate)
                        unique_candidates.append(candidate)
                    else:
                        print(f"  >> 跳过重复候选项: L={lwt['L']:.1f}, W={lwt['W']:.1f}, T={lwt['T']:.1f}, "
                              f"置信度 {confidence:.2f} <= {unique_confidence:.2f}")
                    break
            
            if not is_duplicate:
                unique_candidates.append(candidate)
        
        return unique_candidates
    
    def _single_pass_processing(self) -> List[Dict]:
        """
        单次遍历处理 - 消除多次遍历的冗余
        """
        processing_candidates = []
        
        for entity in self.msp.query('TEXT MTEXT'):
            self.stats['total_texts'] += 1
            
            # 统一文本提取 - 消除类型判断冗余
            text_info = self._extract_text_info(entity)
            if not text_info:
                continue
            
            text = text_info['text']
            
            # 早期筛选 - PCS文本或包含子图ID的文本
            text_upper = text.upper()
            has_pcs = 'PCS' in text_upper
            
            # 快速检查是否包含子图ID
            has_potential_subgraph = False
            for pattern in self._compiled_subgraph_patterns:
                if pattern.search(text):
                    # 确保不是几何标注
                    is_geometry = any(geo_pattern.search(text) for geo_pattern in self._compiled_geometry_patterns)
                    if not is_geometry:
                        has_potential_subgraph = True
                        break
            
            # 如果既没有PCS也没有子图ID，跳过
            if not has_pcs and not has_potential_subgraph:
                continue
            
            self.stats['pcs_texts'] += 1
            
            # 一次性完成所有条件检查和数据提取
            candidate_data = self._comprehensive_analysis(text_info)
            
            if candidate_data and candidate_data['meets_triple_condition']:
                self.stats['triple_candidates'] += 1
                
                # 直接生成最终处理候选项 - 消除中间数据结构
                processing_candidate = self._create_final_candidate(candidate_data, text_info)
                if processing_candidate:
                    processing_candidates.append(processing_candidate)
        
        print(f"📋 发现PCS文本: {self.stats['pcs_texts']} 个")
        print(f"🔍 三重条件筛选: {self.stats['triple_candidates']} 个")
        print(f"✅ 生成处理候选项: {len(processing_candidates)} 个")
        
        return processing_candidates
    
    def _extract_text_info(self, entity) -> Optional[Dict]:
        """
        统一文本信息提取 - 消除类型判断冗余
        """
        try:
            if entity.dxftype() == 'TEXT':
                text_content = entity.dxf.text
                position = (entity.dxf.insert.x, entity.dxf.insert.y)
            elif entity.dxftype() == 'MTEXT':
                text_content = entity.text
                position = (entity.dxf.insert.x, entity.dxf.insert.y)
            else:
                return None
            
            if not text_content:
                return None
            
            # 延迟文本预处理 - 只在需要时处理
            return {
                'raw_text': text_content,
                'text': text_content.replace('\n', ' ').strip(),
                'position': position,
                'entity': entity,
                'type': entity.dxftype()
            }
        except Exception:
            return None
    
    def _comprehensive_analysis(self, text_info: Dict) -> Optional[Dict]:
        """
        综合分析 - 一次性完成所有检查和提取
        """
        text = text_info['text']
        text_hash = hash(text)  # 用于缓存
        
        # 缓存检查 - 避免重复计算
        if text_hash in self._text_cache:
            self.stats['cache_hits'] += 1
            return self._text_cache[text_hash]
        
        # 一次性完成所有分析
        analysis_result = {
            'meets_triple_condition': False,
            'subgraph_id': None,
            'processing_keywords': [],
            'lwt_data': None,
            'has_lwt_format': False,
            'confidence_factors': {}
        }
        
        # 条件1：子图编号检查
        subgraph_result = self._check_subgraph_id_cached(text)
        has_subgraph = subgraph_result[0]
        analysis_result['subgraph_id'] = subgraph_result[1]
        
        # 条件2：PCS检查（重新检查，因为上层逻辑已放宽）
        has_pcs = 'PCS' in text.upper()
        
        # 条件3：加工说明检查
        processing_result = self._check_processing_info_cached(text)
        has_processing = processing_result[0]
        analysis_result['processing_keywords'] = processing_result[1]
        
        # 三重条件判断（放宽：子图ID + (PCS 或 加工说明)）
        if has_subgraph and (has_pcs or has_processing):
            analysis_result['meets_triple_condition'] = True
            
            # L/W/T数据提取（只对符合条件的进行）
            lwt_result = self._extract_lwt_comprehensive(text)
            analysis_result['lwt_data'] = lwt_result['lwt_dict']
            analysis_result['has_lwt_format'] = lwt_result['has_format']
            
            # 置信度因子计算
            analysis_result['confidence_factors'] = {
                'has_lwt_format': lwt_result['has_format'],
                'keyword_count': len(processing_result[1]),
                'subgraph_type': self._classify_subgraph_type(subgraph_result[1])
            }
        
        # 缓存结果
        self._text_cache[text_hash] = analysis_result
        return analysis_result
    
    def _check_subgraph_id_cached(self, text: str) -> Tuple[bool, str]:
        """缓存版子图编号检查（带几何标注过滤）"""
        text_hash = hash(text)
        if text_hash in self._subgraph_cache:
            return self._subgraph_cache[text_hash]
        
        # 首先检查是否为几何标注，如果是则直接排除
        for geometry_pattern in self._compiled_geometry_patterns:
            if geometry_pattern.search(text):
                result = (False, "")
                self._subgraph_cache[text_hash] = result
                return result
        
        # 然后检查子图模式
        for pattern in self._compiled_subgraph_patterns:
            match = pattern.search(text)
            if match:
                matched_text = match.group(0)
                
                # 二次验证：确保匹配的文本不是几何标注
                is_geometry = False
                for geometry_pattern in self._compiled_geometry_patterns:
                    if geometry_pattern.fullmatch(matched_text):
                        is_geometry = True
                        break
                
                if not is_geometry:
                    result = (True, matched_text)
                    self._subgraph_cache[text_hash] = result
                    return result
        
        result = (False, "")
        self._subgraph_cache[text_hash] = result
        return result
    
    def _check_processing_info_cached(self, text: str) -> Tuple[bool, List[str]]:
        """缓存版加工说明检查"""
        text_hash = hash(text)
        if text_hash in self._processing_cache:
            return self._processing_cache[text_hash]
        
        found_keywords = []
        text_upper = text.upper()
        
        # 批量关键词检查 - 优化字符串搜索
        for keyword in self.PROCESSING_KEYWORDS:
            if keyword.upper() in text_upper:
                found_keywords.append(keyword)
        
        # 几何尺寸检查
        if self._compiled_geometry_pattern.search(text):
            found_keywords.append('几何尺寸')
        
        result = (len(found_keywords) > 0, found_keywords)
        self._processing_cache[text_hash] = result
        return result
    
    def _extract_lwt_comprehensive(self, text: str) -> Dict:
        """
        综合L/W/T提取 - 合并检查和提取逻辑
        """
        text_hash = hash(text)
        if text_hash in self._lwt_cache:
            return self._lwt_cache[text_hash]
        
        result = {
            'has_format': False,
            'lwt_dict': None
        }
        
        # 使用预编译的正则表达式
        for pattern in self._compiled_lwt_patterns:
            match = pattern.search(text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 6:
                        lwt_dict = {}
                        for i in range(0, 6, 2):
                            value = float(groups[i])
                            unit = groups[i+1].upper()
                            lwt_dict[unit] = value
                        
                        if set(lwt_dict.keys()) == {'L', 'W', 'T'}:
                            result = {
                                'has_format': True,
                                'lwt_dict': lwt_dict
                            }
                            break
                except (ValueError, IndexError):
                    continue
        
        self._lwt_cache[text_hash] = result
        return result
    
    def _create_final_candidate(self, analysis_data: Dict, text_info: Dict) -> Optional[Dict]:
        """
        创建最终候选项 - 集成文本重构（方案2）
        改进：强制查找视图中心位置，无论L×W×T来源如何
        """
        try:
            # 获取或估算L/W/T
            lwt_dict = analysis_data['lwt_data']
            if not lwt_dict:
                lwt_dict = self._estimate_lwt_optimized(text_info['text'], analysis_data['subgraph_id'])
            
            if not lwt_dict:
                return None
            
            # ✅ 关键改进：无论L×W×T来源如何，都尝试查找视图中心
            subgraph_position = self._find_subgraph_text_position(text_info['text'], analysis_data['subgraph_id'])
            
            views_data = []  # ✅ 新增：保存视图数据
            
            if subgraph_position:
                # 优先尝试从视图提取L×W×T（同时获取视图中心）
                view_result = self._find_views_and_extract_lwt(subgraph_position, analysis_data['subgraph_id'])
                if view_result and 'view_center' in view_result:
                    position = view_result['view_center']
                    views_data = view_result.get('views', [])  # ✅ 保存视图数据
                    print(f"  >> 使用视图中心位置: ({position[0]:.1f}, {position[1]:.1f})")
                else:
                    # 如果找不到视图，尝试查找视图中心（不提取L×W×T）
                    view_center = self._find_view_center_near_text(subgraph_position, lwt_dict)
                    position = view_center if view_center and view_center != subgraph_position else subgraph_position
                    if position != subgraph_position:
                        print(f"  >> 使用查找到的视图中心: ({position[0]:.1f}, {position[1]:.1f})")
                    else:
                        print(f"  >> 未找到视图中心，使用文本位置: ({position[0]:.1f}, {position[1]:.1f})")
            else:
                position = text_info['position']
                print(f"  >> 使用文本实体位置: ({position[0]:.1f}, {position[1]:.1f})")
            
            # 文本重构：将L×W×T插入到原始文本中
            reconstructed_text = TripleConditionConfig.reconstruct_text_with_dimensions(
                text_info['text'], lwt_dict
            )
            
            # 计算置信度
            confidence = self._calculate_optimized_confidence(analysis_data['confidence_factors'])
            
            # 重置视图中心缓存
            self._last_view_center = None
            
            # 精简的数据结构
            return {
                'lwt': lwt_dict,
                'raw_text': text_info['text'],                    # 原始文本
                'reconstructed_text': reconstructed_text,         # 重构后的文本
                'matched_text': f"三重条件: {analysis_data['subgraph_id']}",
                'position': position,                             # 使用视图中心位置
                'entity': text_info['entity'],
                'confidence': confidence,
                'source_type': 'cad_extraction_optimized',
                'subgraph_id': analysis_data['subgraph_id'],
                'processing_keywords': analysis_data['processing_keywords'][:3],
                'has_lwt_format': True,  # 重构后都有L×W×T格式
                'extraction_method': 'cad_annotation' if 'CAD标注提取成功' in str(lwt_dict) else 'intelligent_inference',
                'views': views_data  # ✅ 新增：传递视图数据
            }
            
        except Exception as e:
            print(f"⚠️ 创建候选项失败: {e}")
            return None
    
    def _estimate_lwt_optimized(self, text: str, subgraph_id: str) -> Optional[Dict[str, float]]:
            """
            优化版L/W/T估算 - 改进思路：优先从视图提取
            
            优先级：
            1. 从视图提取L×W×T（最可靠）← 新增
            2. CAD标注提取
            3. 文本数字提取
            4. 智能默认值
            """
            # 优先级0：先找到文本位置
            subgraph_position = self._find_subgraph_text_position(text, subgraph_id)
            
            # 优先级1：从视图提取L×W×T（新方法）
            if subgraph_position:
                view_result = self._find_views_and_extract_lwt(subgraph_position, subgraph_id)
                if view_result:
                    # 保存视图中心位置
                    self._last_view_center = view_result['view_center']
                    print(f"✅ 从视图提取L×W×T成功: {subgraph_id} -> {view_result['lwt']}")
                    return view_result['lwt']
            
            # 优先级2：CAD标注提取（原有方法）
            if subgraph_position:
                cad_dimensions = TripleConditionConfig.extract_dimensions_from_cad_simple(
                    self.msp, subgraph_position, subgraph_id
                )
                if cad_dimensions:
                    print(f"✅ CAD标注提取成功: {subgraph_id} -> {cad_dimensions}")
                    # 查找视图中心位置
                    view_center = self._find_view_center_near_text(subgraph_position, cad_dimensions)
                    if view_center and view_center != subgraph_position:
                        self._last_view_center = view_center
                    return cad_dimensions

            # 优先级3：文本数字提取（改进版 - 过滤小值）
            numbers = self._compiled_number_pattern.findall(text)

            if len(numbers) >= 3:
                try:
                    # 过滤：排除<10mm的值（可能是孔径、螺纹规格等）
                    values = [float(n) for n in numbers if 10.0 <= float(n) <= 10000]
                    if len(values) >= 3:
                        values.sort(reverse=True)
                        l, w, t = values[0], values[1], values[2]

                        # 厚度合理性检查
                        if t > min(l, w):
                            t = min(l, w) * 0.1
                        if t < 0.5:
                            t = 5.0

                        lwt_dict = {'L': l, 'W': w, 'T': t}
                        
                        # 查找视图中心位置
                        if subgraph_position:
                            view_center = self._find_view_center_near_text(subgraph_position, lwt_dict)
                            if view_center and view_center != subgraph_position:
                                self._last_view_center = view_center
                        
                        return lwt_dict
                except (ValueError, IndexError):
                    pass

            # 优先级4：智能配置化默认值
            return TripleConditionConfig._intelligent_dimension_inference(text, subgraph_id)

    
    def _find_subgraph_text_position(self, text: str, subgraph_id: str) -> Optional[tuple]:
            """
            查找子图文本在DXF中的位置
            改进：优先查找加工说明文本的位置,而非第一个匹配的文本
            修复：正确处理MTEXT实体的文本内容
            """
            try:
                positions = []
                for entity in self.msp.query('TEXT MTEXT'):
                    # 正确获取文本内容
                    if entity.dxftype() == 'TEXT':
                        entity_text = entity.dxf.text if hasattr(entity.dxf, 'text') else ''
                    elif entity.dxftype() == 'MTEXT':
                        entity_text = entity.text if hasattr(entity, 'text') else ''
                    else:
                        continue
                    
                    if subgraph_id in entity_text:
                        # 获取文本位置
                        position = None
                        if hasattr(entity.dxf, 'insert'):
                            position = (entity.dxf.insert[0], entity.dxf.insert[1])
                        elif hasattr(entity.dxf, 'location'):
                            position = (entity.dxf.location[0], entity.dxf.location[1])

                        if position:
                            # 优先级：加工说明 > 其他文本
                            priority = 0 if '加工说明' in entity_text else 1
                            positions.append((priority, position, entity_text))

                if positions:
                    # 按优先级排序,优先返回加工说明文本的位置
                    positions.sort(key=lambda x: x[0])
                    print(f"  >> 找到子图文本位置: {positions[0][1]}, 优先级={positions[0][0]}")
                    return positions[0][1]

            except Exception as e:
                print(f"⚠️ 查找子图位置失败: {e}")

            return None
    
    def _find_rectangles_from_lines(self, center_position: tuple, search_radius: float) -> List[Dict]:
        """
        从LINE实体中查找矩形视图
        用于识别由LINE组成的视图（而非闭合LWPOLYLINE）
        """
        rectangles = []
        
        try:
            # 按图层分组LINE
            lines_by_layer = {}
            for entity in self.msp.query('LINE'):
                # 检查距离
                line_center_x = (entity.dxf.start[0] + entity.dxf.end[0]) / 2
                line_center_y = (entity.dxf.start[1] + entity.dxf.end[1]) / 2
                distance = ((line_center_x - center_position[0])**2 + 
                           (line_center_y - center_position[1])**2)**0.5
                
                if distance <= search_radius:
                    layer = entity.dxf.layer
                    if layer not in lines_by_layer:
                        lines_by_layer[layer] = []
                    lines_by_layer[layer].append(entity)
            
            # 对每个图层，尝试识别矩形
            for layer, lines in lines_by_layer.items():
                if len(lines) >= 4:  # 至少4条线
                    # 分类为水平线和垂直线
                    horizontal = []
                    vertical = []
                    
                    for line in lines:
                        dx = abs(line.dxf.end[0] - line.dxf.start[0])
                        dy = abs(line.dxf.end[1] - line.dxf.start[1])
                        
                        if dx > dy * 10:  # 水平线
                            horizontal.append(line)
                        elif dy > dx * 10:  # 垂直线
                            vertical.append(line)
                    
                    # 如果有至少2条水平线和2条垂直线
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
                        
                        # 过滤不合理的尺寸（改进：更严格的过滤，避免识别整个图层）
                        if 10 < width < 1000 and 10 < height < 1000 and 100 < area < 200000:
                            center_x = (bbox[0] + bbox[2]) / 2
                            center_y = (bbox[1] + bbox[3]) / 2
                            distance = ((center_x - center_position[0])**2 + 
                                       (center_y - center_position[1])**2)**0.5
                            
                            rectangles.append({
                                'center': (center_x, center_y),
                                'bbox': bbox,
                                'distance': distance,
                                'width': width,
                                'height': height,
                                'area': area,
                                'type': 'line_rectangle',
                                'layer': layer
                            })
                            print(f"  >> 从LINE识别矩形: {width:.1f}x{height:.1f}, 图层={layer}")
        
        except Exception as e:
            print(f"⚠️ 从LINE识别矩形失败: {e}")
        
        return rectangles
    
    def _find_views_by_layer(self, center_position: tuple, search_radius: float) -> List[Dict]:
        """
        按图层分组，查找可能的视图区域
        用于识别包含多种实体类型的复杂视图
        """
        views = []
        
        try:
            # 重点图层（通常包含视图）
            target_layers = ['DIE', 'PH2', 'PS', 'LP', 'UP', 'dim', '0']
            
            for layer_name in target_layers:
                # 查找该图层的所有实体
                entities = list(self.msp.query(f'*[layer=="{layer_name}"]'))
                
                if entities:
                    # 计算边界框
                    xs = []
                    ys = []
                    
                    for entity in entities:
                        try:
                            if entity.dxftype() == 'LINE':
                                xs.extend([entity.dxf.start[0], entity.dxf.end[0]])
                                ys.extend([entity.dxf.start[1], entity.dxf.end[1]])
                            elif entity.dxftype() == 'LWPOLYLINE':
                                points = list(entity.get_points(format='xy'))
                                xs.extend([p[0] for p in points])
                                ys.extend([p[1] for p in points])
                            elif entity.dxftype() == 'CIRCLE':
                                cx, cy = entity.dxf.center[0], entity.dxf.center[1]
                                r = entity.dxf.radius
                                xs.extend([cx - r, cx + r])
                                ys.extend([cy - r, cy + r])
                            elif entity.dxftype() == 'ARC':
                                cx, cy = entity.dxf.center[0], entity.dxf.center[1]
                                r = entity.dxf.radius
                                xs.extend([cx - r, cx + r])
                                ys.extend([cy - r, cy + r])
                        except Exception:
                            continue
                    
                    if xs and ys:
                        bbox = (min(xs), min(ys), max(xs), max(ys))
                        width = bbox[2] - bbox[0]
                        height = bbox[3] - bbox[1]
                        area = width * height
                        center_x = (bbox[0] + bbox[2]) / 2
                        center_y = (bbox[1] + bbox[3]) / 2
                        distance = ((center_x - center_position[0])**2 + 
                                   (center_y - center_position[1])**2)**0.5
                        
                        # 过滤不合理的尺寸（改进：更严格的过滤，避免识别整个图层）
                        # ✅ 修复：不应该把整个图层当成视图，需要根据L×W×T过滤
                        # 跳过明显过大的边界框（可能是整个图层）
                        if distance <= search_radius and 10 < width < 1000 and 10 < height < 1000 and 100 < area < 200000:
                            views.append({
                                'center': (center_x, center_y),
                                'bbox': bbox,
                                'distance': distance,
                                'width': width,
                                'height': height,
                                'area': area,
                                'type': 'layer_group',
                                'layer': layer_name
                            })
                            print(f"  >> 从图层识别视图: {width:.1f}x{height:.1f}, 图层={layer_name}")
        
        except Exception as e:
            print(f"⚠️ 按图层识别视图失败: {e}")
        
        return views
    
    def _is_valid_view_candidate(self, entity, min_area=500, max_area=2000000) -> Optional[Dict]:
        """
        判断实体是否是有效的视图候选
        
        放宽标准：
        1. 不要求完全闭合（允许有小缺口）
        2. 接受近似矩形（允许有小偏差）
        3. 接受包含内部细节的图形
        
        返回：如果是有效候选，返回视图信息字典；否则返回None
        """
        try:
            if entity.dxftype() not in ['LWPOLYLINE', 'POLYLINE']:
                return None
            
            points = list(entity.get_points(format='xy'))
            if len(points) < 3:
                return None
            
            # 计算边界框
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            area = width * height
            
            # 过滤不合理的尺寸
            if area < min_area or area > max_area:
                return None
            
            # ✅ 放宽标准：不要求完全闭合
            # 检查是否"接近闭合"（首尾点距离小于10mm）
            if entity.dxftype() == 'LWPOLYLINE':
                is_closed = entity.closed
                if not is_closed:
                    # 检查首尾点距离
                    first_point = points[0]
                    last_point = points[-1]
                    distance = ((first_point[0] - last_point[0])**2 + 
                               (first_point[1] - last_point[1])**2)**0.5
                    is_nearly_closed = distance < 10.0  # 允许10mm的缺口
                    
                    if not is_nearly_closed:
                        return None
            
            # ✅ 检查是否"接近矩形"
            # 矩形特征：4个角点，边平行于坐标轴
            if len(points) >= 4:
                # 简化检查：边界框面积与实际面积接近
                # 对于矩形，这两个面积应该相等
                # 允许20%的偏差（考虑内部细节）
                actual_area = self._calculate_polygon_area(points)
                if actual_area > 0:
                    area_ratio = actual_area / area
                    if area_ratio < 0.6:  # 实际面积太小，可能不是视图
                        return None
            
            # 计算中心点
            center_x = sum(xs) / len(xs)
            center_y = sum(ys) / len(ys)
            
            return {
                'bbox': bbox,
                'center': (center_x, center_y),
                'width': width,
                'height': height,
                'area': area,
                'entity': entity
            }
            
        except Exception as e:
            return None
    
    def _calculate_polygon_area(self, points: List[tuple]) -> float:
        """计算多边形面积（Shoelace公式）"""
        n = len(points)
        if n < 3:
            return 0.0
        
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2.0
    
    def _find_missing_views_by_expanding_search(self, text_position: tuple, identified_views: Dict[str, Dict], l: float, w: float, t: float) -> Dict[str, Dict]:
        """
        通过扩大搜索范围查找缺失的视图
        
        策略：
        1. 从已识别的视图位置出发
        2. 在标准三视图布局的预期位置搜索
        3. 逐步扩大搜索半径
        4. ✅ 使用放宽的识别标准
        
        不使用全局搜索，避免多子图干扰
        """
        tolerance = 2.0
        excluded_layers = {'GUIDE', 'DIMENSION', 'TEXT', 'ANNOTATION'}  # 不排除DIM图层
        
        # 确定缺失的视图类型
        all_types = {'主视图', '俯视图', '侧视图'}
        missing_types = all_types - set(identified_views.keys())
        
        if not missing_types:
            return identified_views
        
        print(f"  >> 🔍 扩展搜索缺失的视图: {missing_types}")
        
        # 如果有已识别的视图，从它的位置出发搜索
        if identified_views:
            reference_view = list(identified_views.values())[0]
            search_center = reference_view['center']
            print(f"  >> 从已识别视图位置出发: ({search_center[0]:.1f}, {search_center[1]:.1f})")
        else:
            search_center = text_position
            print(f"  >> 从文本位置出发: ({search_center[0]:.1f}, {search_center[1]:.1f})")
        
        # 逐步扩大搜索范围
        search_radii = [5000, 10000, 15000, 20000]
        
        for radius in search_radii:
            if not missing_types:
                break
            
            print(f"  >> 搜索半径: {radius}mm")
            
            # 在当前半径内搜索
            for entity in self.msp.query('LWPOLYLINE POLYLINE'):
                # ✅ 使用放宽的验证标准
                view_info = self._is_valid_view_candidate(entity)
                if not view_info:
                    continue
                
                # 过滤辅助图层
                layer_name = entity.dxf.layer.upper() if hasattr(entity.dxf, 'layer') else ''
                if layer_name in excluded_layers:
                    continue
                
                center_x, center_y = view_info['center']
                
                # 检查距离
                distance = ((center_x - search_center[0])**2 + (center_y - search_center[1])**2)**0.5
                if distance > radius:
                    continue
                
                width = view_info['width']
                height = view_info['height']
                
                view_data = {
                    'bbox': view_info['bbox'],
                    'center': view_info['center'],
                    'width': width,
                    'height': height,
                    'area': view_info['area'],
                    'layer': entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
                }
                
                # 匹配缺失的视图类型（允许更大的容差）
                relaxed_tolerance = 5.0  # 放宽到5mm
                
                if '主视图' in missing_types:
                    if (abs(width - l) < relaxed_tolerance and abs(height - w) < relaxed_tolerance) or \
                       (abs(width - w) < relaxed_tolerance and abs(height - l) < relaxed_tolerance):
                        identified_views['主视图'] = view_data
                        missing_types.remove('主视图')
                        print(f"     ✅ 找到主视图: {width:.1f}x{height:.1f} @ ({center_x:.1f}, {center_y:.1f}), 距离={distance:.1f}mm")
                
                if '俯视图' in missing_types:
                    if (abs(width - l) < relaxed_tolerance and abs(height - t) < relaxed_tolerance) or \
                       (abs(width - t) < relaxed_tolerance and abs(height - l) < relaxed_tolerance):
                        identified_views['俯视图'] = view_data
                        missing_types.remove('俯视图')
                        print(f"     ✅ 找到俯视图: {width:.1f}x{height:.1f} @ ({center_x:.1f}, {center_y:.1f}), 距离={distance:.1f}mm")
                
                if '侧视图' in missing_types:
                    if (abs(width - t) < relaxed_tolerance and abs(height - w) < relaxed_tolerance) or \
                       (abs(width - w) < relaxed_tolerance and abs(height - t) < relaxed_tolerance):
                        identified_views['侧视图'] = view_data
                        missing_types.remove('侧视图')
                        print(f"     ✅ 找到侧视图: {width:.1f}x{height:.1f} @ ({center_x:.1f}, {center_y:.1f}), 距离={distance:.1f}mm")
            
            if not missing_types:
                print(f"  >> ✅ 在半径{radius}mm内找到所有视图")
                break
        
        if missing_types:
            print(f"  >> ⚠️ 仍有缺失的视图: {missing_types}")
        
        return identified_views
    
    def _find_all_matching_views_globally(self, l: float, w: float, t: float) -> Dict[str, Dict]:
        """
        在整个图纸中全局搜索所有匹配L×W×T的视图
        
        优势：
        1. 不依赖文本位置，全局搜索
        2. 直接通过尺寸匹配L×W×T
        3. 找到所有可能的视图
        4. 通过空间关系验证
        
        返回: {
            '主视图': {'bbox': ..., 'center': ..., 'width': ..., 'height': ...},
            '俯视图': {...},
            '侧视图': {...}
        }
        """
        tolerance = 2.0
        excluded_layers = {'GUIDE', 'DIMENSION', 'TEXT', 'ANNOTATION'}  # 不排除DIM图层
        
        print(f"  >> 🌍 全局搜索匹配L={l:.1f}, W={w:.1f}, T={t:.1f}的视图...")
        
        identified_views = {}
        
        # 1. 搜索所有闭合LWPOLYLINE
        for entity in self.msp.query('LWPOLYLINE'):
            if not entity.closed:
                continue
            
            # 过滤辅助图层
            layer_name = entity.dxf.layer.upper() if hasattr(entity.dxf, 'layer') else ''
            if layer_name in excluded_layers:
                continue
            
            points = list(entity.get_points(format='xy'))
            if not points:
                continue
            
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            area = width * height
            
            # 过滤不合理的尺寸
            if area < 500 or area > 500000:
                continue
            
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            
            view_data = {
                'bbox': bbox,
                'center': (center_x, center_y),
                'width': width,
                'height': height,
                'area': area,
                'layer': entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
            }
            
            # 匹配视图类型
            # 主视图 (L×W)
            if (abs(width - l) < tolerance and abs(height - w) < tolerance) or \
               (abs(width - w) < tolerance and abs(height - l) < tolerance):
                if '主视图' not in identified_views:
                    identified_views['主视图'] = view_data
                    print(f"     ✅ 主视图: {width:.1f}x{height:.1f} @ ({center_x:.1f}, {center_y:.1f}), 图层={view_data['layer']}")
            
            # 俯视图 (L×T)
            elif (abs(width - l) < tolerance and abs(height - t) < tolerance) or \
                 (abs(width - t) < tolerance and abs(height - l) < tolerance):
                if '俯视图' not in identified_views:
                    identified_views['俯视图'] = view_data
                    print(f"     ✅ 俯视图: {width:.1f}x{height:.1f} @ ({center_x:.1f}, {center_y:.1f}), 图层={view_data['layer']}")
            
            # 侧视图 (T×W)
            elif (abs(width - t) < tolerance and abs(height - w) < tolerance) or \
                 (abs(width - w) < tolerance and abs(height - t) < tolerance):
                if '侧视图' not in identified_views:
                    identified_views['侧视图'] = view_data
                    print(f"     ✅ 侧视图: {width:.1f}x{height:.1f} @ ({center_x:.1f}, {center_y:.1f}), 图层={view_data['layer']}")
        
        # 2. 验证空间关系（如果找到多个视图）
        if len(identified_views) >= 2:
            self._validate_spatial_relationship(identified_views)
        
        print(f"  >> 全局搜索结果: 找到{len(identified_views)}个视图")
        return identified_views
    
    def _identify_views_by_dimensions_and_position(self, candidate_views: List[Dict], l: float, w: float, t: float) -> Dict[str, Dict]:
        """
        通过尺寸和位置关系识别三视图的具体位置
        
        策略：
        1. 根据视图尺寸匹配L×W×T
        2. 验证视图之间的空间关系（对齐、相邻）
        3. 返回识别到的视图及其类型
        
        返回: {
            '主视图': {'bbox': ..., 'center': ..., 'width': ..., 'height': ...},
            '俯视图': {...},
            '侧视图': {...}
        }
        """
        if not candidate_views:
            return {}
        
        tolerance = 5.0  # 尺寸容差5mm（放宽以匹配37.5等非整数尺寸）
        identified_views = {}
        
        print(f"  >> 🔍 开始识别三视图（基于尺寸匹配）...")
        print(f"  >> 目标尺寸: L={l:.1f}, W={w:.1f}, T={t:.1f}")
        
        # 遍历所有候选视图，根据尺寸匹配视图类型
        for view in candidate_views:
            w_view = view['width']
            h_view = view['height']
            
            # 主视图 (L×W)
            if (abs(w_view - l) < tolerance and abs(h_view - w) < tolerance) or \
               (abs(w_view - w) < tolerance and abs(h_view - l) < tolerance):
                if '主视图' not in identified_views:
                    identified_views['主视图'] = view
                    print(f"     ✅ 主视图: {w_view:.1f}x{h_view:.1f} @ ({view['center'][0]:.1f}, {view['center'][1]:.1f})")
            
            # 俯视图 (L×T)
            elif (abs(w_view - l) < tolerance and abs(h_view - t) < tolerance) or \
                 (abs(w_view - t) < tolerance and abs(h_view - l) < tolerance):
                if '俯视图' not in identified_views:
                    identified_views['俯视图'] = view
                    print(f"     ✅ 俯视图: {w_view:.1f}x{h_view:.1f} @ ({view['center'][0]:.1f}, {view['center'][1]:.1f})")
            
            # 侧视图 (T×W)
            elif (abs(w_view - t) < tolerance and abs(h_view - w) < tolerance) or \
                 (abs(w_view - w) < tolerance and abs(h_view - t) < tolerance):
                if '侧视图' not in identified_views:
                    identified_views['侧视图'] = view
                    print(f"     ✅ 侧视图: {w_view:.1f}x{h_view:.1f} @ ({view['center'][0]:.1f}, {view['center'][1]:.1f})")
        
        # 验证空间关系（可选，增强可靠性）
        if len(identified_views) >= 2:
            self._validate_spatial_relationship(identified_views)
        
        return identified_views
    
    def _validate_spatial_relationship(self, identified_views: Dict[str, Dict]) -> bool:
        """
        验证识别到的视图之间的空间关系是否合理
        
        标准第一视角布局：
        - 主视图和俯视图：L对齐（X坐标接近）
        - 主视图和侧视图：W对齐（Y坐标接近）
        """
        tolerance_pos = 50.0  # 位置容差50mm
        
        if '主视图' in identified_views and '俯视图' in identified_views:
            main_x = identified_views['主视图']['center'][0]
            top_x = identified_views['俯视图']['center'][0]
            if abs(main_x - top_x) < tolerance_pos:
                print(f"     ✓ 主视图和俯视图L对齐（X差={abs(main_x - top_x):.1f}mm）")
            else:
                print(f"     ⚠️ 主视图和俯视图L未对齐（X差={abs(main_x - top_x):.1f}mm）")
        
        if '主视图' in identified_views and '侧视图' in identified_views:
            main_y = identified_views['主视图']['center'][1]
            side_y = identified_views['侧视图']['center'][1]
            if abs(main_y - side_y) < tolerance_pos:
                print(f"     ✓ 主视图和侧视图W对齐（Y差={abs(main_y - side_y):.1f}mm）")
            else:
                print(f"     ⚠️ 主视图和侧视图W未对齐（Y差={abs(main_y - side_y):.1f}mm）")
        
        return True
    
    def _extract_lwt_from_text(self, text_position: tuple, search_radius: float) -> Optional[Dict[str, float]]:
        """
        从TEXT/MTEXT实体中提取L×W×T格式的尺寸
        支持格式：
        - 550.0L*530.0W*30.00T
        - 550L×530W×30T
        - 550.0L x 530.0W x 30.00T
        """
        import re
        
        try:
            for entity in self.msp.query('TEXT MTEXT'):
                # 获取文本内容和位置
                if entity.dxftype() == 'TEXT':
                    text = entity.dxf.text
                    pos = (entity.dxf.insert[0], entity.dxf.insert[1])
                else:  # MTEXT
                    text = entity.text
                    pos = (entity.dxf.insert[0], entity.dxf.insert[1])
                
                # 检查距离
                distance = ((pos[0] - text_position[0])**2 + (pos[1] - text_position[1])**2)**0.5
                if distance > search_radius:
                    continue
                
                # 匹配L×W×T格式（支持多种分隔符：*、×、x、X）
                pattern = r'(\d+(?:\.\d+)?)\s*[Ll]\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*[Ww]\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*[HhTt]'
                match = re.search(pattern, text)
                
                if match:
                    l = float(match.group(1))
                    w = float(match.group(2))
                    t = float(match.group(3))
                    
                    # 验证尺寸合理性
                    if 1 < l < 10000 and 1 < w < 10000 and 1 < t < 1000:
                        print(f"  >> 从TEXT提取: {text} @ ({pos[0]:.1f}, {pos[1]:.1f})")
                        return {'L': l, 'W': w, 'T': t}
        
        except Exception as e:
            print(f"⚠️ 从TEXT提取L×W×T失败: {e}")
        
        return None
    
    def _collect_all_views(self, text_position: tuple, search_radius: float) -> List[Dict]:
            """收集所有附近的视图（LWPOLYLINE + LINE矩形 + 图层视图）"""
            x, y = text_position
            candidate_views = []
            
            # 排除的图层列表（辅助线、标注等）
            # ✅ 修复：不要排除dim图层，因为有些图纸的视图就在dim图层上
            excluded_layers = {'GUIDE', 'DIMENSION', 'TEXT', 'ANNOTATION'}
            
            # 1. ✅ 使用放宽标准识别LWPOLYLINE/POLYLINE
            for entity in self.msp.query('LWPOLYLINE POLYLINE'):
                # 使用新的验证函数
                view_info = self._is_valid_view_candidate(entity)
                if not view_info:
                    continue
                
                # 过滤GUIDE等辅助图层
                layer_name = entity.dxf.layer.upper() if hasattr(entity.dxf, 'layer') else ''
                if layer_name in excluded_layers:
                    continue
                
                center_x, center_y = view_info['center']
                distance = ((center_x - x)**2 + (center_y - y)**2)**0.5
                
                if distance <= search_radius:
                    candidate_views.append({
                        'center': view_info['center'],
                        'bbox': view_info['bbox'],
                        'distance': distance,
                        'width': view_info['width'],
                        'height': view_info['height'],
                        'area': view_info['area'],
                        'type': 'lwpolyline',
                        'layer': entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
                    })
            
            # 2. LINE组成的矩形
            line_rectangles = self._find_rectangles_from_lines(text_position, search_radius)
            # 过滤GUIDE层的LINE矩形
            line_rectangles = [v for v in line_rectangles 
                              if v.get('layer', '').upper() not in excluded_layers]
            candidate_views.extend(line_rectangles)
            
            # 2.5 成对LINE组成的矩形（侧视图、俯视图）
            # 需要先尝试从TEXT提取L×W×T，如果有的话
            text_lwt = self._extract_lwt_from_text(text_position, search_radius)
            if text_lwt:
                l, w, t = text_lwt['L'], text_lwt['W'], text_lwt['T']
                paired_rectangles = self._find_paired_line_rectangles(text_position, search_radius, l, w, t)
                # ✅ 调试：检查paired_rectangles的bbox
                for rect in paired_rectangles:
                    bbox = rect.get('bbox')
                    if bbox:
                        print(f"  >> 调试paired_rect: bbox=({bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}), 宽度={bbox[2]-bbox[0]:.1f}")
                # 过滤GUIDE层
                paired_rectangles = [v for v in paired_rectangles 
                                    if v.get('layer', '').upper() not in excluded_layers]
                candidate_views.extend(paired_rectangles)
            
            # 3. 按图层分组的视图
            layer_views = self._find_views_by_layer(text_position, search_radius)
            # 过滤GUIDE层的图层视图
            layer_views = [v for v in layer_views 
                          if v.get('layer', '').upper() not in excluded_layers]
            candidate_views.extend(layer_views)

            # ✅ 去重：移除重复的视图（基于中心位置和尺寸）
            unique_views = []
            tolerance_pos = 10.0  # 位置容差10mm
            tolerance_size = 2.0  # 尺寸容差2mm
            
            for view in candidate_views:
                is_duplicate = False
                for existing in unique_views:
                    # 检查位置和尺寸是否相同
                    pos_diff = ((view['center'][0] - existing['center'][0])**2 + 
                               (view['center'][1] - existing['center'][1])**2)**0.5
                    size_diff_w = abs(view['width'] - existing['width'])
                    size_diff_h = abs(view['height'] - existing['height'])
                    
                    if pos_diff < tolerance_pos and size_diff_w < tolerance_size and size_diff_h < tolerance_size:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_views.append(view)
            
            # 按距离排序
            unique_views.sort(key=lambda v: v['distance'])
            
            if len(unique_views) < len(candidate_views):
                print(f"  >> 去重：{len(candidate_views)}个视图 → {len(unique_views)}个唯一视图")
            
            return unique_views

    
    def _infer_lwt_from_views_by_geometry(self, views: List[Dict]) -> Optional[Dict[str, float]]:
        """
        从视图几何形状推断L×W×T（完全基于视图特征，无回退逻辑）
        
        ✅ 核心策略：从图上直接提取
        1. 过滤有效视图（排除过大/过小的边界框）
        2. 根据位置判断视图类型（主视图、俯视图、侧视图）
        3. 从两个已知视图中提取共享尺寸和独有尺寸
        4. 推断第三视图的尺寸
        
        三视图的特征：
        - 主视图 (L×W): 左上角
        - 俯视图 (L×T): 左下角
        - 侧视图 (T×W): 右上角
        
        共享关系：
        - 主视图 + 俯视图 → 共享L
        - 主视图 + 侧视图 → 共享W
        - 俯视图 + 侧视图 → 共享T
        """
        # 过滤有效视图（排除明显错误的边界框）
        # 放宽面积上限，支持大尺寸零件（如550×530=291500）
        valid_views = [v for v in views if 100 < v['area'] < 500000]
        if not valid_views:
            print(f"  >> ❌ 没有有效视图")
            return None
        
        print(f"  >> 📊 有效视图列表 (共{len(valid_views)}个):")
        for i, v in enumerate(valid_views[:10], 1):
            print(f"     视图{i}: {v['width']:.1f}x{v['height']:.1f}, 面积={v['area']:.1f}, 位置=({v['center'][0]:.1f}, {v['center'][1]:.1f})")
        
        # ✅ 步骤1：根据位置判断视图类型
        views_with_type = self._assign_view_types_by_position(valid_views)
        
        # ✅ 步骤2：从视图中提取L×W×T
        return self._extract_lwt_from_typed_views(views_with_type)
    
    def _infer_lwt_from_two_views(self, views: List[Dict]) -> Optional[Dict[str, float]]:
        """
        从两个视图推断L×W×T
        
        ✅ 改进的两视图推断逻辑：
        1. 找到两个视图的共享尺寸（出现在两个视图中的尺寸）
        2. 从两个视图的所有尺寸中排除共享尺寸
        3. 剩余的两个不同尺寸即为第三视图的尺寸
        4. 根据位置判断视图类型，确定L、W、T的对应关系
        
        例如：
        - 视图1: 50x390 (主视图 L×W) - 位置：X小，Y大
        - 视图2: 50x37  (俯视图 L×T) - 位置：X小，Y小
        - 共享尺寸: 50 (L)
        - 视图1独有: 390 (W)
        - 视图2独有: 37 (T)
        - 推断第三视图: 37x390 (侧视图 T×W) - 位置：X大，Y大
        """
        if not views or len(views) == 0:
            return None
        
        if len(views) == 1:
            # 只有一个视图，假设是主视图(L×W)
            view = views[0]
            dims = sorted([view['width'], view['height']], reverse=True)
            l = dims[0]
            w = dims[1]
            t = w * 0.1  # 估算T
            if t < 0.5:
                t = 5.0
            print(f"  >> 单视图推断: L={l:.1f}, W={w:.1f}, T={t:.1f}(估算)")
            return {'L': l, 'W': w, 'T': t}
        
        # 两个视图 - 先根据位置判断视图类型
        views_with_type = self._assign_view_types_by_position(views)
        
        v1, v2 = views_with_type[0], views_with_type[1]
        v1_dims = [round(v1['width'], 1), round(v1['height'], 1)]
        v2_dims = [round(v2['width'], 1), round(v2['height'], 1)]
        
        print(f"  >> 两视图分析:")
        print(f"     视图1: {v1['width']:.1f}x{v1['height']:.1f}, 类型={v1.get('view_type', '未知')}, 位置=({v1['center'][0]:.1f}, {v1['center'][1]:.1f})")
        print(f"     视图2: {v2['width']:.1f}x{v2['height']:.1f}, 类型={v2.get('view_type', '未知')}, 位置=({v2['center'][0]:.1f}, {v2['center'][1]:.1f})")
        
        # ✅ 找共享尺寸（容差2mm）
        tolerance = 2.0
        shared_dims = []
        v1_unique_dims = []
        v2_unique_dims = []
        
        for d1 in v1_dims:
            matched = False
            for d2 in v2_dims:
                if abs(d1 - d2) < tolerance:
                    if d1 not in [s for s, _ in shared_dims]:  # 避免重复
                        shared_dims.append((d1, d2))
                    matched = True
                    break
            if not matched:
                v1_unique_dims.append(d1)
        
        for d2 in v2_dims:
            matched = False
            for d1 in v1_dims:
                if abs(d1 - d2) < tolerance:
                    matched = True
                    break
            if not matched:
                v2_unique_dims.append(d2)
        
        # 计算共享尺寸的平均值
        shared_avg = [(d1 + d2) / 2 for d1, d2 in shared_dims]
        
        print(f"     共享尺寸: {[f'{d:.1f}' for d in shared_avg]}")
        print(f"     视图1独有: {[f'{d:.1f}' for d in v1_unique_dims]}")
        print(f"     视图2独有: {[f'{d:.1f}' for d in v2_unique_dims]}")
        
        # ✅ 组合所有尺寸：共享 + 视图1独有 + 视图2独有
        all_dims = shared_avg + v1_unique_dims + v2_unique_dims
        
        # 去重（容差内的视为相同）
        unique_dims = []
        for dim in all_dims:
            is_duplicate = False
            for existing in unique_dims:
                if abs(dim - existing) < tolerance:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_dims.append(dim)
        
        unique_dims.sort(reverse=True)
        print(f"     所有不同尺寸: {[f'{d:.1f}' for d in unique_dims]}")
        
        if len(unique_dims) >= 3:
            # ✅ 根据视图类型确定L、W、T
            result = self._determine_lwt_from_view_types(views_with_type, unique_dims)
            
            # ✅ 修复：如果返回None，使用简单排序
            if result is None:
                l, w, t = unique_dims[0], unique_dims[1], unique_dims[2]
                print(f"  >> 推断结果(简单排序): L={l:.1f}, W={w:.1f}, T={t:.1f}")
            else:
                l, w, t = result
                print(f"  >> 推断结果: L={l:.1f}, W={w:.1f}, T={t:.1f}")
            
            return {'L': l, 'W': w, 'T': t}
        elif len(unique_dims) == 2:
            # 只有2个不同尺寸，估算第3个
            l, w = unique_dims[0], unique_dims[1]
            t = w * 0.1
            if t < 0.5:
                t = 5.0
            print(f"  >> 推断结果(估算T): L={l:.1f}, W={w:.1f}, T={t:.1f}")
            return {'L': l, 'W': w, 'T': t}
        else:
            # 回退：使用最大视图的尺寸
            main_view = max(views, key=lambda v: v['area'])
            dims = sorted([main_view['width'], main_view['height']], reverse=True)
            l, w = dims[0], dims[1]
            t = w * 0.1
            if t < 0.5:
                t = 5.0
            print(f"  >> 回退推断: L={l:.1f}, W={w:.1f}, T={t:.1f}(估算)")
            return {'L': l, 'W': w, 'T': t}
    
    def _extract_lwt_from_typed_views(self, views: List[Dict]) -> Optional[Dict[str, float]]:
        """
        从已标记类型的视图中提取L×W×T，并推断缺失的视图
        
        完整流程：
        1. 识别已有的视图类型和尺寸
        2. 根据视图类型推断L×W×T
        3. 如果缺少视图，推断缺失视图的位置和尺寸
        4. 返回完整的三视图信息
        """
        # 按类型分组视图
        typed_views = {}
        for view in views:
            view_type = view.get('view_type', '未知')
            if view_type != '未知':
                if view_type not in typed_views:
                    typed_views[view_type] = []
                typed_views[view_type].append(view)
        
        print(f"  >> 📋 视图类型分组:")
        for vtype, vlist in typed_views.items():
            print(f"     {vtype}: {len(vlist)}个")
            for v in vlist[:2]:
                print(f"       - {v['width']:.1f}x{v['height']:.1f}, 位置=({v['center'][0]:.1f}, {v['center'][1]:.1f})")
        
        # 如果没有识别到任何类型，使用两视图推断
        if not typed_views:
            print(f"  >> ⚠️ 没有识别到视图类型，使用两视图推断")
            return self._infer_lwt_from_two_views(views)
        
        # 收集所有视图的尺寸
        all_dims = []
        for view in views:
            all_dims.extend([view['width'], view['height']])
        
        # 去重（容差2mm）
        tolerance = 2.0
        unique_dims = []
        for dim in all_dims:
            is_duplicate = False
            for existing in unique_dims:
                if abs(dim - existing) < tolerance:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_dims.append(dim)
        
        unique_dims.sort(reverse=True)
        print(f"  >> 📏 所有不同尺寸: {[f'{d:.1f}' for d in unique_dims]}")
        
        # 如果只有2个不同尺寸，说明缺少一个维度
        if len(unique_dims) < 3:
            print(f"  >> ⚠️ 只有{len(unique_dims)}个不同尺寸，使用两视图推断")
            return self._infer_lwt_from_two_views(views)
        
        # ✅ 根据视图类型推断L、W、T
        result = self._determine_lwt_from_view_types(views, unique_dims)
        
        # 如果无法从视图类型推断，使用两视图推断逻辑
        if result is None:
            print(f"  >> ⚠️ 无法从视图类型推断，使用两视图推断逻辑")
            return self._infer_lwt_from_two_views(views)
        
        l, w, t = result
        print(f"  >> ✅ 推断L×W×T: L={l:.1f}, W={w:.1f}, T={t:.1f}")
        
        # ✅ 检查是否缺少视图，如果缺少则推断
        complete_views = self._infer_missing_views(typed_views, l, w, t)
        
        print(f"  >> ✅ 最终结果: L={l:.1f}, W={w:.1f}, T={t:.1f}, 视图数量={len(complete_views)}")
        
        return {
            'L': l, 
            'W': w, 
            'T': t,
            'views': complete_views  # ✅ 返回完整的三视图信息
        }
    
    def _infer_missing_views(self, typed_views: Dict[str, List[Dict]], l: float, w: float, t: float) -> List[Dict]:
        """
        推断缺失的视图位置和尺寸
        
        标准第一视角布局：
        - 主视图 (L×W): 左上角
        - 俯视图 (L×T): 左下角
        - 侧视图 (T×W): 右上角
        
        位置关系：
        - 主视图和俯视图：L对齐（X坐标相同）
        - 主视图和侧视图：W对齐（Y坐标端点相同）
        - 俯视图和侧视图：对角关系
        """
        print(f"  >> 调试: typed_views.keys()={list(typed_views.keys())}, len={len(typed_views)}")
        
        # ✅ 特殊处理：如果只有1个"未知"类型的视图，根据尺寸判断其类型
        if len(typed_views) == 1 and '未知' in typed_views:
            unknown_view = typed_views['未知'][0]
            w_view = unknown_view['width']
            h_view = unknown_view['height']
            
            # 判断视图类型（容差2mm）
            tolerance = 2.0
            if abs(w_view - l) < tolerance and abs(h_view - w) < tolerance:
                view_type = '主视图'  # L×W
            elif abs(w_view - w) < tolerance and abs(h_view - l) < tolerance:
                view_type = '主视图'  # W×L（旋转）
            elif abs(w_view - l) < tolerance and abs(h_view - t) < tolerance:
                view_type = '俯视图'  # L×T
            elif abs(w_view - t) < tolerance and abs(h_view - l) < tolerance:
                view_type = '俯视图'  # T×L（旋转）
            elif abs(w_view - t) < tolerance and abs(h_view - w) < tolerance:
                view_type = '侧视图'  # T×W
            elif abs(w_view - w) < tolerance and abs(h_view - t) < tolerance:
                view_type = '侧视图'  # W×T（旋转）
            else:
                view_type = '未知'
            
            print(f"  >> 🔍 单视图尺寸判断: {w_view:.1f}x{h_view:.1f} → {view_type}")
            
            # 更新视图类型并重建typed_views
            if view_type != '未知':
                unknown_view['view_type'] = view_type
                typed_views = {view_type: [unknown_view]}
        
        complete_views = []
        
        # 收集已有视图（排除"未知"类型）
        for view_type, view_list in typed_views.items():
            if view_list and view_type != '未知':
                view = view_list[0]  # 取第一个（去重）
                complete_views.append({
                    'view_type': view_type,
                    'bbox': view['bbox'],
                    'center': view['center'],
                    'width': view['width'],
                    'height': view['height']
                })
        
        # 检查缺失的视图类型
        all_types = {'主视图', '俯视图', '侧视图'}
        existing_types = {v['view_type'] for v in complete_views}
        missing_types = all_types - existing_types
        
        if not missing_types:
            print(f"  >> ✅ 三视图完整，无需推断")
            return complete_views
        
        print(f"  >> 🔧 缺失视图: {missing_types}，开始推断...")
        
        # 根据已有视图推断缺失视图的位置
        for missing_type in missing_types:
            inferred_view = self._infer_single_view(missing_type, typed_views, l, w, t)
            if inferred_view:
                complete_views.append(inferred_view)
                print(f"     ✅ 推断{missing_type}: 位置=({inferred_view['center'][0]:.1f}, {inferred_view['center'][1]:.1f}), 尺寸={inferred_view['width']:.1f}x{inferred_view['height']:.1f}")
        
        return complete_views
    
    def _infer_single_view(self, view_type: str, existing_views: Dict[str, List[Dict]], l: float, w: float, t: float) -> Optional[Dict]:
        """
        推断单个缺失视图的位置和尺寸
        
        根据标准第一视角布局和投影关系推断
        """
        # 确定缺失视图的尺寸
        if view_type == '主视图':
            width, height = l, w
        elif view_type == '俯视图':
            width, height = l, t
        elif view_type == '侧视图':
            width, height = t, w
        else:
            return None
        
        # 根据已有视图推断位置
        spacing = 50.0  # 视图间距
        
        if view_type == '主视图':
            # 主视图在左上角
            if '俯视图' in existing_views:
                # 在俯视图正上方，L对齐
                ref_view = existing_views['俯视图'][0]
                ref_bbox = ref_view['bbox']
                new_x = ref_bbox[0]  # X对齐
                new_y = ref_bbox[3] + spacing  # 在上方
                new_bbox = (new_x, new_y, new_x + width, new_y + height)
            elif '侧视图' in existing_views:
                # 在侧视图左侧，W对齐
                ref_view = existing_views['侧视图'][0]
                ref_bbox = ref_view['bbox']
                new_x = ref_bbox[0] - width - spacing  # 在左侧
                new_y = ref_bbox[1]  # Y对齐
                new_bbox = (new_x, new_y, new_x + width, new_y + height)
            else:
                return None
        
        elif view_type == '俯视图':
            # 俯视图在左下角
            if '主视图' in existing_views:
                # 在主视图正下方，L对齐
                ref_view = existing_views['主视图'][0]
                ref_bbox = ref_view['bbox']
                new_x = ref_bbox[0]  # X对齐
                new_y = ref_bbox[1] - height - spacing  # 在下方
                new_bbox = (new_x, new_y, new_x + width, new_y + height)
            elif '侧视图' in existing_views:
                # 在侧视图左下方
                ref_view = existing_views['侧视图'][0]
                ref_bbox = ref_view['bbox']
                new_x = ref_bbox[0] - width - spacing  # 在左侧
                new_y = ref_bbox[1] - height - spacing  # 在下方
                new_bbox = (new_x, new_y, new_x + width, new_y + height)
            else:
                return None
        
        elif view_type == '侧视图':
            # 侧视图在右上角
            if '主视图' in existing_views:
                # 在主视图右侧，W对齐
                ref_view = existing_views['主视图'][0]
                ref_bbox = ref_view['bbox']
                new_x = ref_bbox[2] + spacing  # 在右侧
                new_y = ref_bbox[1]  # Y对齐
                new_bbox = (new_x, new_y, new_x + width, new_y + height)
            elif '俯视图' in existing_views:
                # 在俯视图右上方
                ref_view = existing_views['俯视图'][0]
                ref_bbox = ref_view['bbox']
                new_x = ref_bbox[2] + spacing  # 在右侧
                new_y = ref_bbox[3] + spacing  # 在上方
                new_bbox = (new_x, new_y, new_x + width, new_y + height)
            else:
                return None
        else:
            return None
        
        # 计算中心点
        center_x = (new_bbox[0] + new_bbox[2]) / 2
        center_y = (new_bbox[1] + new_bbox[3]) / 2
        
        return {
            'view_type': view_type,
            'bbox': new_bbox,
            'center': (center_x, center_y),
            'width': width,
            'height': height,
            'inferred': True  # 标记为推断的视图
        }
    
    def _assign_view_types_by_position(self, views: List[Dict]) -> List[Dict]:
        """
        根据位置判断视图类型（标准第一视角布局）
        
        标准布局：
        - 主视图：X小，Y大（左上角）
        - 侧视图：X大，Y大（右上角）
        - 俯视图：X小，Y小（左下角）
        
        返回：带有view_type字段的视图列表
        """
        if not views:
            return views
        
        # ✅ 特殊情况：只有1个视图时，无法通过位置判断，暂时标记为"未知"
        # 后续会根据尺寸特征（L×W、L×T、T×W）来判断
        if len(views) == 1:
            views[0]['view_type'] = '未知'
            print(f"  >> 只有1个视图，暂时标记为'未知'，后续根据尺寸判断")
            return views
        
        # 计算X和Y的范围
        x_coords = [v['center'][0] for v in views]
        y_coords = [v['center'][1] for v in views]
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        x_threshold = (x_min + x_max) / 2
        y_threshold = (y_min + y_max) / 2
        
        print(f"  >> 位置分析: X范围=[{x_min:.1f}, {x_max:.1f}], Y范围=[{y_min:.1f}, {y_max:.1f}]")
        print(f"  >> 阈值: X={x_threshold:.1f}, Y={y_threshold:.1f}")
        
        for view in views:
            x, y = view['center']
            
            # 判断位置区域
            is_left = x < x_threshold
            is_right = x >= x_threshold
            is_top = y >= y_threshold
            is_bottom = y < y_threshold
            
            # 根据位置判断视图类型
            if is_left and is_top:
                view['view_type'] = '主视图'
            elif is_right and is_top:
                view['view_type'] = '侧视图'
            elif is_left and is_bottom:
                view['view_type'] = '俯视图'
            else:
                view['view_type'] = '未知'
            
            print(f"     视图({x:.1f}, {y:.1f}): {'左' if is_left else '右'}{'上' if is_top else '下'} → {view['view_type']}")
        
        return views
    
    def _determine_lwt_from_view_types(self, views: List[Dict], unique_dims: List[float]) -> Tuple[float, float, float]:
        """
        根据视图类型和尺寸确定L、W、T（完全基于视图特征，无回退逻辑）
        
        视图类型与尺寸的对应关系：
        - 主视图 (L×W)
        - 俯视图 (L×T)
        - 侧视图 (T×W)
        
        策略：
        1. 收集各视图类型的尺寸
        2. 根据共享关系推断L、W、T
        3. 如果识别不出第三个视图，使用两视图推断逻辑
        """
        # 收集各视图类型的尺寸
        view_dims = {}
        for view in views:
            view_type = view.get('view_type', '未知')
            if view_type != '未知':
                # 只保留第一个（去重）
                if view_type not in view_dims:
                    view_dims[view_type] = sorted([view['width'], view['height']], reverse=True)
        
        print(f"  >> 视图类型与尺寸:")
        for vtype, dims in view_dims.items():
            print(f"     {vtype}: {dims[0]:.1f}x{dims[1]:.1f}")
        
        # ✅ 策略1：俯视图(L×T) + 侧视图(T×W) → 共享T
        if '俯视图' in view_dims and '侧视图' in view_dims:
            top_dims = set(view_dims['俯视图'])
            side_dims = set(view_dims['侧视图'])
            
            # T是共享尺寸
            tolerance = 2.0
            shared = []
            for d1 in top_dims:
                for d2 in side_dims:
                    if abs(d1 - d2) < tolerance:
                        shared.append((d1 + d2) / 2)
            
            if shared:
                t = shared[0]
                l = max(top_dims - {min(top_dims, key=lambda x: abs(x - t))}) if len(top_dims) > 1 else max(top_dims)
                w = max(side_dims - {min(side_dims, key=lambda x: abs(x - t))}) if len(side_dims) > 1 else max(side_dims)
                print(f"     推断方式: 俯视图+侧视图 → T={t:.1f}(共享), L={l:.1f}(俯独有), W={w:.1f}(侧独有)")
                return (l, w, t)
        
        # ✅ 策略2：主视图(L×W) + 俯视图(L×T) → 共享L
        if '主视图' in view_dims and '俯视图' in view_dims:
            main_dims = set(view_dims['主视图'])
            top_dims = set(view_dims['俯视图'])
            
            # L是共享尺寸
            tolerance = 2.0
            shared = []
            for d1 in main_dims:
                for d2 in top_dims:
                    if abs(d1 - d2) < tolerance:
                        shared.append((d1 + d2) / 2)
            
            if shared:
                l = shared[0]
                w = max(main_dims - {min(main_dims, key=lambda x: abs(x - l))}) if len(main_dims) > 1 else max(main_dims)
                t = max(top_dims - {min(top_dims, key=lambda x: abs(x - l))}) if len(top_dims) > 1 else max(top_dims)
                print(f"     推断方式: 主视图+俯视图 → L={l:.1f}(共享), W={w:.1f}(主独有), T={t:.1f}(俯独有)")
                return (l, w, t)
        
        # ✅ 策略3：主视图(L×W) + 侧视图(T×W) → 共享W
        if '主视图' in view_dims and '侧视图' in view_dims:
            main_dims = set(view_dims['主视图'])
            side_dims = set(view_dims['侧视图'])
            
            # W是共享尺寸
            tolerance = 2.0
            shared = []
            for d1 in main_dims:
                for d2 in side_dims:
                    if abs(d1 - d2) < tolerance:
                        shared.append((d1 + d2) / 2)
            
            if shared:
                w = shared[0]
                l = max(main_dims - {min(main_dims, key=lambda x: abs(x - w))}) if len(main_dims) > 1 else max(main_dims)
                t = max(side_dims - {min(side_dims, key=lambda x: abs(x - w))}) if len(side_dims) > 1 else max(side_dims)
                print(f"     推断方式: 主视图+侧视图 → W={w:.1f}(共享), L={l:.1f}(主独有), T={t:.1f}(侧独有)")
                return (l, w, t)
        
        # ✅ 策略4：只有一个视图类型，无法推断（返回None让上层处理）
        print(f"     ⚠️ 无法从视图类型推断L×W×T（视图类型不足）")
        return None
    
    def _calculate_view_center(self, views: List[Dict], lwt: Dict[str, float]) -> tuple:
        """
        计算匹配L×W×T的视图的几何中心
        """
        l, w, t = lwt['L'], lwt['W'], lwt['T']
        tolerance = 30.0
        
        matching_views = []
        for view in views:
            vw = view['width']
            vh = view['height']
            
            # 检查是否匹配主视图 (L x W)
            if (abs(vw - l) < tolerance and abs(vh - w) < tolerance) or \
               (abs(vw - w) < tolerance and abs(vh - l) < tolerance):
                matching_views.append(view)
            # 检查是否匹配侧视图 (T x W)
            elif (abs(vw - t) < tolerance and abs(vh - w) < tolerance) or \
                 (abs(vw - w) < tolerance and abs(vh - t) < tolerance):
                matching_views.append(view)
            # 检查是否匹配正视图 (L x T)
            elif (abs(vw - l) < tolerance and abs(vh - t) < tolerance) or \
                 (abs(vw - t) < tolerance and abs(vh - l) < tolerance):
                matching_views.append(view)
        
        if matching_views:
            # 计算匹配视图的几何中心
            avg_x = sum(v['center'][0] for v in matching_views) / len(matching_views)
            avg_y = sum(v['center'][1] for v in matching_views) / len(matching_views)
            return (avg_x, avg_y)
        else:
            # 如果没有匹配的视图，使用最近的视图中心
            return views[0]['center'] if views else (0, 0)
    
    def _find_views_and_extract_lwt(self, text_position: tuple, subgraph_id: str) -> Optional[Dict]:
            """
            改进的思路：先找到三视图，然后从三视图中提取L×W×T
            ✅ 完全按照几何方向提取L×W×T，不使用数值大小排序
            
            优先级：
            1. 从CAD标注提取（使用几何方向）
            2. 从视图几何形状推断（使用几何方向）
            
            改进：支持多种视图类型识别
            1. 闭合LWPOLYLINE（原有）
            2. LINE组成的矩形（新增）
            3. 按图层分组的视图（新增）
            
            返回: {
                'lwt': {'L': float, 'W': float, 'T': float},
                'view_center': (x, y),
                'views': [视图信息列表]
            }
            """
            try:
                x, y = text_position
                search_radius = 10000  # 搜索半径10000mm
                
                # ✅ 优先级1：尝试从CAD标注提取L×W×T（使用几何方向）
                cad_dimensions = TripleConditionConfig.extract_dimensions_from_cad_simple(
                    self.msp, text_position, subgraph_id
                )
                if cad_dimensions:
                    print(f"  >> ✅ 从CAD标注提取L×W×T: {cad_dimensions}")
                    # 查找视图中心
                    candidate_views = self._collect_all_views(text_position, search_radius)
                    if candidate_views:
                        view_center = self._calculate_view_center(candidate_views, cad_dimensions)
                        return {
                            'lwt': cad_dimensions,
                            'view_center': view_center,
                            'views': candidate_views[:3],
                            'extraction_method': 'cad_annotation'
                        }
                    else:
                        # 没有视图，使用文本位置
                        return {
                            'lwt': cad_dimensions,
                            'view_center': text_position,
                            'views': [],
                            'extraction_method': 'cad_annotation'
                        }
                
                # ✅ 优先级1.5：尝试从TEXT实体提取L×W×T格式（如"550.0L*530.0W*30.00T"）
                text_dimensions = self._extract_lwt_from_text(text_position, search_radius)
                if text_dimensions:
                    print(f"  >> ✅ 从TEXT实体提取L×W×T: {text_dimensions}")
                    # 查找视图
                    candidate_views = self._collect_all_views(text_position, search_radius)
                    
                    l, w, t = text_dimensions['L'], text_dimensions['W'], text_dimensions['T']
                    
                    if candidate_views:
                        # ✅ 方法1：通过尺寸识别附近的视图
                        identified_views = self._identify_views_by_dimensions_and_position(candidate_views, l, w, t)
                        
                        # ✅ 方法2：如果识别不完整，扩大搜索范围
                        if len(identified_views) < 3:
                            print(f"  >> 🔧 只识别到{len(identified_views)}个视图，扩大搜索范围...")
                            identified_views = self._find_missing_views_by_expanding_search(
                                text_position, identified_views, l, w, t
                            )
                        
                        if identified_views:
                            # 转换为标准格式
                            complete_views = []
                            for view_type, view_data in identified_views.items():
                                complete_views.append({
                                    'view_type': view_type,
                                    'bbox': view_data['bbox'],
                                    'center': view_data['center'],
                                    'width': view_data['width'],
                                    'height': view_data['height']
                                })
                            
                            # ✅ 方法3：如果还是不完整，才使用推断
                            if len(identified_views) < 3:
                                print(f"  >> ⚠️ 扩展搜索后仍只有{len(identified_views)}个视图，使用推断补充...")
                                typed_views_for_infer = {}
                                for view_type, view_data in identified_views.items():
                                    typed_views_for_infer[view_type] = [view_data]
                                complete_views = self._infer_missing_views(typed_views_for_infer, l, w, t)
                            else:
                                print(f"  >> ✅ 成功识别完整的三视图")
                            
                            view_center = self._calculate_view_center(complete_views, text_dimensions)
                            
                            return {
                                'lwt': text_dimensions,
                                'view_center': view_center,
                                'views': complete_views,
                                'extraction_method': 'text_annotation_with_expanded_search'
                            }
                        else:
                            # 没有识别到任何视图，使用旧方法（位置判断+推断）
                            print(f"  >> ⚠️ 无法通过尺寸识别视图，使用位置判断方法...")
                            views_with_type = self._assign_view_types_by_position(candidate_views)
                            
                            typed_views = {}
                            for view in views_with_type:
                                view_type = view.get('view_type', '未知')
                                if view_type not in typed_views:
                                    typed_views[view_type] = []
                                typed_views[view_type].append(view)
                            
                            complete_views = self._infer_missing_views(typed_views, l, w, t)
                            view_center = self._calculate_view_center(complete_views, text_dimensions)
                            
                            return {
                                'lwt': text_dimensions,
                                'view_center': view_center,
                                'views': complete_views,
                                'extraction_method': 'text_annotation'
                            }
                    else:
                        # 没有视图，使用文本位置
                        return {
                            'lwt': text_dimensions,
                            'view_center': text_position,
                            'views': [],
                            'extraction_method': 'text_annotation'
                        }
                
                # ✅ 优先级2：从视图几何形状推断L×W×T（使用几何方向）
                candidate_views = self._collect_all_views(text_position, search_radius)
                
                if not candidate_views:
                    print(f"  >> 未找到附近的视图区域")
                    return None
                
                print(f"  >> 找到 {len(candidate_views)} 个候选视图区域（LWPOLYLINE + LINE + 图层）")
                
                # 从视图几何形状推断L×W×T（按几何方向）
                result = self._infer_lwt_from_views_by_geometry(candidate_views)
                
                if not result:
                    print(f"  >> 无法从视图推断L×W×T")
                    return None
                
                # 提取L×W×T和完整的视图信息
                lwt_dict = {'L': result['L'], 'W': result['W'], 'T': result['T']}
                complete_views = result.get('views', candidate_views[:3])
                
                # 计算视图中心
                view_center = self._calculate_view_center(complete_views, lwt_dict)
                
                print(f"  >> 从视图几何推断L×W×T: {lwt_dict}")
                print(f"  >> 视图中心: ({view_center[0]:.1f}, {view_center[1]:.1f})")
                
                return {
                    'lwt': lwt_dict,
                    'view_center': view_center,
                    'views': complete_views,  # ✅ 使用完整的三视图信息
                    'extraction_method': 'from_views_geometry'
                }
                    
            except Exception as e:
                print(f"⚠️ 从视图提取L×W×T失败: {e}")
                import traceback
                traceback.print_exc()
                return None
    
    def _find_rectangles_from_lines(self, center_position: tuple, search_radius: float) -> List[Dict]:
        """
        从LINE实体中查找矩形视图
        用于识别由LINE组成的视图（而非闭合LWPOLYLINE）
        """
        rectangles = []

        try:
            # 按图层分组LINE
            lines_by_layer = {}
            for entity in self.msp.query('LINE'):
                # 检查距离
                line_center_x = (entity.dxf.start[0] + entity.dxf.end[0]) / 2
                line_center_y = (entity.dxf.start[1] + entity.dxf.end[1]) / 2
                distance = ((line_center_x - center_position[0])**2 +
                           (line_center_y - center_position[1])**2)**0.5

                if distance <= search_radius:
                    layer = entity.dxf.layer
                    if layer not in lines_by_layer:
                        lines_by_layer[layer] = []
                    lines_by_layer[layer].append(entity)

            # 对每个图层，尝试识别矩形
            for layer, lines in lines_by_layer.items():
                if len(lines) >= 4:  # 至少4条线
                    # 分类为水平线和垂直线
                    horizontal = []
                    vertical = []

                    for line in lines:
                        dx = abs(line.dxf.end[0] - line.dxf.start[0])
                        dy = abs(line.dxf.end[1] - line.dxf.start[1])

                        if dx > dy * 10:  # 水平线
                            horizontal.append(line)
                        elif dy > dx * 10:  # 垂直线
                            vertical.append(line)

                    # 如果有至少2条水平线和2条垂直线
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

                        # 过滤不合理的尺寸（改进：更严格的过滤，避免识别整个图层）
                        # ✅ 修复：不应该把整个图层的LINE当成一个矩形
                        if 10 < width < 1000 and 10 < height < 1000 and 100 < area < 200000:
                            center_x = (bbox[0] + bbox[2]) / 2
                            center_y = (bbox[1] + bbox[3]) / 2
                            distance = ((center_x - center_position[0])**2 +
                                       (center_y - center_position[1])**2)**0.5

                            rectangles.append({
                                'center': (center_x, center_y),
                                'bbox': bbox,
                                'distance': distance,
                                'width': width,
                                'height': height,
                                'area': area,
                                'type': 'line_rectangle',
                                'layer': layer
                            })
                            print(f"  >> 从LINE识别矩形: {width:.1f}x{height:.1f}, 图层={layer}")

        except Exception as e:
            print(f"⚠️ 从LINE识别矩形失败: {e}")

        return rectangles
    
    def _find_paired_line_rectangles(self, center_position: tuple, search_radius: float, 
                                     target_l: float, target_w: float, target_t: float) -> List[Dict]:
        """
        从成对的LINE中识别矩形视图
        用于识别由两条平行线组成的矩形（如侧视图、俯视图）
        
        Args:
            center_position: 搜索中心位置
            search_radius: 搜索半径
            target_l, target_w, target_t: 目标L×W×T尺寸
        
        Returns:
            识别出的矩形列表
        """
        rectangles = []
        tolerance = 10
        
        try:
            # 收集所有LINE
            all_lines = []
            for entity in self.msp.query('LINE'):
                line_center_x = (entity.dxf.start[0] + entity.dxf.end[0]) / 2
                line_center_y = (entity.dxf.start[1] + entity.dxf.end[1]) / 2
                distance = ((line_center_x - center_position[0])**2 + 
                           (line_center_y - center_position[1])**2)**0.5
                
                if distance <= search_radius:
                    dx = abs(entity.dxf.end[0] - entity.dxf.start[0])
                    dy = abs(entity.dxf.end[1] - entity.dxf.start[1])
                    length = (dx**2 + dy**2)**0.5
                    
                    # 判断方向
                    if dx > dy * 10:
                        direction = 'H'
                    elif dy > dx * 10:
                        direction = 'V'
                    else:
                        direction = 'D'
                    
                    all_lines.append({
                        'entity': entity,
                        'start': (entity.dxf.start[0], entity.dxf.start[1]),
                        'end': (entity.dxf.end[0], entity.dxf.end[1]),
                        'center': (line_center_x, line_center_y),
                        'length': length,
                        'direction': direction,
                        'layer': entity.dxf.layer
                    })
            
            # 策略1：寻找成对的垂直线（距离≈T，长度≈W）构成侧视图
            long_v_lines = [line for line in all_lines 
                           if line['direction'] == 'V' and abs(line['length'] - target_w) < tolerance]
            
            for i in range(len(long_v_lines)):
                for j in range(i + 1, len(long_v_lines)):
                    line1 = long_v_lines[i]
                    line2 = long_v_lines[j]
                    
                    x_distance = abs(line2['center'][0] - line1['center'][0])
                    y_min1 = min(line1['start'][1], line1['end'][1])
                    y_max1 = max(line1['start'][1], line1['end'][1])
                    y_min2 = min(line2['start'][1], line2['end'][1])
                    y_max2 = max(line2['start'][1], line2['end'][1])
                    y_overlap = min(y_max1, y_max2) - max(y_min1, y_min2)
                    
                    # 检查X距离是否≈T，且Y坐标有重叠
                    if abs(x_distance - target_t) < tolerance and y_overlap > target_w * 0.8:
                        center_x = (line1['center'][0] + line2['center'][0]) / 2
                        center_y = (line1['center'][1] + line2['center'][1]) / 2
                        distance_to_center = ((center_x - center_position[0])**2 + 
                                            (center_y - center_position[1])**2)**0.5
                        
                        width = x_distance
                        height = (line1['length'] + line2['length']) / 2
                        
                        # 正确计算bbox
                        x_min = min(line1['center'][0], line2['center'][0])
                        x_max = max(line1['center'][0], line2['center'][0])
                        y_min = min(y_min1, y_min2)
                        y_max = max(y_max1, y_max2)
                        
                        rectangles.append({
                            'center': (center_x, center_y),
                            'bbox': (x_min, y_min, x_max, y_max),
                            'distance': distance_to_center,
                            'width': width,
                            'height': height,
                            'area': width * height,
                            'type': 'paired_v_lines',
                            'layer': line1['layer']
                        })
                        print(f"  >> 从成对垂直LINE识别侧视图: {width:.1f}x{height:.1f}, 中心=({center_x:.1f}, {center_y:.1f})")
            
            # 策略2：寻找成对的水平线（距离≈T，长度≈L）构成俯视图
            long_h_lines = [line for line in all_lines 
                           if line['direction'] == 'H' and abs(line['length'] - target_l) < tolerance]
            
            # ✅ 新增：如果没有找到完整的长线，尝试拼接分割的短线
            if len(long_h_lines) == 0:
                print(f"  >> 🔧 未找到长度≈{target_l}的水平线，尝试拼接分割线段...")
                long_h_lines = self._merge_collinear_lines(all_lines, 'H', target_l, tolerance)
                if long_h_lines:
                    print(f"  >> ✅ 拼接成功，找到 {len(long_h_lines)} 条拼接后的水平线")
                    for idx, line in enumerate(long_h_lines, 1):
                        print(f"     拼接线{idx}: 长度={line['length']:.1f}, Y={line['center'][1]:.1f}, X范围=[{line['start'][0]:.1f}, {line['end'][0]:.1f}]")
                else:
                    print(f"  >> ❌ 拼接失败，未找到符合条件的线段")
            
            for i in range(len(long_h_lines)):
                for j in range(i + 1, len(long_h_lines)):
                    line1 = long_h_lines[i]
                    line2 = long_h_lines[j]
                    
                    y_distance = abs(line2['center'][1] - line1['center'][1])
                    x_min1 = min(line1['start'][0], line1['end'][0])
                    x_max1 = max(line1['start'][0], line1['end'][0])
                    x_min2 = min(line2['start'][0], line2['end'][0])
                    x_max2 = max(line2['start'][0], line2['end'][0])
                    x_overlap = min(x_max1, x_max2) - max(x_min1, x_min2)
                    
                    # 检查Y距离是否≈T，且X坐标有重叠
                    if abs(y_distance - target_t) < tolerance and x_overlap > target_l * 0.8:
                        center_x = (line1['center'][0] + line2['center'][0]) / 2
                        center_y = (line1['center'][1] + line2['center'][1]) / 2
                        distance_to_center = ((center_x - center_position[0])**2 + 
                                            (center_y - center_position[1])**2)**0.5
                        
                        width = (line1['length'] + line2['length']) / 2
                        height = y_distance
                        
                        # 正确计算bbox
                        x_min = min(x_min1, x_min2)
                        x_max = max(x_max1, x_max2)
                        y_min = min(line1['center'][1], line2['center'][1])
                        y_max = max(line1['center'][1], line2['center'][1])
                        
                        rectangles.append({
                            'center': (center_x, center_y),
                            'bbox': (x_min, y_min, x_max, y_max),
                            'distance': distance_to_center,
                            'width': width,
                            'height': height,
                            'area': width * height,
                            'type': 'paired_h_lines',
                            'layer': line1['layer']
                        })
                        print(f"  >> 从成对水平LINE识别俯视图: {width:.1f}x{height:.1f}, 中心=({center_x:.1f}, {center_y:.1f})")
        
        except Exception as e:
            print(f"⚠️ 从成对LINE识别矩形失败: {e}")
        
        return rectangles
    
    def _merge_collinear_lines(self, all_lines: List[Dict], direction: str, target_length: float, tolerance: float) -> List[Dict]:
        """
        拼接共线的线段，用于识别被分割的视图边界
        
        Args:
            all_lines: 所有线段
            direction: 'H'（水平）或 'V'（垂直）
            target_length: 目标长度
            tolerance: 容差
        
        Returns:
            拼接后的线段列表
        """
        # 筛选指定方向的线段
        lines = [line for line in all_lines if line['direction'] == direction]
        
        if not lines:
            return []
        
        # 按位置分组（水平线按Y坐标，垂直线按X坐标）
        groups = {}
        position_tolerance = 5.0  # ✅ 放宽到5mm容差认为是同一条线
        
        for line in lines:
            if direction == 'H':
                # 水平线按Y坐标分组
                key_pos = line['center'][1]
            else:
                # 垂直线按X坐标分组
                key_pos = line['center'][0]
            
            # 找到最近的组
            found_group = False
            for group_key in list(groups.keys()):
                if abs(group_key - key_pos) < position_tolerance:
                    groups[group_key].append(line)
                    found_group = True
                    break
            
            if not found_group:
                groups[key_pos] = [line]
        
        # 对每组线段进行拼接
        merged_lines = []
        all_merged_attempts = []  # 记录所有拼接尝试
        
        for group_key, group_lines in groups.items():
            if len(group_lines) < 2:
                # 单条线，直接检查长度
                if abs(group_lines[0]['length'] - target_length) < tolerance:
                    merged_lines.append(group_lines[0])
                continue
            
            # 按位置排序（水平线按X，垂直线按Y）
            if direction == 'H':
                group_lines.sort(key=lambda l: l['center'][0])
            else:
                group_lines.sort(key=lambda l: l['center'][1])
            
            # 尝试拼接相邻的线段
            merge_tolerance = 50.0  # ✅ 进一步放宽到50mm间隙内认为可以拼接
            
            i = 0
            while i < len(group_lines):
                current_line = group_lines[i]
                
                if direction == 'H':
                    # 水平线：从左到右拼接
                    x_min = min(current_line['start'][0], current_line['end'][0])
                    x_max = max(current_line['start'][0], current_line['end'][0])
                    y_avg = current_line['center'][1]
                    
                    # 查找可以拼接的后续线段
                    j = i + 1
                    while j < len(group_lines):
                        next_line = group_lines[j]
                        next_x_min = min(next_line['start'][0], next_line['end'][0])
                        next_x_max = max(next_line['start'][0], next_line['end'][0])
                        
                        # 检查是否相邻或重叠
                        gap = next_x_min - x_max
                        if gap <= merge_tolerance:
                            # 可以拼接
                            x_max = max(x_max, next_x_max)
                            j += 1
                        else:
                            break
                    
                    # 创建拼接后的线段
                    merged_length = x_max - x_min
                    all_merged_attempts.append({
                        'length': merged_length,
                        'y': y_avg,
                        'x_range': (x_min, x_max),
                        'matched': abs(merged_length - target_length) < tolerance * 2.0
                    })
                    # ✅ 放宽长度匹配容差到tolerance * 2.0
                    if abs(merged_length - target_length) < tolerance * 2.0:
                        merged_lines.append({
                            'start': (x_min, y_avg),
                            'end': (x_max, y_avg),
                            'center': ((x_min + x_max) / 2, y_avg),
                            'length': merged_length,
                            'direction': 'H',
                            'layer': current_line['layer']
                        })
                    
                    i = j
                
                else:
                    # 垂直线：从下到上拼接
                    y_min = min(current_line['start'][1], current_line['end'][1])
                    y_max = max(current_line['start'][1], current_line['end'][1])
                    x_avg = current_line['center'][0]
                    
                    # 查找可以拼接的后续线段
                    j = i + 1
                    while j < len(group_lines):
                        next_line = group_lines[j]
                        next_y_min = min(next_line['start'][1], next_line['end'][1])
                        next_y_max = max(next_line['start'][1], next_line['end'][1])
                        
                        # 检查是否相邻或重叠
                        gap = next_y_min - y_max
                        if gap <= merge_tolerance:
                            # 可以拼接
                            y_max = max(y_max, next_y_max)
                            j += 1
                        else:
                            break
                    
                    # 创建拼接后的线段
                    merged_length = y_max - y_min
                    all_merged_attempts.append({
                        'length': merged_length,
                        'x': x_avg,
                        'y_range': (y_min, y_max),
                        'matched': abs(merged_length - target_length) < tolerance * 2.0
                    })
                    # ✅ 放宽长度匹配容差到tolerance * 2.0
                    if abs(merged_length - target_length) < tolerance * 2.0:
                        merged_lines.append({
                            'start': (x_avg, y_min),
                            'end': (x_avg, y_max),
                            'center': (x_avg, (y_min + y_max) / 2),
                            'length': merged_length,
                            'direction': 'V',
                            'layer': current_line['layer']
                        })
                    
                    i = j
        
        # 输出调试信息
        if all_merged_attempts:
            print(f"  >> 📊 拼接统计（方向={direction}，目标长度={target_length:.1f}）:")
            print(f"     总共尝试拼接: {len(all_merged_attempts)} 条线段")
            matched_count = sum(1 for a in all_merged_attempts if a['matched'])
            print(f"     符合长度要求: {matched_count} 条")
            if direction == 'H':
                for idx, attempt in enumerate(all_merged_attempts[:10], 1):
                    status = "✅" if attempt['matched'] else "❌"
                    print(f"     {status} 线段{idx}: 长度={attempt['length']:.1f}, Y={attempt['y']:.1f}, X范围=[{attempt['x_range'][0]:.1f}, {attempt['x_range'][1]:.1f}]")
            else:
                for idx, attempt in enumerate(all_merged_attempts[:10], 1):
                    status = "✅" if attempt['matched'] else "❌"
                    print(f"     {status} 线段{idx}: 长度={attempt['length']:.1f}, X={attempt['x']:.1f}, Y范围=[{attempt['y_range'][0]:.1f}, {attempt['y_range'][1]:.1f}]")
        
        return merged_lines

    def _find_views_by_layer(self, center_position: tuple, search_radius: float) -> List[Dict]:
        """
        按图层分组，查找可能的视图区域
        用于识别包含多种实体类型的复杂视图
        """
        views = []

        try:
            # 重点图层（通常包含视图）
            target_layers = ['DIE', 'PH2', 'PS', 'LP', 'UP', 'dim', '0']

            for layer_name in target_layers:
                # 查找该图层的所有实体
                entities = list(self.msp.query(f'*[layer=="{layer_name}"]'))

                if entities:
                    # 计算边界框
                    xs = []
                    ys = []

                    for entity in entities:
                        try:
                            if entity.dxftype() == 'LINE':
                                xs.extend([entity.dxf.start[0], entity.dxf.end[0]])
                                ys.extend([entity.dxf.start[1], entity.dxf.end[1]])
                            elif entity.dxftype() == 'LWPOLYLINE':
                                points = list(entity.get_points(format='xy'))
                                xs.extend([p[0] for p in points])
                                ys.extend([p[1] for p in points])
                            elif entity.dxftype() == 'CIRCLE':
                                cx, cy = entity.dxf.center[0], entity.dxf.center[1]
                                r = entity.dxf.radius
                                xs.extend([cx - r, cx + r])
                                ys.extend([cy - r, cy + r])
                            elif entity.dxftype() == 'ARC':
                                cx, cy = entity.dxf.center[0], entity.dxf.center[1]
                                r = entity.dxf.radius
                                xs.extend([cx - r, cx + r])
                                ys.extend([cy - r, cy + r])
                        except Exception:
                            continue

                    if xs and ys:
                        bbox = (min(xs), min(ys), max(xs), max(ys))
                        width = bbox[2] - bbox[0]
                        height = bbox[3] - bbox[1]
                        area = width * height
                        center_x = (bbox[0] + bbox[2]) / 2
                        center_y = (bbox[1] + bbox[3]) / 2
                        distance = ((center_x - center_position[0])**2 +
                                   (center_y - center_position[1])**2)**0.5

                        # 过滤不合理的尺寸（改进：更严格的过滤，避免识别整个图层）
                        # ✅ 修复：不应该把整个图层当成视图，需要根据L×W×T过滤
                        # 跳过明显过大的边界框（可能是整个图层）
                        if distance <= search_radius and 10 < width < 1000 and 10 < height < 1000 and 100 < area < 200000:
                            views.append({
                                'center': (center_x, center_y),
                                'bbox': bbox,
                                'distance': distance,
                                'width': width,
                                'height': height,
                                'area': area,
                                'type': 'layer_group',
                                'layer': layer_name
                            })
                            print(f"  >> 从图层识别视图: {width:.1f}x{height:.1f}, 图层={layer_name}")

        except Exception as e:
            print(f"⚠️ 按图层识别视图失败: {e}")
        
        return views
    
    def _find_view_center_near_text(self, text_position: tuple, lwt_dict: Dict[str, float]) -> Optional[tuple]:
            """
            在文本位置附近查找三视图，返回视图的中心位置
            改进：扩大搜索范围，提高成功率
            """
            try:
                x, y = text_position
                search_radius = 15000  # 扩大到15000mm
                min_area = 100  # 最小面积100mm²
                
                l, w, t = lwt_dict['L'], lwt_dict['W'], lwt_dict['T']
                tolerance = 30.0  # 放宽容差到30mm
                
                # 查找附近的闭合多段线
                candidate_views = []
                for entity in self.msp.query('LWPOLYLINE POLYLINE'):
                    if entity.dxftype() == 'LWPOLYLINE' and entity.closed:
                        points = list(entity.get_points(format='xy'))
                        if points:
                            # 计算中心点
                            center_x = sum(p[0] for p in points) / len(points)
                            center_y = sum(p[1] for p in points) / len(points)
                            
                            # 计算距离
                            distance = ((center_x - x)**2 + (center_y - y)**2)**0.5
                            
                            if distance <= search_radius:
                                # 计算边界框和尺寸
                                xs = [p[0] for p in points]
                                ys = [p[1] for p in points]
                                bbox = (min(xs), min(ys), max(xs), max(ys))
                                dx = bbox[2] - bbox[0]
                                dy = bbox[3] - bbox[1]
                                area = dx * dy
                                
                                # 过滤小区域
                                if area < min_area:
                                    continue
                                
                                # 检查尺寸是否匹配
                                is_match = False
                                if (abs(dx - l) < tolerance and abs(dy - w) < tolerance) or \
                                   (abs(dx - w) < tolerance and abs(dy - l) < tolerance) or \
                                   (abs(dx - t) < tolerance and abs(dy - w) < tolerance) or \
                                   (abs(dx - w) < tolerance and abs(dy - t) < tolerance) or \
                                   (abs(dx - l) < tolerance and abs(dy - t) < tolerance) or \
                                   (abs(dx - t) < tolerance and abs(dy - l) < tolerance):
                                    is_match = True
                                
                                if is_match:
                                    candidate_views.append({
                                        'center': (center_x, center_y),
                                        'bbox': bbox,
                                        'distance': distance,
                                        'area': area
                                    })
                
                if candidate_views:
                    # 按距离排序，选择最近的视图
                    candidate_views.sort(key=lambda v: v['distance'])
                    best_view = candidate_views[0]
                    print(f"  >> 找到三视图中心: ({best_view['center'][0]:.1f}, {best_view['center'][1]:.1f}), 距离文本={best_view['distance']:.1f}mm")
                    return best_view['center']
                else:
                    print(f"  >> 未找到匹配的三视图")
                    return None
                    
            except Exception as e:
                print(f"⚠️ 查找视图中心失败: {e}")
                return None

    
    def _classify_subgraph_type(self, subgraph_id: str) -> str:
        """子图类型分类 - 使用配置化规则"""
        return TripleConditionConfig.classify_subgraph_type_advanced(subgraph_id)
    
    def _calculate_optimized_confidence(self, factors: Dict) -> float:
        """
        优化版置信度计算 - 基于多个因子
        """
        confidence = 0.7  # 基础置信度（三重条件满足）
        
        # L/W/T格式加分
        if factors.get('has_lwt_format', False):
            confidence += 0.2
        
        # 关键词数量加分
        keyword_count = factors.get('keyword_count', 0)
        confidence += min(keyword_count * 0.02, 0.1)
        
        # 子图类型加分
        subgraph_type = factors.get('subgraph_type', 'default')
        if subgraph_type == 'ps':
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _print_performance_stats(self):
        """打印性能统计信息"""
        print(f"\n📊 性能统计:")
        print(f"   总文本数: {self.stats['total_texts']}")
        print(f"   PCS文本数: {self.stats['pcs_texts']}")
        print(f"   三重条件候选项: {self.stats['triple_candidates']}")
        print(f"   处理时间: {self.stats['processing_time']:.3f}秒")
        print(f"   缓存命中: {self.stats['cache_hits']}")
        
        if self.stats['pcs_texts'] > 0:
            efficiency = self.stats['triple_candidates'] / self.stats['pcs_texts'] * 100
            print(f"   筛选效率: {efficiency:.1f}%")

def analyze_optimized_triple_condition_strategy(dxf_file_path: str):
    """
    分析优化版三重条件策略的效果
    """
    processor = OptimizedTripleConditionProcessor(dxf_file_path)
    candidates = processor.apply_triple_condition_strategy()
    
    # 统计分析
    total_count = len(candidates)
    has_lwt_count = len([c for c in candidates if c['has_lwt_format']])
    no_lwt_count = total_count - has_lwt_count
    
    print(f"\n📊 优化版三重条件策略分析结果:")
    print("-" * 50)
    print(f"符合三重条件总数:     {total_count:3d} 个")
    print(f"其中有L/W/T格式:      {has_lwt_count:3d} 个")
    print(f"其中无L/W/T格式:      {no_lwt_count:3d} 个")
    print(f"预期目标(232个):      {'✅ 接近' if abs(total_count - 232) < 50 else '❌ 差距较大'}")
    
    # 显示前5个示例
    print(f"\n📋 前5个候选项示例:")
    print("-" * 50)
    for i, candidate in enumerate(candidates[:5]):
        lwt_status = "有L/W/T" if candidate['has_lwt_format'] else "估算"
        confidence = candidate['confidence']
        print(f"{i+1}. {candidate['subgraph_id']:8s} {lwt_status:8s} 置信度:{confidence:.2f} {candidate['raw_text'][:30]}...")
    
    return candidates

if __name__ == "__main__":
    # 导入路径配置
    try:
        from path_config import get_test_file
        dxf_file = get_test_file('M250286_P2')
    except (ImportError, KeyError):
        # 如果无法导入配置，使用默认路径
        dxf_file = "M250286-P2-20260203.dxf"
        print("⚠️ 警告: 使用默认测试文件路径")
    
    if os.path.exists(dxf_file):
        analyze_optimized_triple_condition_strategy(dxf_file)
    else:
        print(f"❌ 文件不存在: {dxf_file}")
        print(f"💡 提示: 请在 path_config.py 中配置正确的测试文件路径")