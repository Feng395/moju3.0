# Agent 输入/输出格式规范

> **版本**: v1.0  
> **更新日期**: 2026-01-12  
> **适用范围**: 所有继承自 `BaseAgent` 的 Agent 实现

---

## 一、总体架构

```
RabbitMQ 消息 → OrchestratorAgent → 各 Agent → 返回 OpResult → 更新 State
                     ↓
                 StateGraph
            (状态管理 + 流程编排)
```

**核心原则**：
- ✅ Agent 之间**不直接通信**，通过 State 共享数据
- ✅ 所有 Agent 继承 `BaseAgent`，实现 `process()` 方法
- ✅ 统一返回 `OpResult` 对象
- ✅ 编排器负责依赖管理和错误处理

---

## 二、RabbitMQ 消息格式（队列触发）

### 2.1 任务触发消息

**队列名称**: `job_processing`

**消息结构**:
```python
{
    "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  # UUID 字符串
    "user_id": "user_789",                             # 用户ID
    "created_at": "2026-01-12T10:15:30.123456",       # ISO8601 时间戳
    
    # 可选字段
    "trigger_source": "user_upload",  # "user_upload" | "retry" | "manual_recalc"
    "priority": 5,                    # 0-9，默认 5
    "context_hints": {                # 业务上下文提示（可选）
        "job_type": "new_mold",       # "new_mold" | "modify_mold"
        "require_nc_calc": true        # 是否需要 NC 计算
    }
}
```

### 2.2 重算任务消息

**队列名称**: `recalculation_queue`

**消息结构**:
```python
{
    "job_id": "a1b2c3d4-...",
    "user_id": "user_789",
    "recalc_type": "partial",         # "partial" | "full"
    "recalc_scope": ["pricing"],      # 需要重新执行的 Agent 列表
    "trigger_by": "user_manual",      # "user_manual" | "system_auto"
    "created_at": "2026-01-12T10:15:30.123456"
}
```

---

## 三、OrchestratorState 结构（LangGraph State）

### 3.1 State 类型定义

```python
from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime

class OrchestratorState(TypedDict):
    """LangGraph State Schema"""
    
    # ========== 核心标识 ==========
    job_id: str                          # Job UUID
    user_id: str                         # 用户ID
    session_id: str                      # 本次编排会话ID（格式: sess_YYYYMMDD_NNN）
    execution_start_time: str            # ISO8601 时间戳
    
    # ========== Job 元信息（从数据库读取，只读）==========
    job_metadata: Dict[str, Any]
    # {
    #   "dwg_file_path": str,
    #   "dwg_file_name": str,
    #   "prt_file_path": str,
    #   "prt_file_name": str,
    #   "status": str,
    #   "created_at": str,
    #   "job_parameters": {...}  # 用户提交的参数
    # }
    
    # ========== 快照引用（从 Job 表读取）==========
    snapshot_refs: Dict[str, Any]
    # {
    #   "price_version_locked": str,       # 如 "v1.0"
    #   "process_version_locked": str,     # 如 "v1.0"
    #   "snapshot_created_at": str         # ISO8601 时间戳
    # }
    
    # ========== 工作流控制 ==========
    current_stage: str                   # 当前阶段: "initializing" | "cad_parsing" | ...
    progress: int                        # 进度 0-100
    stage_history: List[Dict[str, Any]]  # 阶段执行历史
    # [
    #   {
    #     "stage": "cad_parsing",
    #     "status": "completed",  # "pending" | "running" | "completed" | "failed" | "skipped"
    #     "started_at": "2026-01-12T10:16:00.000Z",
    #     "completed_at": "2026-01-12T10:16:15.000Z",
    #     "duration_ms": 15000
    #   }
    # ]
    
    # ========== Agent 输出收集器 ==========
    agent_outputs: Dict[str, Dict[str, Any]]
    # Key: Agent名称 (如 "CADAgent", "PricingAgent")
    # Value: OpResult.to_dict() 的结果
    # 示例:
    # {
    #   "CADAgent": {
    #     "status": "ok",
    #     "data": {...},
    #     "message": "成功拆分为 5 个子图",
    #     "timestamp": "2026-01-12T10:16:15.000Z",
    #     ...
    #   }
    # }
    
    # ========== 业务数据累积（跨 Agent 共享）==========
    subgraphs: List[Dict[str, Any]]      # CAD 拆图结果
    features: List[Dict[str, Any]]       # 特征提取结果
    nc_time_results: Optional[Dict]      # NC 时间计算结果
    pricing_results: Optional[Dict]      # 定价结果
    report_artifact: Optional[Dict]      # 报表生成结果
    
    # ========== 交互控制 ==========
    missing_params: List[str]            # 缺失参数列表 ["material", "heat_treatment"]
    requires_user_input: bool            # 是否需要等待用户输入
    user_input_data: Optional[Dict]      # 用户提交的补充数据
    
    # ========== 错误与重试 ==========
    errors: List[Dict[str, Any]]         # 错误列表
    # [
    #   {
    #     "stage": "cad_parsing",
    #     "agent": "CADAgent",
    #     "error_code": "FILE_PARSE_ERROR",
    #     "message": "无法解析 DWG 文件",
    #     "timestamp": "2026-01-12T10:16:10.000Z",
    #     "is_retryable": true,
    #     "retry_count": 0
    #   }
    # ]
    
    # ========== 扩展元数据 ==========
    metadata: Dict[str, Any]             # 自定义元数据
```

### 3.2 State 初始化示例

```python
def _initialize_state(self, mq_message: Dict[str, Any], job: Job) -> OrchestratorState:
    """从 RabbitMQ 消息和数据库 Job 初始化 State"""
    return {
        "job_id": mq_message["job_id"],
        "user_id": mq_message["user_id"],
        "session_id": f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "execution_start_time": datetime.utcnow().isoformat(),
        
        "job_metadata": {
            "dwg_file_path": job.dwg_file_path,
            "dwg_file_name": job.dwg_file_name,
            "prt_file_path": job.prt_file_path,
            "prt_file_name": job.prt_file_name,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "job_parameters": job.metadata or {}
        },
        
        "snapshot_refs": {
            "price_version_locked": job.price_version_locked,
            "process_version_locked": job.process_version_locked,
            "snapshot_created_at": job.snapshot_created_at.isoformat() if job.snapshot_created_at else None
        },
        
        "current_stage": "initializing",
        "progress": 0,
        "stage_history": [],
        
        "agent_outputs": {},
        
        "subgraphs": [],
        "features": [],
        "nc_time_results": None,
        "pricing_results": None,
        "report_artifact": None,
        
        "missing_params": [],
        "requires_user_input": False,
        "user_input_data": None,
        
        "errors": [],
        "metadata": mq_message.get("context_hints", {})
    }
```

---

## 四、Agent 输入格式（process 方法的 context 参数）

### 4.1 AgentContext 标准结构

```python
class AgentContext(TypedDict):
    """Agent.process(context) 的输入参数标准"""
    
    # ========== 必填字段 ==========
    job_id: str                          # Job UUID
    session_id: str                      # 编排会话ID
    agent_execution_id: str              # 本次执行唯一ID（格式: exec_{agent}_{timestamp}）
    
    # ========== 上游 Agent 输出（依赖数据）==========
    upstream_outputs: Dict[str, Dict[str, Any]]
    # Key: 上游 Agent 名称
    # Value: OpResult.to_dict()
    # 示例:
    # {
    #   "CADAgent": {
    #     "status": "ok",
    #     "data": {"subgraphs": [...]},
    #     "message": "成功拆分为 5 个子图"
    #   }
    # }
    
    # ========== 快照引用 ==========
    snapshot_refs: Dict[str, Any]
    # 包含 price_version_locked, process_version_locked
    # Agent 根据 version 去查询 job_price_snapshots / job_process_snapshots
    
    # ========== Job 元信息（只读）==========
    job_metadata: Dict[str, Any]
    # 包含文件路径、用户参数等
    
    # ========== 业务数据（按需传递）==========
    subgraphs: Optional[List[Dict]]      # 子图数据（如果该 Agent 需要）
    features: Optional[List[Dict]]       # 特征数据（如果该 Agent 需要）
    
    # ========== Agent 特定参数 ==========
    agent_parameters: Dict[str, Any]
    # 编排器传给该 Agent 的配置参数
    # 示例: {"timeout_seconds": 120, "parse_level": "detailed"}
    
    # ========== 控制指令 ==========
    directives: Dict[str, Any]
    # {
    #   "timeout_at": str,           # ISO8601 截止时间
    #   "priority": int,             # 优先级 0-9
    #   "retry_attempt": int,        # 当前是第几次重试（0 表示首次）
    #   "trace_context": {...}       # 分布式追踪上下文（预留）
    # }
```

### 4.2 编排器构造 Context 示例

```python
def _build_agent_context(
    self,
    state: OrchestratorState,
    agent_name: str,
    upstream_deps: List[str]
) -> AgentContext:
    """构造 Agent 输入 Context"""
    
    # 提取上游 Agent 输出
    upstream_outputs = {}
    for dep in upstream_deps:
        if dep in state["agent_outputs"]:
            upstream_outputs[dep] = state["agent_outputs"][dep]
    
    return {
        "job_id": state["job_id"],
        "session_id": state["session_id"],
        "agent_execution_id": f"exec_{agent_name}_{int(datetime.now().timestamp())}",
        
        "upstream_outputs": upstream_outputs,
        "snapshot_refs": state["snapshot_refs"],
        "job_metadata": state["job_metadata"],
        
        "subgraphs": state.get("subgraphs"),
        "features": state.get("features"),
        
        "agent_parameters": self._get_agent_parameters(agent_name),
        
        "directives": {
            "timeout_at": (datetime.utcnow() + timedelta(seconds=120)).isoformat(),
            "priority": 5,
            "retry_attempt": 0,
            "trace_context": {}
        }
    }
```

---

## 五、Agent 输出格式（OpResult 增强）

### 5.1 OpResult 类增强定义

```python
from datetime import datetime
from typing import Dict, Any, Optional, List

class OpResult:
    """Agent 操作结果（标准化版本）"""
    
    def __init__(
        self,
        status: str,                          # "ok" | "warning" | "error" | "skipped"
        data: Optional[Dict[str, Any]] = None,
        message: str = "",
        refs: Optional[Dict[str, Any]] = None,
        
        # ========== 标准字段 ==========
        agent_name: Optional[str] = None,     # Agent 名称
        agent_version: str = "1.0.0",         # Agent 版本
        execution_id: Optional[str] = None,   # 执行ID
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        
        # ========== 质量元数据 ==========
        confidence_score: float = 1.0,        # 结果置信度 0.0-1.0
        warnings: Optional[List[str]] = None, # 警告列表
        
        # ========== 错误详情（status="error" 时必填）==========
        error_code: Optional[str] = None,     # 标准错误码
        error_details: Optional[str] = None,  # 技术详情
        is_retryable: bool = False,           # 是否可重试
        
        # ========== 生成的工件 ==========
        artifacts: Optional[List[Dict]] = None
    ):
        self.status = status
        self.data = data or {}
        self.message = message
        self.refs = refs or {}
        self.timestamp = datetime.utcnow()
        
        self.agent_name = agent_name
        self.agent_version = agent_version
        self.execution_id = execution_id
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at or datetime.utcnow()
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        
        self.confidence_score = confidence_score
        self.warnings = warnings or []
        
        self.error_code = error_code
        self.error_details = error_details
        self.is_retryable = is_retryable
        
        self.artifacts = artifacts or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转为字典（用于存入 State 和数据库）"""
        return {
            "status": self.status,
            "data": self.data,
            "message": self.message,
            "refs": self.refs,
            "timestamp": self.timestamp.isoformat(),
            
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_ms": self.duration_ms,
            
            "confidence_score": self.confidence_score,
            "warnings": self.warnings,
            
            "error_code": self.error_code,
            "error_details": self.error_details,
            "is_retryable": self.is_retryable,
            
            "artifacts": self.artifacts
        }
```

### 5.2 标准错误码

| 错误码 | 分类 | 说明 | 可重试 |
|--------|------|------|--------|
| `TIMEOUT` | 系统 | 执行超时 | ✅ |
| `MCP_SERVICE_UNAVAILABLE` | 系统 | MCP 服务不可用 | ✅ |
| `FILE_NOT_FOUND` | 业务 | 文件不存在 | ❌ |
| `FILE_PARSE_ERROR` | 业务 | 文件解析失败 | ❌ |
| `INVALID_INPUT` | 业务 | 输入参数无效 | ❌ |
| `SNAPSHOT_NOT_FOUND` | 数据 | 快照数据不存在 | ❌ |
| `DATABASE_ERROR` | 系统 | 数据库错误 | ✅ |
| `FEATURE_EXTRACTION_INCOMPLETE` | 业务 | 特征提取不完整 | ⚠️ 部分成功 |

---

## 六、各 Agent 具体格式规范

### 6.1 CADAgent（CAD 解析）

#### 输入 Context
```python
{
    "job_id": "...",
    "session_id": "...",
    "agent_execution_id": "exec_CADAgent_1705056930",
    
    "upstream_outputs": {},  # 无上游依赖
    
    "snapshot_refs": {...},
    
    "job_metadata": {
        "dwg_file_path": "/uploads/job_xxx/drawing.dwg",
        "prt_file_path": "/uploads/job_xxx/part.prt"
    },
    
    "subgraphs": None,
    "features": None,
    
    "agent_parameters": {
        "parse_level": "detailed",  # "basic" | "detailed" | "full"
        "auto_split": true
    },
    
    "directives": {...}
}
```

#### 输出 OpResult.data
```python
{
    "subgraphs": [
        {
            "subgraph_id": "sub_001",
            "part_name": "芯子1",
            "part_code": "XZ001",
            "subgraph_file_url": "/exports/job_xxx/sub_001.dwg",
            "geometry": {
                "length_mm": 150.0,
                "width_mm": 100.0,
                "thickness_mm": 25.0,
                "volume_mm3": 375000.0,
                "weight_kg": 2.96  # 根据材料密度计算
            },
            "raw_features": {
                "layer_count": 5,
                "entity_count": 120
            }
        }
    ],
    "total_subgraphs": 5,
    "parsing_metadata": {
        "dwg_version": "2018",
        "parsing_method": "auto",
        "total_layers": 12
    }
}
```

#### 成功示例
```python
return OpResult(
    status="ok",
    data={...},  # 如上
    message=f"成功拆分为 {len(subgraphs)} 个子图",
    agent_name="CADAgent",
    agent_version="1.0.0",
    execution_id=context["agent_execution_id"],
    confidence_score=0.95
)
```

#### 失败示例
```python
return OpResult(
    status="error",
    message="DWG 文件解析失败",
    agent_name="CADAgent",
    execution_id=context["agent_execution_id"],
    error_code="FILE_PARSE_ERROR",
    error_details="DWG 版本不兼容，需要 2018 或更高版本",
    is_retryable=False
)
```

---

### 6.2 FeatureExtractionAgent（特征提取）

#### 输入 Context
```python
{
    "job_id": "...",
    "session_id": "...",
    "agent_execution_id": "exec_FeatureExtractionAgent_1705056945",
    
    "upstream_outputs": {
        "CADAgent": {
            "status": "ok",
            "data": {"subgraphs": [...]}
        }
    },
    
    "snapshot_refs": {...},
    "job_metadata": {...},
    
    "subgraphs": [...],  # 从 state 传入
    "features": None,
    
    "agent_parameters": {
        "extract_wire_length": true,
        "detect_heat_treatment": true
    },
    
    "directives": {...}
}
```

#### 输出 OpResult.data
```python
{
    "features": [
        {
            "subgraph_id": "sub_001",
            "feature_id": "feat_001",
            
            # 几何特征
            "length_mm": 150.0,
            "width_mm": 100.0,
            "thickness_mm": 25.0,
            "volume_mm3": 375000.0,
            "weight_kg": 2.96,
            
            # 材料和热处理
            "material": "SKD11",
            "heat_treatment": "HRC58-62",
            "needs_heat_treatment": true,
            
            # 线割长度（三个视图）
            "wire_lengths": {
                "top_view": 500.0,
                "front_view": 300.0,
                "side_view": 200.0
            },
            
            # 加工说明
            "processing_instructions": [
                "需要慢走丝加工",
                "孔径精度 ±0.01mm"
            ],
            
            # 完整性标记
            "is_complete": true,
            "missing_params": []
        }
    ],
    "total_features": 5
}
```

---

### 6.3 DecisionAgent（工艺决策）

#### 输入 Context
```python
{
    "job_id": "...",
    "upstream_outputs": {
        "FeatureExtractionAgent": {...}
    },
    "snapshot_refs": {
        "process_version_locked": "v1.0"
    },
    "subgraphs": [...],
    "features": [...],
    "agent_parameters": {
        "use_advanced_matching": true
    }
}
```

#### 输出 OpResult.data
```python
{
    "process_decisions": [
        {
            "subgraph_id": "sub_001",
            "selected_processes": ["slow_wire", "grinding"],
            
            "matched_rules": [
                {
                    "rule_snapshot_id": 10,  # job_process_snapshots 的 snapshot_id
                    "rule_name": "慢走丝标准工艺",
                    "match_score": 0.95,
                    "conditions_met": [
                        "thickness < 30mm",
                        "material == SKD11",
                        "precision_required == high"
                    ]
                }
            ],
            
            "output_params": {
                "slow_wire_length": 500.0,
                "slow_wire_side_length": 0.0,
                "grinding_time": 2.5,
                "estimated_total_time_hours": 8.5
            },
            
            "alternative_processes": [
                {
                    "process": "mid_wire",
                    "cost_estimate": 350.0,
                    "time_estimate": 6.0,
                    "quality_score": 0.8
                }
            ]
        }
    ]
}
```

---

### 6.4 PricingAgent（价格计算）

#### 输入 Context
```python
{
    "job_id": "...",
    "upstream_outputs": {
        "DecisionAgent": {...}
    },
    "snapshot_refs": {
        "price_version_locked": "v1.0"
    },
    "subgraphs": [...],
    "features": [...],
    "agent_parameters": {
        "include_markup": false
    }
}
```

#### 输出 OpResult.data
```python
{
    "subgraph_pricing": [
        {
            "subgraph_id": "sub_001",
            
            "cost_breakdown": {
                "material_cost": 120.50,
                "heat_treatment_cost": 80.00,
                "slow_wire_cost": 350.00,
                "grinding_cost": 125.00,
                "nc_cost": 200.00,
                "total": 875.50
            },
            
            "matched_price_items": [
                {
                    "price_snapshot_id": 1,  # job_price_snapshots 的 snapshot_id
                    "name": "SKD11 材料费",
                    "unit_price": 40.68,
                    "unit": "kg",
                    "quantity": 2.96,
                    "subtotal": 120.50
                },
                {
                    "price_snapshot_id": 5,
                    "name": "慢走丝加工费",
                    "unit_price": 0.70,
                    "unit": "mm",
                    "quantity": 500.0,
                    "subtotal": 350.00
                }
            ]
        }
    ],
    
    "job_total_cost": 4377.50,
    "currency": "CNY",
    
    "summary": {
        "total_material_cost": 602.50,
        "total_processing_cost": 3775.00,
        "subgraph_count": 5
    }
}
```

---

### 6.5 NCTimeAgent（NC 时间计算）

#### 输入 Context
```python
{
    "job_id": "...",
    "upstream_outputs": {
        "FeatureExtractionAgent": {...}
    },
    "subgraphs": [...],
    "features": [...],
    "agent_parameters": {
        "calculation_method": "analytical"  # "analytical" | "simulation"
    }
}
```

#### 输出 OpResult.data
```python
{
    "nc_time_results": [
        {
            "subgraph_id": "sub_001",
            
            "time_breakdown": {
                "nc_roughing_time": 3.5,     # 小时
                "nc_milling_time": 2.0,
                "drilling_time": 1.5,
                "total_nc_time": 7.0
            },
            
            "operation_details": [
                {
                    "operation": "roughing",
                    "machine_type": "CNC_MILL",
                    "cutting_time": 3.2,
                    "rapid_time": 0.3,
                    "tool_change_time": 0.0
                }
            ]
        }
    ],
    
    "job_total_nc_time": 35.0  # 小时
}
```

---

### 6.6 ReportAgent（报表生成）

#### 输入 Context
```python
{
    "job_id": "...",
    "upstream_outputs": {
        "PricingAgent": {...}
    },
    "subgraphs": [...],
    "features": [...],
    "agent_parameters": {
        "report_format": "pdf",  # "pdf" | "excel"
        "language": "zh-CN"
    }
}
```

#### 输出 OpResult.data
```python
{
    "report_summary": {
        "total_pages": 12,
        "sections": ["基本信息", "子图列表", "成本明细", "工艺说明"]
    }
}
```

#### 输出 OpResult.artifacts
```python
[
    {
        "artifact_id": "report_20260112_001",
        "artifact_type": "report_pdf",
        "file_name": "模具成本核算报告_XZ001.pdf",
        "storage_path": "/reports/job_xxx/final_report.pdf",
        "file_size_bytes": 2048576,
        "created_at": "2026-01-12T10:20:00.000Z"
    }
]
```

---

## 七、Agent 实现模板

### 7.1 标准 Agent 实现模板

```python
from typing import Dict, Any
from datetime import datetime
from .base_agent import BaseAgent, OpResult

class MyAgent(BaseAgent):
    """
    Agent 描述
    负责人：XXX
    """
    
    def __init__(self):
        super().__init__("MyAgent")
        self.version = "1.0.0"
    
    async def process(self, context: Dict[str, Any]) -> OpResult:
        """处理任务"""
        started_at = datetime.utcnow()
        
        try:
            # 1. 验证输入
            if not self._validate_context(context):
                return self._error_result(
                    context,
                    "INVALID_INPUT",
                    "缺少必要的输入参数",
                    started_at
                )
            
            # 2. 执行业务逻辑
            result_data = await self._do_work(context)
            
            # 3. 返回成功结果
            return OpResult(
                status="ok",
                data=result_data,
                message="处理成功",
                agent_name=self.name,
                agent_version=self.version,
                execution_id=context["agent_execution_id"],
                started_at=started_at,
                completed_at=datetime.utcnow(),
                confidence_score=0.95
            )
            
        except Exception as e:
            self.logger.error(f"{self.name} failed: {e}", exc_info=True)
            return self._error_result(
                context,
                "INTERNAL_ERROR",
                str(e),
                started_at,
                is_retryable=True
            )
    
    def _validate_context(self, context: Dict[str, Any]) -> bool:
        """验证输入上下文"""
        required_keys = ["job_id", "session_id", "agent_execution_id"]
        return all(k in context for k in required_keys)
    
    async def _do_work(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体业务逻辑（子类实现）"""
        # TODO: 实现业务逻辑
        return {"result": "success"}
    
    def _error_result(
        self,
        context: Dict[str, Any],
        error_code: str,
        error_message: str,
        started_at: datetime,
        is_retryable: bool = False
    ) -> OpResult:
        """构造错误结果"""
        return OpResult(
            status="error",
            message=error_message,
            agent_name=self.name,
            agent_version=self.version,
            execution_id=context.get("agent_execution_id"),
            started_at=started_at,
            completed_at=datetime.utcnow(),
            error_code=error_code,
            error_details=error_message,
            is_retryable=is_retryable
        )
```

---

## 八、数据库审计表

### 8.1 Agent 执行日志表

```sql
CREATE TABLE agent_execution_logs (
    log_id SERIAL PRIMARY KEY,
    
    -- 标识
    session_id VARCHAR(50) NOT NULL,
    job_id UUID NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    execution_id VARCHAR(100) UNIQUE NOT NULL,
    
    -- 输入输出
    input_context JSONB NOT NULL,
    output_result JSONB NOT NULL,
    
    -- 状态
    status VARCHAR(20) NOT NULL,  -- ok | warning | error | skipped
    error_code VARCHAR(50),
    error_message TEXT,
    
    -- 时间
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    
    -- 质量
    confidence_score DECIMAL(3, 2),
    
    -- 追踪
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX idx_exec_logs_job ON agent_execution_logs(job_id);
CREATE INDEX idx_exec_logs_session ON agent_execution_logs(session_id);
CREATE INDEX idx_exec_logs_status ON agent_execution_logs(status);
```

### 8.2 编排会话表

```sql
CREATE TABLE orchestration_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    job_id UUID NOT NULL,
    
    -- 状态
    status VARCHAR(20) NOT NULL,  -- running | completed | failed
    current_stage VARCHAR(50),
    progress INTEGER DEFAULT 0,
    
    -- 完整 State 快照（用于恢复）
    state_snapshot JSONB,
    
    -- 时间
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX idx_orch_sessions_job ON orchestration_sessions(job_id);
```

---

## 九、测试规范

### 9.1 Agent 单元测试模板

```python
import pytest
from agents.my_agent import MyAgent

@pytest.mark.asyncio
async def test_my_agent_success():
    """测试 Agent 正常执行"""
    agent = MyAgent()
    
    context = {
        "job_id": "test-job-123",
        "session_id": "sess_test_001",
        "agent_execution_id": "exec_test_001",
        "upstream_outputs": {},
        "snapshot_refs": {},
        "job_metadata": {},
        "subgraphs": [],
        "features": None,
        "agent_parameters": {},
        "directives": {}
    }
    
    result = await agent.process(context)
    
    assert result.status == "ok"
    assert result.agent_name == "MyAgent"
    assert result.execution_id == "exec_test_001"
    assert "data" in result.to_dict()

@pytest.mark.asyncio
async def test_my_agent_invalid_input():
    """测试 Agent 输入验证"""
    agent = MyAgent()
    
    context = {}  # 缺少必填字段
    
    result = await agent.process(context)
    
    assert result.status == "error"
    assert result.error_code == "INVALID_INPUT"
```

---

## 十、常见问题（FAQ）

### Q1: Agent 如何访问快照表？
**A**: Agent 从 `context["snapshot_refs"]["price_version_locked"]` 获取版本号，然后查询数据库：

```python
async with get_db() as db:
    snapshots = await db.execute(
        select(JobPriceSnapshot).where(
            JobPriceSnapshot.job_id == context["job_id"],
            JobPriceSnapshot.version_id == context["snapshot_refs"]["price_version_locked"]
        )
    )
```

### Q2: Agent 如何读取上游 Agent 的输出？
**A**: 从 `context["upstream_outputs"]` 中读取：

```python
cad_output = context["upstream_outputs"].get("CADAgent")
if cad_output and cad_output["status"] == "ok":
    subgraphs = cad_output["data"]["subgraphs"]
```

### Q3: Agent 需要记录日志吗？
**A**: Agent 内部使用 `self.logger` 记录关键步骤，编排器会自动将 `OpResult` 写入 `agent_execution_logs` 表。

### Q4: 如何处理可选依赖？
**A**: 检查上游 Agent 是否存在：

```python
nc_output = context["upstream_outputs"].get("NCTimeAgent")
if nc_output:
    # 使用 NC 时间数据
    pass
else:
    # 使用默认估算
    pass
```

---

## 十一、版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-01-12 | 初始版本 | 系统架构师 |

---

**文档结束**
