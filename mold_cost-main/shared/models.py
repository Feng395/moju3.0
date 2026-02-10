"""
数据库模型
负责人：人员A
"""
from sqlalchemy import Column, String, Integer, DECIMAL, TIMESTAMP, Boolean, Text, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base

class Job(Base):
    """任务表"""
    __tablename__ = "jobs"
    
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # DWG文件信息
    dwg_file_id = Column(String(100))
    dwg_file_name = Column(String(255))
    dwg_file_path = Column(String(500))
    dwg_file_size = Column(Integer)
    
    # PRT文件信息
    prt_file_id = Column(String(100))
    prt_file_name = Column(String(255))
    prt_file_path = Column(String(500))
    prt_file_size = Column(Integer)
    
    # 任务状态
    status = Column(String(20), nullable=False, default="pending")
    current_stage = Column(String(50))
    progress = Column(Integer, default=0)
    total_subgraphs = Column(Integer, default=0)
    
    # 成本汇总
    total_cost = Column(DECIMAL(12, 2))
    currency = Column(String(10), default="CNY")
    processes_used = Column(ARRAY(Text))
    
    # 各工艺成本
    material_cost = Column(DECIMAL(12, 2))
    heat_treatment_cost = Column(DECIMAL(12, 2))
    fast_wire_cost = Column(DECIMAL(12, 2))
    mid_wire_cost = Column(DECIMAL(12, 2))
    slow_wire_cost = Column(DECIMAL(12, 2))
    nc_cost = Column(DECIMAL(12, 2))
    grinding_cost = Column(DECIMAL(12, 2))
    edm_cost = Column(DECIMAL(12, 2))
    processing_cost_total = Column(DECIMAL(12, 2))
    
    # 版本锁定（快照模式）
    price_version_locked = Column(String(20))
    process_version_locked = Column(String(20))
    snapshot_created_at = Column(TIMESTAMP)
    
    # 报表
    report_id = Column(String(100))
    
    # 时间戳
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(TIMESTAMP)
    archived_at = Column(TIMESTAMP)
    
    # 其他
    error_message = Column(Text)
    # extra_data = Column(JSONB)  # 暂时注释，数据库中没有此字段
    
    # 关系定义
    subgraphs = relationship("Subgraph", back_populates="job", lazy="select")

class Subgraph(Base):
    """子图表 - 存储业务数据和成本数据"""
    __tablename__ = "subgraphs"
    
    subgraph_id = Column(String(50), primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"), nullable=False)
    
    # 基本信息
    part_name = Column(String(100))
    part_code = Column(String(100))
    # material 字段不存在于数据库中，材质信息在 features 表
    subgraph_file_url = Column(String(500))
    
    # 业务数据
    weight_kg = Column(DECIMAL(10, 3))
    
    # 材料和热处理
    material_unit_price = Column(DECIMAL(10, 2))
    material_cost = Column(DECIMAL(12, 2))
    heat_treatment_unit_price = Column(DECIMAL(10, 2))
    heat_treatment_cost = Column(DECIMAL(12, 2))
    
    # 工艺说明
    process_description = Column(String(200))
    
    # 加工时间
    nc_roughing_time = Column(DECIMAL(10, 2))
    nc_milling_time = Column(DECIMAL(10, 2))
    drilling_time = Column(DECIMAL(10, 2))
    milling_machine_time = Column(DECIMAL(10, 2))
    large_grinding_time = Column(DECIMAL(10, 2))
    small_grinding_count = Column(Integer)
    edm_time = Column(DECIMAL(10, 2))
    engraving_time = Column(DECIMAL(10, 2))
    
    # 线割长度
    slow_wire_length = Column(DECIMAL(12, 3))
    slow_wire_side_length = Column(DECIMAL(12, 3))
    mid_wire_length = Column(DECIMAL(12, 3))
    fast_wire_length = Column(DECIMAL(12, 3))
    
    # 单独项
    separate_item = Column(String(200))
    
    # 费用
    total_cost = Column(DECIMAL(12, 2))
    wire_process_note = Column(Text)
    nc_roughing_cost = Column(DECIMAL(12, 2))
    nc_milling_cost = Column(DECIMAL(12, 2))
    drilling_cost = Column(DECIMAL(12, 2))
    milling_machine_cost = Column(DECIMAL(12, 2))
    large_grinding_cost = Column(DECIMAL(12, 2))
    small_grinding_cost = Column(DECIMAL(12, 2))
    slow_wire_cost = Column(DECIMAL(12, 2))
    slow_wire_side_cost = Column(DECIMAL(12, 2))
    mid_wire_cost = Column(DECIMAL(12, 2))
    fast_wire_cost = Column(DECIMAL(12, 2))
    edm_cost = Column(DECIMAL(12, 2))
    engraving_cost = Column(DECIMAL(12, 2))
    separate_item_cost = Column(DECIMAL(12, 2))
    processing_cost_total = Column(DECIMAL(12, 2))
    
    # 工艺决策
    applied_snapshot_ids = Column(ARRAY(Text))
    rule_reason = Column(Text)
    override_by_user = Column(Boolean, default=False)
    cost_calculation_method = Column(String(20))
    
    # 扩展功能
    has_sheet_line = Column(Boolean, default=False)
    sheet_area_mm2 = Column(DECIMAL(12, 3))
    sheet_perimeter_mm = Column(DECIMAL(12, 3))
    sheet_line_data = Column(JSONB)
    has_single_nc_calc = Column(Boolean, default=False)
    single_prt_file = Column(String(500))
    process_changed = Column(Boolean, default=False)
    original_process = Column(String(20))
    prt_3d_file = Column(String(500))
    
    # 重算
    recalc_count = Column(Integer, default=0)
    last_recalc_at = Column(TIMESTAMP)
    last_recalc_by = Column(String(50))
    
    # 状态
    status = Column(String(20), default='pending')
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 数据库中实际存在的字段
    # 注意: 'metadata' 是 SQLAlchemy 保留字段,使用 'meta_data' 作为属性名映射到数据库的 'metadata' 列
    meta_data = Column('metadata', JSONB)
    wire_process = Column(String(255))
    
    # 关系定义
    job = relationship("Job", back_populates="subgraphs")

class Feature(Base):
    """特征表 - 存储从CAD提取的原始特征数据，支持历史版本"""
    __tablename__ = "features"
    
    feature_id = Column(Integer, primary_key=True, autoincrement=True)
    subgraph_id = Column(String(50), ForeignKey("subgraphs.subgraph_id"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    
    # 几何特征（从CAD提取）
    length_mm = Column(DECIMAL(10, 2))
    width_mm = Column(DECIMAL(10, 2))
    thickness_mm = Column(DECIMAL(10, 3))
    quantity = Column(Integer, default=1)
    material = Column(String(50))
    heat_treatment = Column(String(100))
    calculated_weight_kg = Column(DECIMAL(10, 3))
    
    # 三个视图的线割长度
    top_view_wire_length = Column(DECIMAL(10, 3))
    front_view_wire_length = Column(DECIMAL(10, 3))
    side_view_wire_length = Column(DECIMAL(10, 3))
    
    # 三个视图的线割长度
    top_view_wire_length = Column(DECIMAL(10, 3))
    front_view_wire_length = Column(DECIMAL(10, 3))
    side_view_wire_length = Column(DECIMAL(10, 3))
    
    # 加工特征
    has_auto_material = Column(Boolean, default=False)
    needs_heat_treatment = Column(Boolean, default=False)
    boring_length_mm = Column(DECIMAL(10, 3))
    slider_angle = Column(String(255))
    boring_num = Column(Integer)
    # boring_outer = Column(String(255))  # 数据库中不存在此字段
    # borehole = Column(String(255))  # 已移除，数据库表中不存在此列
    # area_num = Column(JSONB)  # 已移除，数据存储在 metadata 中
    
    # NC 时间详细数据
    nc_time_cost = Column(JSONB)  # 格式: {"nc_details": [{"code": "L", "value": "5"}, {"code": "ZXZ", "value": "5"}, {"code": "开粗", "value": "5"}, {"code": "精铣", "value": "5"}]}
    
    # 加工说明（JSON格式，包含所有提取到的加工说明）
    processing_instructions = Column(JSONB)
    
    # 识别信息
    is_complete = Column(Boolean, default=False)
    missing_params = Column(ARRAY(String))
    
    # 扩展特征（数据库中不存在此列，已移除）
    # extended_features = Column(JSONB)
    
    # 元数据
    meta_data = Column('metadata', JSONB)
    created_by = Column(String(50))
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

class PriceItem(Base):
    """价格项表（全局模板）"""
    __tablename__ = "price_items"
    
    id = Column(String(50), primary_key=True)
    version_id = Column(String(20), nullable=False)
    feature_type = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    unit_price = Column(DECIMAL(10, 4), nullable=False)
    unit = Column(String(20), nullable=False)
    param_conditions = Column(JSONB)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50))
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    # extra_data = Column(JSONB)  # 暂时注释，数据库中没有此字段

class ProcessRule(Base):
    """工艺规则表（全局模板）"""
    __tablename__ = "process_rules"
    
    id = Column(String(50), primary_key=True)
    version_id = Column(String(20), nullable=False)
    feature_type = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    conditions = Column(JSONB, nullable=False)
    output_params = Column(JSONB, nullable=False)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50))
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class JobPriceSnapshot(Base):
    """任务价格快照表"""
    __tablename__ = "job_price_snapshots"
    
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"), nullable=False)
    
    # 从price_items复制的字段
    original_price_id = Column(String(50))
    version_id = Column(String(20), nullable=False)
    feature_type = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    unit_price = Column(DECIMAL(10, 4), nullable=False)
    unit = Column(String(20), nullable=False)
    param_conditions = Column(JSONB)
    priority = Column(Integer, default=0)
    
    # 快照特有字段
    is_modified = Column(Boolean, default=False)
    modified_by = Column(String(50))
    modified_at = Column(TIMESTAMP)
    modification_reason = Column(Text)
    
    # 审计字段
    snapshot_created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    snapshot_metadata = Column(JSONB)

class JobProcessSnapshot(Base):
    """任务工艺快照表"""
    __tablename__ = "job_process_snapshots"
    
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"), nullable=False)
    
    # 从process_rules复制的字段
    original_rule_id = Column(String(50))
    version_id = Column(String(20), nullable=False)
    feature_type = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    conditions = Column(JSONB, nullable=False)
    output_params = Column(JSONB, nullable=False)
    priority = Column(Integer, default=0)
    
    # 快照特有字段
    is_modified = Column(Boolean, default=False)
    modified_by = Column(String(50))
    modified_at = Column(TIMESTAMP)
    modification_reason = Column(Text)
    
    # 审计字段
    snapshot_created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    snapshot_metadata = Column(JSONB)

class OperationLog(Base):
    """操作日志表 - 记录所有 Agent 的操作审计"""
    __tablename__ = "operation_logs"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"), nullable=False)
    subgraph_id = Column(String(50), ForeignKey("subgraphs.subgraph_id"))
    
    # Agent 信息
    agent = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    
    # 输入输出
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    
    # 执行结果
    status = Column(String(20), nullable=False)
    duration_ms = Column(Integer)
    error_message = Column(Text)
    
    # 时间戳
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    # 扩展数据
    # extra_data = Column(JSONB)  # 暂时注释，数据库中没有此字段

# 其他模型类...
