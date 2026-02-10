# Spec: 特征数据表设计与实现

## 一、需求背景

### 1.1 当前问题
当前系统中，`subgraphs`表包含80+字段，混合了以下三类数据：
1. **特征数据**：从CAD文件中提取的几何特征和加工说明
2. **业务数据**：工艺决策、价格计算、成本汇总等
3. **报表数据**：对应M250209报表的43列数据

这种设计导致：
- 表结构臃肿，难以维护
- 特征数据与业务数据耦合
- 无法追溯特征识别的历史版本
- 扩展性差（新增特征类型需要修改表结构）

### 1.2 解决方案
将特征数据从`subgraphs`表中分离出来，创建独立的`features`表：
- **features表**：存储从CAD文件中提取的原始特征数据，支持历史版本
- **subgraphs表**：保留业务数据、成本数据和报表数据
- **关系**：一对多关系（一个subgraph可以有多个feature版本）
- **不保留冗余字段**：subgraphs表不保留任何特征字段，需要时通过JOIN查询
- **一个子图一种主要特征**：每个子图只对应一种主要特征类型（feature_type）
- **子图文件URL**：subgraphs表保存拆分后的子图文件URL（subgraph_file_url）

## 二、用户故事

### US-1: 作为CAD Agent，我需要将提取的特征数据存储到独立的表中
**验收标准**：
- 能够将边界框、面积、周长等特征数据保存到features表
- 能够将三个视图的线割长度保存到独立字段
- 能够将所有加工说明保存到processing_instructions JSONB字段
- 能够记录是否有自找料、是否需要热处理、镗孔长度等特征
- 能够记录识别方法和置信度
- 能够标记特征数据是否完整
- 能够保存拆分后的子图文件URL到subgraphs表

### US-2: 作为系统，我需要支持特征识别的历史版本
**验收标准**：
- 每次重新识别时，创建新的feature记录，version自动递增
- 能够查询某个子图的所有历史版本
- 能够查询某个子图的最新版本
- 能够对比不同版本之间的差异

### US-3: 作为Decision Agent，我需要查询完整的特征数据进行工艺决策
**验收标准**：
- 能够通过JOIN查询获取最新版本的特征数据
- 能够查询三个视图的线割长度
- 能够查询加工说明（processing_instructions）
- 能够根据特征类型过滤数据

### US-4: 作为系统管理员，我需要查看特征提取的完整性和质量
**验收标准**：
- 能够查询is_complete字段，了解哪些子图的特征数据不完整
- 能够查询missing_params字段，了解缺失哪些参数
- 能够查询confidence字段，了解识别置信度
- 能够查询recognition_method字段，了解识别方法
- 能够查看特征识别的历史版本和变更记录

### US-5: 作为开发人员，我需要扩展新的特征类型而不修改表结构
**验收标准**：
- 能够在processing_instructions JSONB字段中添加新的加工说明
- 能够在extended_features JSONB字段中添加新特征
- 能够查询和过滤JSONB字段中的特征
- 不需要执行ALTER TABLE操作

## 三、技术设计

### 3.1 数据库表结构

#### 3.1.1 features表（新建）
```sql
CREATE TABLE IF NOT EXISTS features (
    feature_id BIGSERIAL PRIMARY KEY,
    subgraph_id VARCHAR(50) NOT NULL REFERENCES subgraphs(subgraph_id),
    job_id UUID NOT NULL REFERENCES jobs(job_id),
    version INTEGER NOT NULL DEFAULT 1,
    feature_type VARCHAR(20) NOT NULL,
    
    -- 几何特征
    thickness_mm DECIMAL(10, 3),
    bbox_min_x DECIMAL(10, 3),
    bbox_min_y DECIMAL(10, 3),
    bbox_max_x DECIMAL(10, 3),
    bbox_max_y DECIMAL(10, 3),
    area_mm2 DECIMAL(12, 3),
    perimeter_mm DECIMAL(10, 3),
    
    -- 三个视图的线割长度
    top_view_wire_length DECIMAL(10, 3),
    front_view_wire_length DECIMAL(10, 3),
    side_view_wire_length DECIMAL(10, 3),
    
    -- 加工特征
    has_auto_material BOOLEAN DEFAULT false,
    needs_heat_treatment BOOLEAN DEFAULT false,
    boring_length_mm DECIMAL(10, 3),
    hole_diameter_mm DECIMAL(10, 3),
    hole_count INTEGER,
    
    -- 加工说明（JSON格式，包含所有提取到的加工说明）
    processing_instructions JSONB,
    
    -- 识别信息
    confidence DECIMAL(5, 4),
    recognition_method VARCHAR(50),
    is_complete BOOLEAN DEFAULT false,
    missing_params TEXT[],
    
    -- 扩展特征
    extended_features JSONB,
    
    -- 元数据
    created_by VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB
);

-- 创建索引
CREATE INDEX idx_features_subgraph_id ON features(subgraph_id);
CREATE INDEX idx_features_job_id ON features(job_id);
CREATE INDEX idx_features_version ON features(subgraph_id, version DESC);
CREATE INDEX idx_features_feature_type ON features(feature_type);
CREATE INDEX idx_features_processing_instructions ON features USING GIN(processing_instructions);
CREATE INDEX idx_features_extended_features ON features USING GIN(extended_features);

-- 创建唯一约束（同一子图的同一版本号唯一）
CREATE UNIQUE INDEX idx_features_subgraph_version ON features(subgraph_id, version);
```

#### 3.1.2 subgraphs表（修改）
移除所有特征相关字段，只保留业务数据和报表数据：
- 移除：`thickness_mm`, `bbox_*`, `area_mm2`, `perimeter_mm`, `confidence`, `recognition_method`等
- 新增：`subgraph_file_url`（拆分后的子图文件URL）
- 保留：`feature_type`（主要特征类型，用于快速过滤）

### 3.2 processing_instructions JSONB字段结构

#### 3.2.1 加工说明示例
```json
{
  "wire_cutting": {
    "method": "slow_wire",
    "passes": "cut1_trim1",
    "note": "慢丝割一修一，精度要求±0.01mm"
  },
  "nc_machining": {
    "roughing": {
      "required": true,
      "estimated_time": 120,
      "note": "开粗去除大部分材料"
    },
    "milling": {
      "required": true,
      "estimated_time": 60,
      "note": "精铣达到精度要求"
    }
  },
  "drilling": {
    "required": true,
    "hole_count": 5,
    "hole_diameter": [6, 8, 10],
    "note": "钻孔后需要倒角"
  },
  "heat_treatment": {
    "required": true,
    "method": "quenching",
    "temperature": 850,
    "note": "淬火处理，硬度HRC50-55"
  },
  "surface_finish": {
    "required": false,
    "method": "grinding",
    "note": "表面粗糙度Ra0.8"
  },
  "special_instructions": [
    "注意保护基准面",
    "加工前需要去毛刺",
    "完成后需要清洗"
  ]
}
```

### 3.3 查询示例

#### 3.3.1 查询子图及其最新特征（JOIN）
```python
from sqlalchemy.orm import joinedload
from sqlalchemy import desc

# 查询子图及其最新版本的特征
subgraph_with_feature = session.query(Subgraph)\
    .outerjoin(
        Feature,
        (Feature.subgraph_id == Subgraph.subgraph_id) &
        (Feature.version == session.query(func.max(Feature.version))
            .filter(Feature.subgraph_id == Subgraph.subgraph_id)
            .scalar_subquery())
    )\
    .filter(Subgraph.subgraph_id == "UP01")\
    .first()

# 访问特征数据
if subgraph_with_feature.features:
    latest_feature = subgraph_with_feature.features[0]
    print(f"厚度: {latest_feature.thickness_mm}")
    print(f"俯视图线割长度: {latest_feature.top_view_wire_length}")
    print(f"加工说明: {latest_feature.processing_instructions}")
```

#### 3.3.2 查询子图的所有历史版本
```python
# 查询某个子图的所有特征版本
feature_history = session.query(Feature)\
    .filter(Feature.subgraph_id == "UP01")\
    .order_by(Feature.version.desc())\
    .all()

for feature in feature_history:
    print(f"版本{feature.version}: 厚度={feature.thickness_mm}, 创建时间={feature.created_at}")
```

#### 3.3.3 查询不完整的特征
```python
# 查询特征数据不完整的子图
incomplete_features = session.query(Feature)\
    .filter(Feature.is_complete == False)\
    .filter(Feature.version == session.query(func.max(Feature.version))
        .filter(Feature.subgraph_id == Feature.subgraph_id)
        .scalar_subquery())\
    .all()

for feature in incomplete_features:
    print(f"子图ID: {feature.subgraph_id}")
    print(f"缺失参数: {feature.missing_params}")
```

#### 3.3.4 查询加工说明（JSONB）
```python
# 查询需要热处理的子图
features_need_heat_treatment = session.query(Feature)\
    .filter(Feature.needs_heat_treatment == True)\
    .all()

# 查询加工说明中包含特定内容的子图
features_with_drilling = session.query(Feature)\
    .filter(Feature.processing_instructions['drilling']['required'].astext == 'true')\
    .all()
```

## 四、实施计划

### 4.1 数据库迁移

#### 阶段1：创建features表（1天）
- [ ] 编写SQL脚本创建features表
- [ ] 创建索引和唯一约束
- [ ] 测试版本号自动递增
- [ ] 测试JSONB字段查询

#### 阶段2：修改subgraphs表（1天）
- [ ] 添加subgraph_file_url字段
- [ ] 移除特征相关字段（备份后）
- [ ] 验证数据完整性
- [ ] 更新相关索引

#### 阶段3：更新数据模型（1天）
- [ ] 更新shared/models.py
- [ ] 添加Feature模型
- [ ] 更新Subgraph模型
- [ ] 添加关系映射（一对多）

#### 阶段4：更新Agent代码（2天）
- [ ] 更新CAD Agent：插入features表，保存子图文件URL
- [ ] 更新Feature Recognition Agent：创建新版本的feature记录
- [ ] 更新Decision Agent：查询最新版本的features
- [ ] 更新Pricing Agent：通过JOIN获取特征数据
- [ ] 更新Interaction Agent：处理特征数据

#### 阶段5：测试与验证（1天）
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 数据一致性测试
- [ ] 版本管理测试

### 4.2 总工期
**6天**（1人全职）

### 4.3 负责人
**人员A（数据库与基础设施工程师）**

## 五、测试计划

### 5.1 单元测试

#### 测试用例1：插入特征数据
```python
def test_insert_feature():
    feature = Feature(
        subgraph_id="UP01",
        job_id=job_id,
        version=1,
        feature_type="WIRE",
        thickness_mm=25.5,
        top_view_wire_length=150.0,
        front_view_wire_length=80.0,
        side_view_wire_length=60.0,
        has_auto_material=True,
        needs_heat_treatment=False,
        confidence=0.95,
        recognition_method="layer",
        is_complete=True,
        processing_instructions={
            "wire_cutting": {
                "method": "slow_wire",
                "passes": "cut1_trim1"
            }
        }
    )
    session.add(feature)
    session.commit()
    
    assert feature.feature_id is not None
    assert feature.version == 1
```

#### 测试用例2：创建新版本
```python
def test_create_new_version():
    # 创建第一个版本
    feature_v1 = Feature(
        subgraph_id="UP01",
        job_id=job_id,
        version=1,
        feature_type="WIRE",
        thickness_mm=25.5
    )
    session.add(feature_v1)
    session.commit()
    
    # 创建第二个版本
    feature_v2 = Feature(
        subgraph_id="UP01",
        job_id=job_id,
        version=2,
        feature_type="WIRE",
        thickness_mm=30.0
    )
    session.add(feature_v2)
    session.commit()
    
    # 查询所有版本
    versions = session.query(Feature)\
        .filter_by(subgraph_id="UP01")\
        .order_by(Feature.version)\
        .all()
    
    assert len(versions) == 2
    assert versions[0].version == 1
    assert versions[1].version == 2
```

#### 测试用例3：查询最新版本
```python
def test_query_latest_version():
    latest_feature = session.query(Feature)\
        .filter_by(subgraph_id="UP01")\
        .order_by(Feature.version.desc())\
        .first()
    
    assert latest_feature.version == 2
    assert latest_feature.thickness_mm == 30.0
```

### 5.2 集成测试

#### 测试用例4：端到端流程
1. 上传DWG文件
2. CAD Agent提取特征并插入features表（version=1）
3. 保存子图文件URL到subgraphs表
4. 用户请求重新识别
5. Feature Recognition Agent创建新版本（version=2）
6. Decision Agent查询最新版本进行工艺决策
7. Pricing Agent通过JOIN获取特征数据计算价格
8. 验证数据一致性

### 5.3 性能测试

#### 测试用例5：查询性能对比
- 测试1：查询subgraphs（不JOIN features）
- 测试2：查询subgraphs + JOIN最新版本的features
- 测试3：查询subgraphs + JOIN所有版本的features
- 对比查询时间

#### 测试用例6：并发插入测试
- 并发插入100个特征记录
- 验证版本号是否正确递增
- 验证数据一致性

## 六、风险与缓解措施

### 6.1 风险1：JOIN查询性能问题
**缓解措施**：
- 创建复合索引(subgraph_id, version DESC)
- 使用子查询优化最新版本查询
- 考虑使用物化视图缓存最新版本
- 监控查询性能，必要时添加缓存

### 6.2 风险2：版本号管理复杂
**缓解措施**：
- 使用应用层逻辑自动计算下一个版本号
- 添加唯一约束防止版本号冲突
- 提供辅助函数简化版本号管理

### 6.3 风险3：JSONB查询性能
**缓解措施**：
- 创建GIN索引
- 对常用查询字段创建表达式索引
- 考虑将高频查询字段提升为普通列

### 6.4 风险4：历史版本数据膨胀
**缓解措施**：
- 设置版本保留策略（如只保留最近10个版本）
- 定期归档旧版本数据
- 提供版本清理工具

## 七、验收标准

### 7.1 功能验收
- [ ] features表创建成功
- [ ] subgraphs表修改完成
- [ ] 版本号管理正常工作
- [ ] Agent代码更新完成
- [ ] 所有测试用例通过
- [ ] 子图文件URL正确保存

### 7.2 性能验收
- [ ] 查询最新版本时间 < 50ms
- [ ] JOIN查询时间 < 100ms
- [ ] JSONB查询时间 < 100ms
- [ ] 并发插入性能无明显下降

### 7.3 文档验收
- [ ] 数据库ER图更新
- [ ] API文档更新
- [ ] 数据迁移文档完成
- [ ] 运维文档更新

## 八、后续优化

### 8.1 短期优化（1-2周）
- 监控JSONB查询性能，必要时创建表达式索引
- 优化最新版本查询，考虑使用物化视图
- 添加版本清理定时任务

### 8.2 长期优化（1-3个月）
- 考虑将高频查询的加工说明提升为普通列
- 考虑使用分区表优化大数据量查询
- 实现版本对比和回滚功能

## 九、相关文档

- [数据库ER图](../docs/数据库ER图.md)
- [需求文档](../../模具成本核算系统-需求文档.md)
- [技术方案](../docs/模具成本核算系统-详细技术方案.md)
- [数据模型](../shared/models.py)
- [数据库初始化脚本](../infrastructure/init-db.sql)
