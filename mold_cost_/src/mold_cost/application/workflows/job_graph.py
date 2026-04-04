"""任务工作流外壳。

当前阶段先复用既有 OrchestratorAgent，
但所有新入口统一通过 `job_graph` 进入，
后续再逐步替换为真正的 LangGraph 节点图。
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ...core.logging import get_logger
from .job_state import JobState

logger = get_logger(__name__)


class JobGraph:
    """任务工作流门面。

    设计目标：
    1. 给外部提供稳定的工作流入口；
    2. 内部继续复用旧 orchestrator，降低迁移风险；
    3. 后续可以平滑切换为 LangGraph 的真实图结构。
    """

    def __init__(self):
        self._compiled_graph = None

    def invoke(self, state: JobState) -> JobState:
        """同步返回状态对象，兼容未来 LangGraph 的状态流接口。"""
        return state

    async def start_job(self, job_id: str) -> dict[str, Any]:
        """启动任务主流程。"""
        logger.info("通过 JobGraph 启动任务: job_id=%s", job_id)
        orchestrator = self._get_orchestrator()
        return await orchestrator.start(job_id)

    async def continue_job(self, job_id: str) -> dict[str, Any]:
        """继续执行等待确认后的任务。"""
        logger.info("通过 JobGraph 继续任务: job_id=%s", job_id)
        orchestrator = self._get_orchestrator()
        return await orchestrator.continue_job(job_id)

    def to_state(self, job_id: str, **kwargs) -> JobState:
        """构造标准工作流状态对象。"""
        return JobState(job_id=job_id, **kwargs)

    def serialize_state(self, state: JobState) -> dict[str, Any]:
        """序列化状态，便于后续存储到 LangGraph checkpoint。"""
        return asdict(state)

    def get_compiled_graph(self):
        """按需构造 LangGraph 对象。

        当前仅提供最小图结构，作为后续持久化和 interrupt 的落点。
        如果环境未安装 LangGraph，则返回 `None`，不影响现有流程。
        """
        if self._compiled_graph is not None:
            return self._compiled_graph

        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            logger.info("当前环境未启用 LangGraph，继续使用门面模式")
            return None

        # 中文注释：这里先放一个极简图，后续逐步拆为真正节点。
        graph = StateGraph(dict)
        graph.add_node("passthrough", lambda state: state)
        graph.add_edge(START, "passthrough")
        graph.add_edge("passthrough", END)
        self._compiled_graph = graph.compile()
        return self._compiled_graph

    @staticmethod
    def _get_orchestrator():
        """懒加载 Orchestrator，避免导入时初始化大量依赖。"""
        from agents import get_orchestrator_agent

        return get_orchestrator_agent()


job_graph = JobGraph()
