"""
BaseAgent基类
负责人：人员A
版本：v1.2 - 增强 OpResult，标准化输入输出，支持上海时区

合并信息：
- 合并日期：2026-02-10
- 源文件：mold_cost-main/agents/base_agent.py + mold_cost_/agents/base_agent.py
- 合并策略：使用 mold_cost-main 的增强版，添加 mold_cost_ 的时区支持
- 主要改动：
  1. 保留 mold_cost-main 的增强 OpResult 类（元数据、质量评分、错误详情）
  2. 保留 mold_cost-main 的增强 BaseAgent 类（版本管理、验证、日志）
  3. 添加上海时区支持（now_shanghai）
  4. 所有时间戳使用上海时区

OpResult 增强功能：
- 支持 agent_name, agent_version, execution_id
- 支持 confidence_score（质量评分）
- 支持 warnings（警告列表）
- 支持 error_code, error_details, is_retryable
- 支持 artifacts（工件列表）
- 支持 duration_ms（持续时间）
- 提供 to_dict() 方法

BaseAgent 增强功能：
- 版本号管理
- validate_context() - 上下文验证
- build_error_result() - 标准错误构造
- _log_operation() - 操作日志记录到数据库
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from shared.timezone_utils import now_shanghai

logger = logging.getLogger(__name__)

class OpResult:
    """
    Agent 操作结果（增强版）
    
    使用示例:
    ```python
    return OpResult(
        status="ok",
        data={"subgraphs": [...]},
        message="成功拆分为 5 个子图",
        agent_name="CADAgent",
        agent_version="1.0.0",
        execution_id=context["agent_execution_id"],
        confidence_score=0.95
    )
    ```
    """
    def __init__(
        self,
        status: str,  # "ok" | "warning" | "error" | "skipped"
        data: Optional[Dict[str, Any]] = None,
        message: str = "",
        refs: Optional[Dict[str, Any]] = None,
        
        # ========== 标准字段 ==========
        agent_name: Optional[str] = None,
        agent_version: str = "1.0.0",
        execution_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        
        # ========== 质量元数据 ==========
        confidence_score: float = 1.0,  # 0.0-1.0
        warnings: Optional[List[str]] = None,
        
        # ========== 错误详情（status="error" 时必填）==========
        error_code: Optional[str] = None,
        error_details: Optional[str] = None,
        is_retryable: bool = False,
        
        # ========== 生成的工件 ==========
        artifacts: Optional[List[Dict]] = None
    ):
        self.status = status
        self.data = data or {}
        self.message = message
        self.refs = refs or {}
        self.timestamp = now_shanghai()  # 使用上海时区
        
        self.agent_name = agent_name
        self.agent_version = agent_version
        self.execution_id = execution_id
        self.started_at = started_at or now_shanghai()  # 使用上海时区
        self.completed_at = completed_at or now_shanghai()  # 使用上海时区
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
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            
            "confidence_score": self.confidence_score,
            "warnings": self.warnings,
            
            "error_code": self.error_code,
            "error_details": self.error_details,
            "is_retryable": self.is_retryable,
            
            "artifacts": self.artifacts
        }

class BaseAgent(ABC):
    """
    Agent 基类
    
    所有 Agent 必须继承此类并实现 process() 方法
    
    使用示例:
    ```python
    class MyAgent(BaseAgent):
        def __init__(self):
            super().__init__("MyAgent")
            self.version = "1.0.0"
        
        async def process(self, context: Dict[str, Any]) -> OpResult:
            started_at = now_shanghai()
            
            # 执行业务逻辑
            result_data = await self._do_work(context)
            
            return OpResult(
                status="ok",
                data=result_data,
                agent_name=self.name,
                agent_version=self.version,
                execution_id=context["agent_execution_id"],
                started_at=started_at,
                completed_at=now_shanghai()
            )
    ```
    """
    
    def __init__(self, name: str):
        self.name = name
        self.version = "1.0.0"  # 子类应覆盖此版本号
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> OpResult:
        """
        处理任务（子类必须实现）
        
        Args:
            context: AgentContext 输入上下文，包含：
                - job_id: 任务ID
                - session_id: 会话ID
                - agent_execution_id: 执行ID
                - upstream_outputs: 上游 Agent 输出
                - snapshot_refs: 快照引用
                - job_metadata: Job 元信息
                - subgraphs: 子图数据（可选）
                - features: 特征数据（可选）
                - agent_parameters: Agent 参数
                - directives: 控制指令
        
        Returns:
            OpResult: 标准化的操作结果
        """
        pass
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """
        验证输入上下文
        
        检查必填字段是否存在
        """
        required_keys = ["job_id", "session_id", "agent_execution_id"]
        return all(k in context for k in required_keys)
    
    def build_error_result(
        self,
        context: Dict[str, Any],
        error_code: str,
        error_message: str,
        started_at: datetime,
        is_retryable: bool = False
    ) -> OpResult:
        """
        构造标准错误结果
        
        使用示例:
        ```python
        return self.build_error_result(
            context,
            "FILE_NOT_FOUND",
            "文件不存在",
            started_at,
            is_retryable=False
        )
        ```
        """
        return OpResult(
            status="error",
            message=error_message,
            agent_name=self.name,
            agent_version=self.version,
            execution_id=context.get("agent_execution_id"),
            started_at=started_at,
            completed_at=now_shanghai(),  # 使用上海时区
            error_code=error_code,
            error_details=error_message,
            is_retryable=is_retryable
        )
    
    def log_operation(self, action: str, input_data: Any, output_data: Any):
        """记录操作日志"""
        self.logger.info(f"Action: {action}, Input: {input_data}, Output: {output_data}")
    
    async def _log_operation(
        self,
        job_id: str,
        subgraph_id: Optional[str],
        action: str,
        result: Dict[str, Any],
        duration_ms: int,
        input_data: Optional[Dict[str, Any]] = None
    ):
        """
        记录操作日志到 operation_logs 表
        
        用于记录 Agent 的每次操作，支持 Job 级别和子图级别
        
        Args:
            job_id: 任务ID
            subgraph_id: 子图ID（可选，Job级别操作时为None）
            action: 操作名称（如 "feature_recognition_retry", "pricing_calculation_retry"）
            result: 操作结果字典
            duration_ms: 耗时（毫秒）
            input_data: 输入参数（可选）
        
        使用示例:
        ```python
        await self._log_operation(
            job_id="xxx",
            subgraph_id="sub_001",
            action="feature_recognition_retry",
            result={"status": "ok", "features": {...}},
            duration_ms=2500,
            input_data={"job_id": "xxx", "subgraph_id": "sub_001"}
        )
        ```
        """
        try:
            from shared.database import get_db
            from shared.models import OperationLog
            from sqlalchemy import insert
            
            # 构造输入数据
            if input_data is None:
                input_data = {"job_id": job_id}
                if subgraph_id:
                    input_data["subgraph_id"] = subgraph_id
            
            # 写入数据库
            async for db in get_db():
                await db.execute(
                    insert(OperationLog).values(
                        job_id=job_id,
                        subgraph_id=subgraph_id,
                        agent=self.name,
                        action=action,
                        input_data=input_data,
                        output_data=result,
                        status=result.get("status", "unknown"),
                        duration_ms=duration_ms,
                        error_message=result.get("message") if result.get("status") in ["error", "failed"] else None,
                        created_at=now_shanghai()  # 使用上海时区
                    )
                )
                await db.commit()
                
                self.logger.debug(
                    f"[{self.name}] 记录操作日志: action={action}, "
                    f"subgraph_id={subgraph_id}, status={result.get('status')}, "
                    f"duration={duration_ms}ms"
                )
                break  # 只需要第一次迭代
                
        except Exception as e:
            self.logger.error(f"[{self.name}] 记录操作日志失败: {e}", exc_info=True)
