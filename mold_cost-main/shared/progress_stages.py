"""
进度阶段常量定义
负责人：架构组
"""

class ProgressStage:
    """进度阶段常量"""
    
    # 初始化
    INITIALIZING = "initializing"
    
    # CAD拆图
    CAD_SPLIT_STARTED = "cad_split_started"
    CAD_SPLIT_COMPLETED = "cad_split_completed"
    CAD_SPLIT_FAILED = "cad_split_failed"
    
    # 特征识别
    FEATURE_RECOGNITION_STARTED = "feature_recognition_started"
    FEATURE_RECOGNITION_COMPLETED = "feature_recognition_completed"
    FEATURE_RECOGNITION_FAILED = "feature_recognition_failed"
    
    # 等待用户确认
    WAITING_FOR_CONFIRMATION = "awaiting_confirm"
    
    # NC时间计算
    NC_CALCULATION_STARTED = "nc_calculation_started"
    NC_CALCULATION_COMPLETED = "nc_calculation_completed"
    NC_CALCULATION_FAILED = "nc_calculation_failed"
    DECISION_FAILED = "decision_failed"
    
    # 价格计算
    PRICING_STARTED = "pricing_started"
    PRICING_COMPLETED = "pricing_completed"
    PRICING_FAILED = "pricing_failed"
    
    # 完成/失败
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressPercent:
    """进度百分比常量"""
    
    # 初始化
    INITIALIZING = 0
    
    # CAD拆图
    CAD_SPLIT_STARTED = 5
    CAD_SPLIT_COMPLETED = 20
    
    # 特征识别
    FEATURE_RECOGNITION_STARTED = 25
    FEATURE_RECOGNITION_COMPLETED = 50
    
    # NC时间计算
    NC_CALCULATION_STARTED = 55
    NC_CALCULATION_COMPLETED = 70
    
    # 价格计算
    PRICING_STARTED = 75
    PRICING_COMPLETED = 90
    
    # 完成
    COMPLETED = 100
