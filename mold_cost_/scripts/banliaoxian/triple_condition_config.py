#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三重条件策略配置文件
"""

from typing import Dict, List, Optional

class TripleConditionConfig:
    """三重条件筛选配置"""
    
    # 默认启用状态
    DEFAULT_ENABLE = False
    
    # 子图编号模式
    SUBGRAPH_PATTERNS = [
        r'[A-Z]\d+[-_]\d+',
        r'[A-Z]\d+',
        r'\d+[-_]\d+',
        r'ps[-_]?\d+',
        r'PS[-_]?\d+',
        r'[A-Z]{2,3}[-_]?\d+',
        r'M\d+[-_]P\d+',
        r'[A-Z]\d+[A-Z]\d*',
    ]
    
    # 加工说明关键词
    PROCESSING_KEYWORDS = [
        '45#', 'CR12MOV', 'SECC', 'P20', 'SKD11',
        'HRC', 'HB', 'HV',
        '淬火', '回火', '调质',
        '镀', '氧化', '发黑',
        '精加工', '粗加工',
        '车', '铣', '钻', '磨',
        '公差', '配合', '基准',
        'Ra', 'Rz',
        '备注', '说明', '注意', '要求',
    ]
    
    # 筛选策略
    FILTER_STRATEGIES = {
        'strict': {
            'require_subgraph': True,
            'require_pcs': True,
            'require_processing': True,
            'min_keywords': 1
        },
        'medium': {
            'require_subgraph': True,
            'require_pcs': True,
            'require_processing': False,
            'min_keywords': 0
        },
        'loose': {
            'require_subgraph': False,
            'require_pcs': True,
            'require_processing': True,
            'min_keywords': 1
        }
    }
    
    DEFAULT_STRATEGY = 'strict'
    
    # CAD标注识别配置
    CAD_ANNOTATION_EXTRACTION = {
        'enable_cad_extraction': True,
        'search_radius': 200.0,
        'min_dimension_value': 0.5,
        'max_dimension_value': 5000.0,
        'exclude_small_values': True,
        'small_value_threshold': 5.0,
        'confidence_threshold': 0.6,
        'enable_distance_sorting': True,
        'max_annotations': 5,
    }
    
    # 文本重构配置
    TEXT_RECONSTRUCTION = {
        'enable_text_reconstruction': True,
        'dimension_format': '{T}T×{L}L×{W}W',
        'insert_position': 'before_pcs',
        'pcs_patterns': [
            r'\d+\s*PCS',
            r'\d+\s*pcs',
            r'\d+\s*PC',
            r'\d+\s*pc',
            r'\d+\s*个',
            r'\d+\s*件'
        ],
        'number_format_precision': 1,
    }
    
    # 默认尺寸配置
    DEFAULT_DIMENSIONS = {
        'ps': {'L': 100.0, 'W': 80.0, 'T': 10.0},
        'ph': {'L': 150.0, 'W': 120.0, 'T': 15.0},
        'die': {'L': 200.0, 'W': 150.0, 'T': 20.0},
        'default': {'L': 120.0, 'W': 90.0, 'T': 12.0},
    }
    
    @classmethod
    def classify_subgraph_type_advanced(cls, subgraph_id: str) -> str:
        """子图类型分类"""
        if not subgraph_id:
            return 'default'
        
        subgraph_upper = subgraph_id.upper()
        if 'PS' in subgraph_upper:
            return 'ps'
        elif 'PH' in subgraph_upper:
            return 'ph'
        elif 'DIE' in subgraph_upper:
            return 'die'
        else:
            return 'default'
    
    @classmethod
    def extract_dimensions_from_cad_simple(cls, msp, subgraph_position: tuple, subgraph_id: str) -> Optional[Dict[str, float]]:
        """简单CAD标注提取方法"""
        if not cls.CAD_ANNOTATION_EXTRACTION['enable_cad_extraction']:
            return None
        
        import math
        
        nearby_dimensions = []
        search_radius = cls.CAD_ANNOTATION_EXTRACTION['search_radius']
        
        try:
            for entity in msp.query('DIMENSION'):
                dim_position = None
                if hasattr(entity.dxf, 'text_midpoint'):
                    dim_position = entity.dxf.text_midpoint
                elif hasattr(entity.dxf, 'defpoint'):
                    dim_position = entity.dxf.defpoint
                else:
                    continue
                
                distance = math.sqrt(
                    (dim_position[0] - subgraph_position[0])**2 + 
                    (dim_position[1] - subgraph_position[1])**2
                )
                
                if distance <= search_radius:
                    dim_value = None
                    if hasattr(entity.dxf, 'actual_measurement') and entity.dxf.actual_measurement:
                        dim_value = entity.dxf.actual_measurement
                    elif hasattr(entity.dxf, 'text') and entity.dxf.text:
                        import re
                        numbers = re.findall(r'\d+(?:\.\d+)?', entity.dxf.text)
                        if numbers:
                            dim_value = float(numbers[0])
                    
                    if dim_value and cls._is_valid_dimension_value(dim_value):
                        direction = cls._get_dimension_direction(entity)
                        nearby_dimensions.append({
                            'value': dim_value,
                            'position': dim_position,
                            'distance': distance,
                            'direction': direction,
                            'entity': entity
                        })
        
        except Exception as e:
            print(f"警告: CAD标注提取出错: {e}")
            return None
        
        return cls._assign_lwt_by_direction(nearby_dimensions, subgraph_id)
    
    @classmethod
    def _get_dimension_direction(cls, dim_entity) -> str:
        """获取标注的方向"""
        try:
            import math
            
            if hasattr(dim_entity.dxf, 'defpoint3') and hasattr(dim_entity.dxf, 'defpoint4'):
                p3 = dim_entity.dxf.defpoint3
                p4 = dim_entity.dxf.defpoint4
                dx = abs(p4[0] - p3[0])
                dy = abs(p4[1] - p3[1])
                if dx > dy * 1.2:
                    return 'horizontal'
                elif dy > dx * 1.2:
                    return 'vertical'
            
            if hasattr(dim_entity.dxf, 'defpoint') and hasattr(dim_entity.dxf, 'defpoint2'):
                p1 = dim_entity.dxf.defpoint
                p2 = dim_entity.dxf.defpoint2
                dx = abs(p2[0] - p1[0])
                dy = abs(p2[1] - p1[1])
                if dx > dy * 1.2:
                    return 'horizontal'
                elif dy > dx * 1.2:
                    return 'vertical'
        except Exception:
            pass
        
        return 'unknown'
    
    @classmethod
    def _assign_lwt_by_direction(cls, dimensions: List[Dict], subgraph_id: str) -> Optional[Dict[str, float]]:
        """基于几何方向分配L×W×T"""
        if len(dimensions) < 2:
            return None
        
        if cls.CAD_ANNOTATION_EXTRACTION.get('enable_distance_sorting', True):
            dimensions = sorted(dimensions, key=lambda x: x['distance'])[:5]
        
        horizontal_dims = [d for d in dimensions if d['direction'] == 'horizontal']
        vertical_dims = [d for d in dimensions if d['direction'] == 'vertical']
        
        result = {}
        vertical_w_candidate = None
        
        # 垂直方向标注
        if vertical_dims:
            vertical_sorted = sorted(vertical_dims, key=lambda x: x['position'][1])
            if len(vertical_sorted) >= 2:
                result['L'] = vertical_sorted[0]['value']
                vertical_w_candidate = vertical_sorted[-1]
            elif len(vertical_sorted) == 1:
                result['L'] = vertical_sorted[0]['value']
        
        # 水平方向标注
        if horizontal_dims:
            horizontal_sorted = sorted(horizontal_dims, key=lambda x: x['position'][1], reverse=True)
            if len(horizontal_sorted) >= 2:
                result['W'] = horizontal_sorted[0]['value']
                result['T'] = horizontal_sorted[-1]['value']
            elif len(horizontal_sorted) == 1:
                result['T'] = horizontal_sorted[0]['value']
        
        # 补充W
        if 'W' not in result and vertical_w_candidate:
            result['W'] = vertical_w_candidate['value']
        
        if len(result) >= 3 and all(k in result for k in ['L', 'W', 'T']):
            return result
        
        return None
    
    @classmethod
    def _is_valid_dimension_value(cls, value: float) -> bool:
        """验证尺寸值的有效性"""
        config = cls.CAD_ANNOTATION_EXTRACTION
        if not (config['min_dimension_value'] <= value <= config['max_dimension_value']):
            return False
        if config['exclude_small_values'] and value < config['small_value_threshold']:
            return False
        return True
    
    @classmethod
    def _intelligent_dimension_inference(cls, text_content: str, subgraph_id: str) -> Dict[str, float]:
        """智能尺寸推断"""
        subgraph_type = cls.classify_subgraph_type_advanced(subgraph_id)
        base_dimensions = cls.DEFAULT_DIMENSIONS.get(subgraph_type, cls.DEFAULT_DIMENSIONS['default']).copy()
        
        import re
        numbers = re.findall(r'\d+(?:\.\d+)?', text_content)
        if numbers:
            try:
                numeric_values = [float(n) for n in numbers if 10.0 <= float(n) <= 1000.0]
                if len(numeric_values) >= 3:
                    numeric_values.sort(reverse=True)
                    return {'L': numeric_values[0], 'W': numeric_values[1], 'T': numeric_values[2]}
            except (ValueError, IndexError):
                pass
        
        return base_dimensions
    
    @classmethod
    def reconstruct_text_with_dimensions(cls, original_text: str, lwt_dict: Dict[str, float]) -> str:
        """文本重构：将L×W×T尺寸插入到原始文本中"""
        if not cls.TEXT_RECONSTRUCTION['enable_text_reconstruction']:
            return original_text
        
        if cls._already_has_dimensions(original_text):
            return original_text
        
        dimension_str = cls._format_dimension_string(lwt_dict)
        
        import re
        pcs_pattern = '|'.join(cls.TEXT_RECONSTRUCTION['pcs_patterns'])
        pcs_match = re.search(f'({pcs_pattern})', original_text, re.IGNORECASE)
        
        if pcs_match:
            return cls._insert_before_pcs(original_text, dimension_str, pcs_match)
        else:
            return f"{original_text.rstrip()} {dimension_str}"
    
    @classmethod
    def _format_dimension_string(cls, lwt_dict: Dict[str, float]) -> str:
        """格式化尺寸字符串"""
        T = lwt_dict.get('T', 0)
        L = lwt_dict.get('L', 0)
        W = lwt_dict.get('W', 0)
        precision = cls.TEXT_RECONSTRUCTION['number_format_precision']
        
        def format_number(num):
            if precision == 0 or num == int(num):
                return str(int(num))
            else:
                return f"{num:.{precision}f}"
        
        return cls.TEXT_RECONSTRUCTION['dimension_format'].format(
            T=format_number(T), L=format_number(L), W=format_number(W)
        )
    
    @classmethod
    def _insert_before_pcs(cls, text: str, dimension_str: str, pcs_match) -> str:
        """在PCS前插入尺寸"""
        pcs_start = pcs_match.start()
        before_pcs = text[:pcs_start]
        pcs_and_after = text[pcs_start:]
        
        if not before_pcs.strip():
            return f"{dimension_str} {pcs_and_after}"
        
        if before_pcs and not before_pcs.endswith(' '):
            return f"{before_pcs}  {dimension_str} {pcs_and_after}"
        else:
            return f"{before_pcs}{dimension_str} {pcs_and_after}"
    
    @classmethod
    def _already_has_dimensions(cls, text: str) -> bool:
        """检查文本是否已经包含尺寸信息"""
        import re
        dimension_patterns = [
            r'\d+\.?\d*L\s*×\s*\d+\.?\d*W\s*×\s*\d+\.?\d*T',
            r'\d+\.?\d*T\s*×\s*\d+\.?\d*L\s*×\s*\d+\.?\d*W',
        ]
        for pattern in dimension_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def get_strategy_config(cls, strategy_name: str = None):
        """获取策略配置"""
        if strategy_name is None:
            strategy_name = cls.DEFAULT_STRATEGY
        return cls.FILTER_STRATEGIES.get(strategy_name, cls.FILTER_STRATEGIES[cls.DEFAULT_STRATEGY])
