"""
子图检测器 - 基于连通性分析的子图分组
用于将DXF中的实体按空间连通性分组为独立的子图
"""
import ezdxf
from typing import List, Dict, Set, Tuple, Optional
import numpy as np
from collections import defaultdict


class SubgraphDetector:
    """
    基于连通性分析的子图检测器
    
    功能：
    1. 分析DXF中所有几何实体的空间关系
    2. 基于连通性将实体分组为独立的子图
    3. 为每个子图计算边界框和中心点
    4. 支持文本实体的归属判断
    """
    
    def __init__(self, dxf_path: str, connection_tolerance: float = 1.0):
        """
        初始化子图检测器
        
        Args:
            dxf_path: DXF文件路径
            connection_tolerance: 连接容差（mm），两个实体距离小于此值认为连通
        """
        self.dxf_path = dxf_path
        self.doc = ezdxf.readfile(dxf_path)
        self.msp = self.doc.modelspace()
        self.connection_tolerance = connection_tolerance
        
        # 存储分析结果
        self.entities = []  # 所有几何实体
        self.entity_bboxes = {}  # 实体ID -> 边界框
        self.subgraphs = []  # 子图列表
        
    def detect_subgraphs(self) -> List[Dict]:
        """
        检测所有子图
        
        Returns:
            子图列表，每个子图包含：
            - id: 子图ID
            - entities: 实体列表
            - bbox: 边界框 (x_min, y_min, x_max, y_max)
            - center: 中心点 (x, y)
            - area: 面积
            - entity_count: 实体数量
        """
        print("=" * 60)
        print("开始子图检测（基于连通性分析）")
        print("=" * 60)
        
        # 步骤1：收集所有几何实体
        self._collect_entities()
        
        # 步骤2：构建连通图
        adjacency = self._build_connectivity_graph()
        
        # 步骤3：查找连通分量（子图）
        self._find_connected_components(adjacency)
        
        # 步骤4：计算每个子图的属性
        self._compute_subgraph_properties()
        
        # 步骤5：过滤太小的子图
        self._filter_small_subgraphs(min_area=100, min_entities=3)
        
        print(f"✅ 检测完成，找到 {len(self.subgraphs)} 个有效子图")
        return self.subgraphs
    
    def _collect_entities(self):
        """收集所有几何实体并计算边界框"""
        print("收集几何实体...")
        
        entity_types = ['LINE', 'LWPOLYLINE', 'POLYLINE', 'CIRCLE', 'ARC', 'ELLIPSE', 'SPLINE']
        
        for entity in self.msp.query(' '.join(entity_types)):
            try:
                bbox = self._get_entity_bbox(entity)
                if bbox:
                    entity_id = len(self.entities)
                    self.entities.append(entity)
                    self.entity_bboxes[entity_id] = bbox
            except Exception as e:
                continue
        
        print(f"   找到 {len(self.entities)} 个几何实体")
    
    def _get_entity_bbox(self, entity) -> Optional[Tuple[float, float, float, float]]:
        """获取实体的边界框"""
        try:
            entity_type = entity.dxftype()
            
            if entity_type == 'LINE':
                x1, y1 = entity.dxf.start[0], entity.dxf.start[1]
                x2, y2 = entity.dxf.end[0], entity.dxf.end[1]
                return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            
            elif entity_type in ['LWPOLYLINE', 'POLYLINE']:
                points = list(entity.get_points(format='xy'))
                if points:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    return (min(xs), min(ys), max(xs), max(ys))
            
            elif entity_type == 'CIRCLE':
                cx, cy = entity.dxf.center[0], entity.dxf.center[1]
                r = entity.dxf.radius
                return (cx - r, cy - r, cx + r, cy + r)
            
            elif entity_type == 'ARC':
                cx, cy = entity.dxf.center[0], entity.dxf.center[1]
                r = entity.dxf.radius
                # 简化：使用圆的边界框
                return (cx - r, cy - r, cx + r, cy + r)
            
            elif entity_type == 'ELLIPSE':
                cx, cy = entity.dxf.center[0], entity.dxf.center[1]
                # 简化：使用一个估算的边界框
                major_axis = entity.dxf.major_axis
                ratio = entity.dxf.ratio
                rx = (major_axis[0]**2 + major_axis[1]**2)**0.5
                ry = rx * ratio
                return (cx - rx, cy - ry, cx + rx, cy + ry)
            
        except Exception as e:
            pass
        
        return None
    
    def _build_connectivity_graph(self) -> Dict[int, Set[int]]:
        """
        构建连通图
        
        Returns:
            邻接表：entity_id -> {connected_entity_ids}
        """
        print("构建连通图...")
        
        adjacency = defaultdict(set)
        n = len(self.entities)
        
        # 检查每对实体是否连通
        for i in range(n):
            for j in range(i + 1, n):
                if self._are_entities_connected(i, j):
                    adjacency[i].add(j)
                    adjacency[j].add(i)
        
        # 统计连接数
        total_connections = sum(len(neighbors) for neighbors in adjacency.values()) // 2
        print(f"   找到 {total_connections} 个连接关系")
        
        return adjacency
    
    def _are_entities_connected(self, id1: int, id2: int) -> bool:
        """
        判断两个实体是否连通
        
        连通条件：
        1. 边界框距离小于容差
        2. 或者边界框有重叠
        """
        bbox1 = self.entity_bboxes[id1]
        bbox2 = self.entity_bboxes[id2]
        
        # 计算边界框之间的最小距离
        dx = max(0, max(bbox1[0], bbox2[0]) - min(bbox1[2], bbox2[2]))
        dy = max(0, max(bbox1[1], bbox2[1]) - min(bbox1[3], bbox2[3]))
        distance = (dx**2 + dy**2)**0.5
        
        return distance <= self.connection_tolerance
    
    def _find_connected_components(self, adjacency: Dict[int, Set[int]]):
        """
        查找连通分量（使用DFS）
        
        Args:
            adjacency: 邻接表
        """
        print("查找连通分量...")
        
        visited = set()
        component_id = 0
        
        for entity_id in range(len(self.entities)):
            if entity_id not in visited:
                # 开始新的连通分量
                component = []
                self._dfs(entity_id, adjacency, visited, component)
                
                if component:
                    self.subgraphs.append({
                        'id': f"SUBGRAPH_{component_id:03d}",
                        'entity_ids': component,
                        'entities': [self.entities[i] for i in component]
                    })
                    component_id += 1
        
        print(f"   找到 {len(self.subgraphs)} 个连通分量")
    
    def _dfs(self, entity_id: int, adjacency: Dict[int, Set[int]], 
             visited: Set[int], component: List[int]):
        """深度优先搜索"""
        visited.add(entity_id)
        component.append(entity_id)
        
        for neighbor_id in adjacency.get(entity_id, []):
            if neighbor_id not in visited:
                self._dfs(neighbor_id, adjacency, visited, component)
    
    def _compute_subgraph_properties(self):
        """计算每个子图的属性"""
        print("计算子图属性...")
        
        for subgraph in self.subgraphs:
            # 计算整体边界框
            entity_ids = subgraph['entity_ids']
            bboxes = [self.entity_bboxes[eid] for eid in entity_ids]
            
            x_min = min(bbox[0] for bbox in bboxes)
            y_min = min(bbox[1] for bbox in bboxes)
            x_max = max(bbox[2] for bbox in bboxes)
            y_max = max(bbox[3] for bbox in bboxes)
            
            subgraph['bbox'] = (x_min, y_min, x_max, y_max)
            subgraph['center'] = ((x_min + x_max) / 2, (y_min + y_max) / 2)
            subgraph['area'] = (x_max - x_min) * (y_max - y_min)
            subgraph['entity_count'] = len(entity_ids)
    
    def _filter_small_subgraphs(self, min_area: float = 100, min_entities: int = 3):
        """过滤太小的子图"""
        original_count = len(self.subgraphs)
        
        self.subgraphs = [
            sg for sg in self.subgraphs
            if sg['area'] >= min_area and sg['entity_count'] >= min_entities
        ]
        
        filtered_count = original_count - len(self.subgraphs)
        if filtered_count > 0:
            print(f"   过滤掉 {filtered_count} 个小子图（面积<{min_area}或实体数<{min_entities}）")
    
    def assign_text_to_subgraphs(self, text_entities: List) -> Dict[str, int]:
        """
        将文本实体分配到最近的子图
        
        Args:
            text_entities: 文本实体列表
        
        Returns:
            文本内容 -> 子图索引的映射
        """
        text_to_subgraph = {}
        
        for text_entity in text_entities:
            try:
                # 获取文本位置
                if hasattr(text_entity.dxf, 'insert'):
                    pos = (text_entity.dxf.insert[0], text_entity.dxf.insert[1])
                elif hasattr(text_entity.dxf, 'location'):
                    pos = (text_entity.dxf.location[0], text_entity.dxf.location[1])
                else:
                    continue
                
                # 获取文本内容
                if text_entity.dxftype() == 'TEXT':
                    text = text_entity.dxf.text if hasattr(text_entity.dxf, 'text') else ''
                elif text_entity.dxftype() == 'MTEXT':
                    text = text_entity.text if hasattr(text_entity, 'text') else ''
                else:
                    continue
                
                # 查找最近的子图
                min_distance = float('inf')
                nearest_subgraph_idx = -1
                
                for idx, subgraph in enumerate(self.subgraphs):
                    center = subgraph['center']
                    distance = ((pos[0] - center[0])**2 + (pos[1] - center[1])**2)**0.5
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_subgraph_idx = idx
                
                if nearest_subgraph_idx >= 0:
                    text_to_subgraph[text] = nearest_subgraph_idx
            
            except Exception as e:
                continue
        
        return text_to_subgraph
    
    def visualize_subgraphs(self, output_path: str):
        """
        可视化子图（在DXF中用不同颜色标记）
        
        Args:
            output_path: 输出DXF文件路径
        """
        print(f"生成子图可视化...")
        
        # 创建新文档
        new_doc = ezdxf.new('R2010')
        new_msp = new_doc.modelspace()
        
        # 为每个子图创建图层
        colors = [1, 2, 3, 4, 5, 6, 7, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]
        
        for idx, subgraph in enumerate(self.subgraphs):
            layer_name = f"SUBGRAPH_{idx:03d}"
            color = colors[idx % len(colors)]
            
            if layer_name not in new_doc.layers:
                new_doc.layers.new(layer_name, dxfattribs={'color': color})
            
            # 复制实体到新图层
            for entity in subgraph['entities']:
                try:
                    new_entity = entity.copy()
                    new_entity.dxf.layer = layer_name
                    new_msp.add_entity(new_entity)
                except:
                    pass
            
            # 添加边界框
            bbox = subgraph['bbox']
            points = [
                (bbox[0], bbox[1]),
                (bbox[2], bbox[1]),
                (bbox[2], bbox[3]),
                (bbox[0], bbox[3]),
                (bbox[0], bbox[1])
            ]
            new_msp.add_lwpolyline(points, dxfattribs={'layer': layer_name, 'color': color})
            
            # 添加标签
            center = subgraph['center']
            text_entity = new_msp.add_text(
                f"{subgraph['id']}\n实体数:{subgraph['entity_count']}\n面积:{subgraph['area']:.0f}",
                dxfattribs={
                    'layer': layer_name,
                    'color': color,
                    'height': 50,
                    'insert': center
                }
            )
        
        new_doc.saveas(output_path)
        print(f"✅ 可视化已保存到: {output_path}")


if __name__ == "__main__":
    # 测试代码
    dxf_file = r"D:\my_project\cadagent\sheet_line\ceshitu009.dxf"
    
    detector = SubgraphDetector(dxf_file, connection_tolerance=5.0)
    subgraphs = detector.detect_subgraphs()
    
    print("\n" + "=" * 60)
    print("📋 子图详情")
    print("=" * 60)
    for sg in subgraphs:
        print(f"\n{sg['id']}:")
        print(f"  实体数: {sg['entity_count']}")
        print(f"  面积: {sg['area']:.1f} mm²")
        print(f"  中心: ({sg['center'][0]:.1f}, {sg['center'][1]:.1f})")
        print(f"  边界框: ({sg['bbox'][0]:.1f}, {sg['bbox'][1]:.1f}) -> ({sg['bbox'][2]:.1f}, {sg['bbox'][3]:.1f})")
    
    # 生成可视化
    output_file = r"D:\my_project\cadagent\sheet_line\output\subgraphs_visualization.dxf"
    detector.visualize_subgraphs(output_file)
