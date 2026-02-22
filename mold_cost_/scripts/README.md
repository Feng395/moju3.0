# Scripts 模块

## 📋 概述

Scripts 模块包含模具成本核算系统的核心业务逻辑实现，包括 CAD 拆图、特征识别、价格计算和数据搜索等功能。这些脚本被 AI Agents 调用，完成具体的计算和处理任务。

## 📁 目录结构

```
scripts/
├── cad_chaitu/              # CAD拆图模块
│   ├── cad_system.py       # CAD系统主入口
│   ├── converter.py        # 格式转换器
│   ├── block_analyzer.py   # 图块分析
│   ├── cutting_detector.py # 切割检测
│   ├── text_processor.py   # 文本处理
│   ├── number_extractor.py # 数字提取
│   ├── storage.py          # 存储管理
│   ├── database.py         # 数据库操作
│   ├── unified_api.py      # 统一API接口
│   └── utils.py            # 工具函数
├── feature_recognition/     # 特征识别模块
│   ├── feature_recognition.py  # 特征识别主入口
│   ├── dimension_extractor.py  # 尺寸提取
│   ├── view_identifier.py      # 视图识别
│   ├── material_info_extractor.py  # 材料信息提取
│   ├── tooth_hole_detector.py      # 齿孔检测
│   ├── chamfer_detector.py         # 倒角检测
│   ├── bevel_detector.py           # 斜面检测
│   ├── oil_tank_detector.py        # 油槽检测
│   ├── hanging_table_detector.py   # 挂台检测
│   ├── grinding_detector.py        # 磨削检测
│   ├── water_mill_calculator.py    # 水磨计算
│   ├── wire_length_calculator.py   # 线割长度计算
│   ├── boring_calculator.py        # 镗孔计算
│   ├── slider_calculator.py        # 滑块计算
│   └── ...
├── calculate/               # 价格计算模块
│   ├── price_material.py   # 材料价格
│   ├── price_nc_base.py    # NC基础价格
│   ├── price_nc_time.py    # NC时间价格
│   ├── price_nc_total.py   # NC总价格
│   ├── price_water_mill_*.py  # 水磨价格系列
│   ├── price_wire_*.py        # 线割价格系列
│   ├── price_heat.py          # 热处理价格
│   ├── price_tooth_hole.py    # 齿孔价格
│   ├── price_weight.py        # 重量价格
│   ├── price_total.py         # 总价格
│   └── judgment.py            # 判断逻辑
├── search/                  # 数据搜索模块
│   ├── search.py           # 搜索主入口
│   ├── material_search.py  # 材料搜索
│   ├── density_search.py   # 密度搜索
│   ├── heat_search.py      # 热处理搜索
│   ├── nc_search.py        # NC搜索
│   ├── water_mill_search.py # 水磨搜索
│   ├── wire_*_search.py    # 线割搜索系列
│   ├── tooth_hole_search.py # 齿孔搜索
│   └── total_search.py     # 总搜索
├── minio_client.py         # MinIO客户端
├── process_rule_matcher.py # 工艺规则匹配
├── monitor_*.py            # 监控脚本
└── __init__.py
```

## 🎨 CAD 拆图模块 (`cad_chaitu/`)

### 功能概述

CAD 拆图模块负责解析 CAD 文件，提取图纸信息，识别图块和文本。

### 核心组件

#### 1. CADSystem (cad_system.py)

**主要功能**:
- CAD 文件格式转换 (DWG → DXF)
- 图纸解析和分析
- 图块识别和提取
- 文本信息提取

**使用示例**:
```python
from scripts.cad_chaitu.cad_system import CADSystem

cad_system = CADSystem()
result = await cad_system.process_cad_file(
    file_path="path/to/file.dwg",
    job_id="job-123"
)
```

#### 2. Converter (converter.py)

**主要功能**:
- DWG 转 DXF 格式
- 支持多种 CAD 版本
- 批量转换

**使用示例**:
```python
from scripts.cad_chaitu.converter import convert_dwg_to_dxf

dxf_path = convert_dwg_to_dxf("input.dwg", "output.dxf")
```

#### 3. BlockAnalyzer (block_analyzer.py)

**主要功能**:
- 图块识别
- 图块属性提取
- 图块关系分析

#### 4. TextProcessor (text_processor.py)

**主要功能**:
- 文本提取
- 文本分类
- 文本位置识别

### 工作流程

```
1. 上传 DWG 文件
   ↓
2. 格式转换 (DWG → DXF)
   ↓
3. 解析 DXF 文件
   ↓
4. 提取图块和文本
   ↓
5. 分析图纸结构
   ↓
6. 存储结果到数据库
```

## 🔍 特征识别模块 (`feature_recognition/`)

### 功能概述

特征识别模块负责从 CAD 图纸中识别各种加工特征，如孔、槽、倒角等。

### 核心组件

#### 1. FeatureRecognition (feature_recognition.py)

**主要功能**:
- 统一的特征识别入口
- 协调各个识别器
- 结果汇总和验证

**使用示例**:
```python
from scripts.feature_recognition.feature_recognition import recognize_features

features = await recognize_features(
    dxf_path="path/to/file.dxf",
    job_id="job-123"
)
```

#### 2. DimensionExtractor (dimension_extractor.py)

**主要功能**:
- 提取尺寸标注
- 识别长宽高
- 计算体积

**识别内容**:
- 长度尺寸
- 宽度尺寸
- 高度尺寸
- 直径尺寸
- 角度尺寸

#### 3. ToothHoleDetector (tooth_hole_detector.py)

**主要功能**:
- 检测齿孔
- 计算齿孔数量
- 识别齿孔类型

**齿孔类型**:
- 通孔
- 盲孔
- 螺纹孔
- 沉孔

#### 4. ChamferDetector (chamfer_detector.py)

**主要功能**:
- 检测倒角
- 识别倒角类型
- 计算倒角尺寸

**倒角类型**:
- 直角倒角
- 圆角倒角
- 斜角倒角

#### 5. WaterMillCalculator (water_mill_calculator.py)

**主要功能**:
- 计算水磨面积
- 识别水磨类型
- 估算加工时间

**水磨类型**:
- 平面水磨
- 斜面水磨
- 曲面水磨

#### 6. WireLengthCalculator (wire_length_calculator.py)

**主要功能**:
- 计算线割长度
- 识别线割路径
- 估算加工时间

### 识别流程

```
1. 加载 DXF 文件
   ↓
2. 识别视图类型
   ↓
3. 提取尺寸信息
   ↓
4. 检测各类特征
   ↓
5. 计算特征参数
   ↓
6. 验证识别结果
   ↓
7. 返回特征数据
```

## 💰 价格计算模块 (`calculate/`)

### 功能概述

价格计算模块负责根据识别的特征和工艺参数，计算各项成本和总价格。

### 核心组件

#### 1. 材料价格 (price_material.py)

**计算内容**:
- 材料单价
- 材料重量
- 材料总价
- 损耗系数

**计算公式**:
```python
材料价格 = 材料单价 × 材料重量 × (1 + 损耗率)
```

#### 2. NC 价格系列

**price_nc_base.py** - NC 基础价格
```python
NC基础价格 = 基础单价 × 加工面积
```

**price_nc_time.py** - NC 时间价格
```python
NC时间价格 = 时间单价 × 加工时间
```

**price_nc_total.py** - NC 总价格
```python
NC总价格 = NC基础价格 + NC时间价格 + 附加费用
```

#### 3. 水磨价格系列

**price_water_mill_plate.py** - 板材水磨
**price_water_mill_bevel_cost.py** - 斜面水磨
**price_water_mill_chamfer_cost.py** - 倒角水磨
**price_water_mill_oil_tank.py** - 油槽水磨
**price_water_mill_hanging_table.py** - 挂台水磨
**price_water_mill_long_strip.py** - 长条水磨
**price_water_mill_high_cost.py** - 高精度水磨
**price_water_mill_thread_ends.py** - 螺纹端面水磨
**price_water_mill_component.py** - 组件水磨
**price_water_mill_total.py** - 水磨总价

#### 4. 线割价格系列

**price_wire_base.py** - 线割基础价格
**price_wire_standard.py** - 标准线割
**price_wire_special.py** - 特殊线割
**price_wire_total.py** - 线割总价

#### 5. 其他价格

**price_heat.py** - 热处理价格
**price_tooth_hole.py** - 齿孔加工价格
**price_weight.py** - 重量相关价格
**price_add_auto_material.py** - 自动添加材料价格

#### 6. 总价格 (price_total.py)

**计算内容**:
```python
总价格 = 材料价格 + NC价格 + 水磨价格 + 线割价格 + 热处理价格 + 其他费用
```

### 计算流程

```
1. 获取特征数据
   ↓
2. 查询价格规则
   ↓
3. 计算材料成本
   ↓
4. 计算加工成本
   ↓
5. 计算附加费用
   ↓
6. 汇总总价格
   ↓
7. 生成价格明细
```

## 🔎 搜索模块 (`search/`)

### 功能概述

搜索模块负责从数据库中查询各种价格数据和工艺参数。

### 核心组件

#### 1. MaterialSearch (material_search.py)

**查询内容**:
- 材料单价
- 材料规格
- 材料供应商
- 材料库存

#### 2. DensitySearch (density_search.py)

**查询内容**:
- 材料密度
- 密度单位转换

#### 3. HeatSearch (heat_search.py)

**查询内容**:
- 热处理工艺
- 热处理价格
- 热处理时间

#### 4. NCSearch (nc_search.py)

**查询内容**:
- NC 加工单价
- NC 时间单价
- NC 设备参数

#### 5. WaterMillSearch (water_mill_search.py)

**查询内容**:
- 水磨单价
- 水磨工艺参数
- 水磨设备信息

#### 6. WireSearch 系列

**查询内容**:
- 线割单价
- 线割工艺参数
- 线割设备信息

### 搜索流程

```
1. 接收查询参数
   ↓
2. 构建查询条件
   ↓
3. 执行数据库查询
   ↓
4. 过滤和排序结果
   ↓
5. 格式化返回数据
```

## 🛠️ 工具脚本

### MinIO 客户端 (minio_client.py)

**功能**:
- 文件上传
- 文件下载
- 预签名 URL 生成
- 文件删除

**使用示例**:
```python
from scripts.minio_client import MinIOClient

client = MinIOClient()
url = await client.upload_file("local_file.dwg", "remote_path.dwg")
```

### 工艺规则匹配 (process_rule_matcher.py)

**功能**:
- 匹配工艺规则
- 验证工艺参数
- 推荐工艺方案

**使用示例**:
```python
from scripts.process_rule_matcher import match_process_rules

rules = await match_process_rules(
    feature_type="hole",
    parameters={"diameter": 10, "depth": 20}
)
```

### 监控脚本

**monitor_concurrency.py** - 并发监控
**monitor_locks.py** - 锁监控
**monitor_redis_websocket.py** - Redis/WebSocket 监控

## 🧪 测试

### 单元测试

```bash
# 测试 CAD 拆图
pytest tests/scripts/test_cad_chaitu.py

# 测试特征识别
pytest tests/scripts/test_feature_recognition.py

# 测试价格计算
pytest tests/scripts/test_calculate.py

# 测试搜索功能
pytest tests/scripts/test_search.py
```

### 集成测试

```bash
# 端到端测试
pytest tests/integration/test_full_workflow.py
```

## 📊 性能优化

### 并行处理

```python
import asyncio

# 并行识别多个特征
results = await asyncio.gather(
    recognize_holes(dxf_data),
    recognize_chamfers(dxf_data),
    recognize_surfaces(dxf_data)
)
```

### 缓存策略

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_material_price(material_code: str):
    # 缓存材料价格查询结果
    return query_material_price(material_code)
```

## 📝 配置

### 环境变量

```bash
# ODA 转换器路径
ODA_FILE_CONVERTER_PATH=/path/to/ODAFileConverter.exe

# MinIO 配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mold_cost_db
```

## 📚 相关文档

- [Agents 文档](../agents/README.md)
- [API Gateway 文档](../api_gateway/README.md)
- [主项目文档](../README.md)

## 🤝 贡献指南

1. 遵循现有代码风格
2. 添加必要的注释
3. 编写单元测试
4. 更新相关文档
5. 提交 Pull Request

## 📞 联系方式

如有问题，请联系 Scripts 团队或提交 Issue。
