# 板料线自动生成模块

## 📋 概述

板料线（Material Line）自动生成模块是一个用于 CAD 图纸处理的独立工具集，主要功能是从 DXF/DWG 文件中自动识别零件的三视图，并在视图上添加板料线标注。该模块专注于模具零件的板料尺寸标注，支持多零件识别和智能尺寸提取。

## 🎯 核心功能

### 1. 格式转换
- DWG → DXF 转换（支持 ODA File Converter）
- 支持多种 AutoCAD 版本

### 2. 尺寸提取
- **高精度 L×W×T 提取**：从文本标注中提取长宽高信息
- **CAD 标注提取**：从 DIMENSION 实体中提取尺寸
- **三重条件筛选**：基于子图编号、PCS 数量、加工说明的智能筛选
- **智能推断**：当无法提取时使用默认尺寸

### 3. 视图识别
- 自动识别主视图、俯视图、侧视图
- 支持 LWPOLYLINE 和 LINE 组成的视图
- 基于尺寸匹配和位置分析的视图分类

### 4. 板料线生成
- 在识别的视图上自动添加板料线
- 支持单零件和多零件模式
- 避免重复添加（去重机制）
- 使用 CAD 标准属性（颜色 252，虚线）

### 5. 子图检测
- 基于连通性分析的子图分组
- 自动计算子图边界框和中心点
- 支持文本实体归属判断

## 📁 文件结构

```
banliaoxian/
├── dwg_to_dxf_converter.py              # DWG→DXF 转换工具
├── dxf_auto_sheetline.py                # 主处理脚本（板料线生成）
├── precision_lwt_extractor.py           # 高精度 L×W×T 提取器
├── triple_condition_processor_optimized.py  # 三重条件处理器（优化版）
├── triple_condition_config.py           # 三重条件配置文件
├── subgraph_detector.py                 # 子图检测器
├── path_config.py                       # 路径配置文件（重要）
└── README.md                            # 本文档
```

### 核心文件说明

- **path_config.py**：集中管理所有绝对路径配置，包括：
  - ODA File Converter 路径
  - 测试文件路径
  - 输出目录路径
  - 提供路径检查和自动创建目录功能

## 🚀 快速开始

### 环境要求

```bash
# Python 依赖
pip install ezdxf numpy networkx pandas

# 可选：ODA File Converter（用于 DWG 转换）
# 下载地址：https://www.opendesign.com/guestfiles/oda_file_converter
```

### 路径配置

首次使用前，需要配置路径信息：

1. 复制配置示例文件：

```bash
cd mold_cost_/scripts/banliaoxian
cp path_config.example.py path_config.py
```

2. 编辑 `path_config.py`，根据实际情况修改以下配置：

```python
# ODA File Converter 路径
ODA_CONVERTER_PATH = r"D:\my_project\ODAFileConverter.exe"

# 测试 DXF 文件目录
TEST_DXF_DIR = r"D:\my_project\cadagent\sheet_line"
```

3. 运行环境检查：

```bash
python path_config.py
```

这将检查所有路径配置是否正确，并自动创建必要的输出目录。

**输出示例**：
```
================================================================================
板料线模块环境检查
================================================================================
📁 项目根目录: D:\workspace\projects\mold3.0
   存在: ✅

📁 板料线模块目录: D:\workspace\projects\mold3.0\mold_cost_\scripts\banliaoxian
   存在: ✅

🔧 ODA File Converter: D:\my_project\ODAFileConverter.exe
   存在: ✅

📁 测试文件目录: D:\my_project\cadagent\sheet_line
   存在: ✅

📄 测试文件:
   ceshitu: ✅ D:\my_project\cadagent\sheet_line\ceshitu.dxf
   ceshitu009: ✅ D:\my_project\cadagent\sheet_line\ceshitu009.dxf
   ...

📁 输出目录:
   默认输出: D:\workspace\projects\mold3.0\output\banliaoxian
   日志目录: D:\workspace\projects\mold3.0\logs\banliaoxian
   ...
================================================================================
环境检查完成
================================================================================
```

**注意事项**：
- `path_config.py` 已添加到 `.gitignore`，不会被提交到版本控制
- 每个开发者可以有自己的路径配置
- 如果 `path_config.py` 不存在，脚本会使用默认路径并显示警告

### 基本使用

#### 1. DWG 转 DXF

```python
from dwg_to_dxf_converter import convert_with_oda

# 转换 DWG 文件
dwg_path = "drawing.dwg"
dxf_path = "drawing.dxf"
success = convert_with_oda(dwg_path, dxf_path)
```

#### 2. 自动添加板料线

```python
from dxf_auto_sheetline import process_single_dxf_with_triple_integration

# 处理 DXF 文件
dxf_file = "drawing.dxf"
output_dir = "./output"
log_dir = "./logs"

success = process_single_dxf_with_triple_integration(
    dxf_file_path=dxf_file,
    output_dir=output_dir,
    log_file_dir=log_dir,
    use_triple_condition=True,  # 启用三重条件筛选
    multi_part_mode=True        # 多零件模式
)
```

#### 3. 高精度 L×W×T 提取

```python
from precision_lwt_extractor import analyze_with_precision

# 提取 L×W×T 信息
dxf_file = "drawing.dxf"
results = analyze_with_precision(
    dxf_file_path=dxf_file,
    enable_triple_filter=True  # 启用三重条件筛选
)

# 查看结果
for i, result in enumerate(results):
    lwt = result['lwt']
    print(f"零件 {i+1}: L={lwt['L']}, W={lwt['W']}, T={lwt['T']}")
    print(f"  置信度: {result['confidence']:.2f}")
    print(f"  原始文本: {result['raw_text']}")
```

#### 4. 子图检测

```python
from subgraph_detector import SubgraphDetector

# 检测子图
detector = SubgraphDetector(
    dxf_path="drawing.dxf",
    connection_tolerance=5.0  # 连接容差（mm）
)

subgraphs = detector.detect_subgraphs()

# 查看结果
for sg in subgraphs:
    print(f"{sg['id']}: {sg['entity_count']} 个实体, 面积={sg['area']:.1f} mm²")

# 生成可视化
detector.visualize_subgraphs("output/subgraphs_visualization.dxf")
```

## 🔧 核心算法

### 1. 三重条件筛选策略

三重条件筛选用于从大量文本中准确识别零件信息：

**条件 1：子图编号**
- 识别模式：`A1-1`, `PS-1`, `DIE-1`, `M250286-P2` 等
- 排除几何标注：`r12`, `φ20`, `M6` 等

**条件 2：PCS 数量**
- 识别模式：`1PCS`, `2 PCS`, `10个`, `5件` 等

**条件 3：加工说明**
- 材料：`45#`, `CR12MOV`, `P20`, `SKD11` 等
- 硬度：`HRC`, `HB`, `HV` 等
- 热处理：`淬火`, `回火`, `调质` 等
- 表面处理：`镀`, `氧化`, `发黑` 等
- 加工方法：`车`, `铣`, `钻`, `磨` 等

**筛选逻辑**：
```
满足条件 = 子图编号 AND (PCS 或 加工说明)
```

### 2. L×W×T 提取优先级

```
优先级 1: 从视图几何提取（最可靠）
    ↓ 失败
优先级 2: CAD 标注提取（DIMENSION 实体）
    ↓ 失败
优先级 3: 文本数字提取（正则匹配）
    ↓ 失败
优先级 4: 智能默认值（基于子图类型）
```

### 3. 视图识别算法

**步骤 1：尺寸匹配**
- 使用动态容差（相对误差 5%）
- 考虑旋转（宽高可互换）
- 匹配三种视图类型：
  - 主视图：L × W
  - 俯视图：L × T
  - 侧视图：T × W

**步骤 2：位置辅助**
- 标准第一视角布局参考
- 左下角：俯视图
- 左上角：主视图
- 右上角：侧视图

**步骤 3：去重机制**
- 每种视图类型只添加一次
- 避免重复添加板料线

### 4. 动态容差策略

```python
def calculate_dynamic_tolerance(dimension: float, relative_error: float = 0.05) -> float:
    """
    动态容差 = dimension × relative_error
    限制范围：2mm ~ 20mm
    """
    min_tolerance = 2.0
    max_tolerance = 20.0
    tolerance = dimension * relative_error
    return max(min_tolerance, min(tolerance, max_tolerance))
```

**优势**：
- 小尺寸零件：使用较小容差（避免误匹配）
- 大尺寸零件：使用较大容差（提高匹配率）

## 📊 处理模式

### 单零件模式

```python
process_single_dxf_with_triple_integration(
    dxf_file_path="drawing.dxf",
    output_dir="./output",
    multi_part_mode=False  # 单零件模式
)
```

- 选择置信度最高的 L×W×T
- 在一个 DXF 文件中添加板料线
- 适用于单个零件的图纸

### 多零件模式

```python
process_single_dxf_with_triple_integration(
    dxf_file_path="drawing.dxf",
    output_dir="./output",
    multi_part_mode=True  # 多零件模式
)
```

- 为每个识别的零件生成独立的 DXF 文件
- 文件命名：`原文件名_PART_1.dxf`, `原文件名_PART_2.dxf` 等
- 适用于包含多个零件的图纸

## 🎨 输出格式

### 板料线属性

- **图层名称**：`MATERIAL_LINE_主视图`, `MATERIAL_LINE_俯视图`, `MATERIAL_LINE_侧视图`
- **颜色**：252（CAD 标准板料线颜色）
- **线型**：DASHED（虚线）
- **线宽**：默认

### 输出文件

```
output/
├── drawing_with_material_lines.dxf  # 单零件模式输出
├── drawing_PART_1.dxf               # 多零件模式输出
├── drawing_PART_2.dxf
└── ...
```

### 日志文件

```
logs/
├── processing.log                   # 处理日志
├── lwt_report.txt                   # L×W×T 提取报告
└── errors.log                       # 错误日志
```

## ⚙️ 配置选项

### 三重条件配置

编辑 `triple_condition_config.py`：

```python
class TripleConditionConfig:
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
    
    DEFAULT_STRATEGY = 'strict'  # 默认策略
    
    # CAD 标注提取配置
    CAD_ANNOTATION_EXTRACTION = {
        'enable_cad_extraction': True,
        'search_radius': 200.0,
        'min_dimension_value': 0.5,
        'max_dimension_value': 5000.0,
        'exclude_small_values': True,
        'small_value_threshold': 5.0,
        'confidence_threshold': 0.6,
    }
    
    # 默认尺寸配置
    DEFAULT_DIMENSIONS = {
        'ps': {'L': 100.0, 'W': 80.0, 'T': 10.0},
        'ph': {'L': 150.0, 'W': 120.0, 'T': 15.0},
        'die': {'L': 200.0, 'W': 150.0, 'T': 20.0},
        'default': {'L': 120.0, 'W': 90.0, 'T': 12.0},
    }
```

### 处理模式配置

编辑 `dxf_auto_sheetline.py`：

```python
PROCESSING_MODE = {
    'precision_lwt': False,      # 原有精密 L/W/T 提取器
    'triple_condition': True,    # 三重条件系统（推荐）
    'hybrid': False             # 混合模式（未来扩展）
}
```

## 🐛 常见问题

### 1. DWG 转 DXF 失败

**问题**：`ODA File Converter 未找到`

**解决**：
```python
# 方法1：在 path_config.py 中修改路径
ODA_CONVERTER_PATH = r"D:\your_path\ODAFileConverter.exe"

# 方法2：添加备用路径
ODA_CONVERTER_FALLBACK_PATHS = [
    r"D:\workspace\ODA\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter.exe",
]

# 方法3：运行环境检查
python path_config.py
```

### 2. 未识别到 L×W×T

**问题**：提取器返回空结果

**解决**：
1. 检查文本格式是否符合模式（如 `100L×80W×10T`）
2. 启用三重条件筛选：`enable_triple_filter=True`
3. 检查是否有 CAD 标注（DIMENSION 实体）
4. 降低筛选策略严格度：`DEFAULT_STRATEGY = 'medium'`

### 3. 视图识别错误

**问题**：板料线添加到错误的视图

**解决**：
1. 调整动态容差：修改 `relative_error` 参数
2. 检查视图尺寸是否与 L×W×T 匹配
3. 使用 `subgraph_detector.py` 可视化子图

### 4. 重复添加板料线

**问题**：同一视图添加了多条板料线

**解决**：
- 已内置去重机制，检查是否禁用了去重功能
- 检查视图类型判断逻辑

### 5. 性能问题

**问题**：处理大文件时速度慢

**解决**：
1. 使用优化版处理器：`OptimizedTripleConditionProcessor`
2. 减小搜索半径：`search_radius=100.0`
3. 启用缓存机制（已默认启用）

### 6. 路径配置问题

**问题**：测试文件找不到或输出目录创建失败

**解决**：
```bash
# 运行环境检查
python path_config.py

# 查看详细的路径配置信息和错误提示
# 根据提示修改 path_config.py 中的路径配置
```

## 📈 性能优化

### 已实现的优化

1. **正则表达式预编译**：避免重复编译
2. **缓存机制**：缓存文本分析结果
3. **单次遍历**：一次遍历完成所有处理
4. **早期筛选**：快速排除不相关文本
5. **批量处理**：减少 I/O 操作

### 性能指标

- 单个 DXF 文件（100 个文本实体）：< 2 秒
- 多零件模式（10 个零件）：< 5 秒
- 子图检测（500 个实体）：< 3 秒

## 🔬 测试

### 单元测试

```bash
# 测试 DWG 转换
python dwg_to_dxf_converter.py test.dwg

# 测试 L×W×T 提取
python precision_lwt_extractor.py

# 测试子图检测
python subgraph_detector.py

# 测试三重条件处理器
python triple_condition_processor_optimized.py
```

### 集成测试

```bash
# 完整流程测试
python dxf_auto_sheetline.py
```

## 📝 开发日志

### 最近更新（2026-03-09）

1. ✅ 添加动态容差策略（解决小尺寸零件误匹配）
2. ✅ 改进匹配得分计算（使用相对误差）
3. ✅ 添加视图类型去重机制（防止重复添加板料线）
4. ✅ 优化三重条件处理器性能
5. ✅ 添加零件去重机制
6. ✅ 改进视图中心位置查找
7. ✅ 添加文本重构功能

### 已知问题

1. 对于非标准布局的图纸，视图识别可能不准确
2. 某些特殊字体的文本可能无法正确提取
3. 极小尺寸零件（< 10mm）的识别精度较低

### 未来计划

1. 支持更多 CAD 格式（STEP, IGES）
2. 添加 GUI 界面
3. 支持批量处理
4. 添加机器学习模型提高识别精度
5. 支持自定义板料线样式

## 🤝 贡献指南

### 代码规范

- 使用 Python 3.8+
- 遵循 PEP 8 代码风格
- 添加类型注解
- 编写文档字符串

### 提交规范

```
feat: 添加新功能
fix: 修复 bug
docs: 更新文档
perf: 性能优化
refactor: 代码重构
test: 添加测试
```

## 📄 许可证

本模块为内部开发工具，仅用于开发测试。

## 📞 联系方式

如有问题或建议，请联系开发团队。

---

**最后更新**：2026-03-10  
**版本**：v2.0  
**维护者**：Kiro AI
