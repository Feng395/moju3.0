"""
Agent 输入/输出类型定义
负责人：架构组
版本：v1.0
"""
from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


# ========== 枚举类型 ==========

class JobStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class StageStatus(str, Enum):
    """阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentStatus(str, Enum):
    """Agent 执行状态"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


# ========== OrchestratorState 类型定义 ==========

class StageHistoryItem(TypedDict):
    """阶段历史记录项"""
    stage: str
    status: str  # StageStatus
    started_at: str  # ISO8601
    completed_at: Optional[str]  # ISO8601
    duration_ms: Optional[int]


class ErrorItem(TypedDict):
    """错误记录项"""
    stage: str
    agent: str
    error_code: str
    message: str
    timestamp: str  # ISO8601
    is_retryable: bool
    retry_count: int


class OrchestratorState(TypedDict):
    """
    LangGraph State Schema
    
    使用示例:
    ```python
    state: OrchestratorState = {
        "job_id": "...",
        "user_id": "...",
        ...
    }
    ```
    """

# ========== AgentContext 类型定义 ==========

class AgentContext(TypedDict):
    """
    Agent.process(context) 的输入参数标准
    
    使用示例:
    ```python
    def _build_context(state: OrchestratorState) -> AgentContext:
        return {
            "job_id": state["job_id"],
            ...
        }
    ```
    """

# ========== RabbitMQ 消息类型 ==========

class JobTriggerMessage(TypedDict):
    """任务触发消息（从 RabbitMQ 消费）"""
    job_id: str
    user_id: str
    created_at: str  # ISO8601
    trigger_source: Optional[str]  # "user_upload" | "retry" | "manual_recalc"
    priority: Optional[int]  # 0-9
    context_hints: Optional[Dict[str, Any]]


class RecalcMessage(TypedDict):
    """重算任务消息"""
    job_id: str
    user_id: str
    recalc_type: str  # "partial" | "full"
    recalc_scope: List[str]  # Agent 名称列表
    trigger_by: str  # "user_manual" | "system_auto"
    created_at: str  # ISO8601


# ========== Agent 输出数据结构 ==========

class SubgraphData(TypedDict):
    """子图数据结构（CADAgent 输出）"""
    subgraph_id: str
    part_name: str
    part_code: Optional[str]
    subgraph_file_url: str
    geometry: Dict[str, float]  # length_mm, width_mm, thickness_mm, volume_mm3, weight_kg
    raw_features: Optional[Dict[str, Any]]


class FeatureData(TypedDict):
    """特征数据结构（FeatureExtractionAgent 输出）"""
    subgraph_id: str
    feature_id: str
    length_mm: float
    width_mm: float
    thickness_mm: float
    volume_mm3: float
    weight_kg: float
    material: Optional[str]
    heat_treatment: Optional[str]
    needs_heat_treatment: bool
    wire_lengths: Dict[str, float]  # top_view, front_view, side_view
    processing_instructions: List[str]
    is_complete: bool
    missing_params: List[str]


class MatchedRule(TypedDict):
    """匹配的工艺规则（DecisionAgent 输出）"""
    rule_snapshot_id: int
    rule_name: str
    match_score: float
    conditions_met: List[str]


# class ProcessDecision(TypedDict):
#     """工艺决策（DecisionAgent 输出）"""
#     subgraph_id: str
#     selected_processes: List[str]
#     matched_rules: List[MatchedRule]
#     output_params: Dict[str, Any]
#     alternative_processes: Optional[List[Dict[str, Any]]]


class MatchedPriceItem(TypedDict):
    """匹配的价格项（PricingAgent 输出）"""
    price_snapshot_id: int
    name: str
    unit_price: float
    unit: str
    quantity: float
    subtotal: float


class SubgraphPricing(TypedDict):
    """子图定价（PricingAgent 输出）"""
    subgraph_id: str
    cost_breakdown: Dict[str, float]
    matched_price_items: List[MatchedPriceItem]


class ArtifactData(TypedDict):
    """生成的工件数据"""
    artifact_id: str
    artifact_type: str  # "report_pdf" | "nc_program" | "cad_model"
    file_name: str
    storage_path: str
    file_size_bytes: int
    created_at: str  # ISO8601


# ========== Agent 依赖配置 ==========

class AgentDependencyConfig(TypedDict):
    """Agent 依赖配置"""
    depends_on: List[str]  # 依赖的 Agent 名称列表
    required: bool  # 是否必须执行
    timeout_seconds: int
    retry_policy: Optional[Dict[str, Any]]
    requires_data: Optional[List[str]]  # 需要的数据字段
    requires_snapshots: Optional[List[str]]  # 需要的快照类型


# ========== 标准错误码 ==========

class ErrorCode:
    """标准错误码常量"""
    # 系统错误
    TIMEOUT = "TIMEOUT"
    MCP_SERVICE_UNAVAILABLE = "MCP_SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # 业务错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_PARSE_ERROR = "FILE_PARSE_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    FEATURE_EXTRACTION_INCOMPLETE = "FEATURE_EXTRACTION_INCOMPLETE"
    
    # 数据错误
    SNAPSHOT_NOT_FOUND = "SNAPSHOT_NOT_FOUND"
    PRICE_ITEM_NOT_FOUND = "PRICE_ITEM_NOT_FOUND"
    PROCESS_RULE_NOT_FOUND = "PROCESS_RULE_NOT_FOUND"


# ========== 错误处理策略 ==========

RETRYABLE_ERRORS = {
    ErrorCode.TIMEOUT,
    ErrorCode.MCP_SERVICE_UNAVAILABLE,
    ErrorCode.DATABASE_ERROR
}

NON_RETRYABLE_ERRORS = {
    ErrorCode.FILE_NOT_FOUND,
    ErrorCode.FILE_PARSE_ERROR,
    ErrorCode.INVALID_INPUT,
    ErrorCode.SNAPSHOT_NOT_FOUND
}

PARTIAL_SUCCESS_ERRORS = {
    ErrorCode.FEATURE_EXTRACTION_INCOMPLETE
}


# ========== 工具函数 ==========

def is_retryable_error(error_code: str) -> bool:
    """判断错误是否可重试"""
    return error_code in RETRYABLE_ERRORS


def validate_agent_context(context: Dict[str, Any]) -> bool:
    """验证 AgentContext 必填字段"""
    required_keys = ["job_id", "session_id", "agent_execution_id"]
    return all(k in context for k in required_keys)


def extract_upstream_output(
    context: AgentContext,
    agent_name: str,
    data_key: Optional[str] = None
) -> Optional[Any]:
    """
    从上游 Agent 输出中提取数据
    
    Args:
        context: Agent 输入上下文
        agent_name: 上游 Agent 名称
        data_key: 数据字段名（如果为 None，返回整个 data）
    
    Returns:
        提取的数据，如果不存在返回 None
    
    使用示例:
    ```python
    subgraphs = extract_upstream_output(context, "CADAgent", "subgraphs")
    ```
    """
    upstream = context["upstream_outputs"].get(agent_name)
    if not upstream or upstream.get("status") != "ok":
        return None
    
    data = upstream.get("data", {})
    if data_key:
        return data.get(data_key)
    return data


def build_execution_id(agent_name: str) -> str:
    """
    生成 Agent 执行ID
    
    格式: exec_{agent_name}_{timestamp}
    """
    timestamp = int(datetime.utcnow().timestamp())
    return f"exec_{agent_name}_{timestamp}"


def build_session_id() -> str:
    """
    生成编排会话ID
    
    格式: sess_YYYYMMDD_HHMMSS
    """
    now = datetime.utcnow()
    return f"sess_{now.strftime('%Y%m%d_%H%M%S')}"
