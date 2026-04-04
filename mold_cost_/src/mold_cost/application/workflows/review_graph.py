"""审核工作流外壳。

当前阶段先复用既有 InteractionAgent，
通过统一 workflow 入口承接 review 相关动作，
后续再迁移为 LangGraph + Human-in-the-loop 模式。
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ...core.logging import get_logger
from .review_state import ReviewState

logger = get_logger(__name__)


class ReviewGraph:
    """审核工作流门面。"""

    def __init__(self):
        self._compiled_graph = None

    def invoke(self, state: ReviewState) -> ReviewState:
        """同步返回状态对象，兼容未来图执行接口。"""
        return state

    async def start_review(self, job_id: str, db_session):
        """启动审核流程。"""
        logger.info("通过 ReviewGraph 启动审核: job_id=%s", job_id)
        agent = self._get_agent()
        return await agent.start_review(job_id=job_id, db_session=db_session)

    async def handle_modification(self, job_id: str, modification_text: str, user_id: str, db_session):
        """处理审核修改指令。"""
        logger.info("通过 ReviewGraph 处理修改: job_id=%s", job_id)
        agent = self._get_agent()
        return await agent.handle_modification(
            job_id=job_id,
            modification_text=modification_text,
            user_id=user_id,
            db_session=db_session,
        )

    async def confirm_changes(self, job_id: str, user_id: str, db_session):
        """确认审核修改。"""
        logger.info("通过 ReviewGraph 确认修改: job_id=%s", job_id)
        agent = self._get_agent()
        return await agent.confirm_changes(job_id=job_id, user_id=user_id, db_session=db_session)

    async def refresh_data(self, job_id: str, db_session):
        """刷新审核数据。"""
        logger.info("通过 ReviewGraph 刷新审核数据: job_id=%s", job_id)
        agent = self._get_agent()
        return await agent.refresh_data(job_id=job_id, db_session=db_session)

    async def get_review_state(self, job_id: str):
        """获取审核状态。"""
        agent = self._get_agent()
        return await agent.get_review_state(job_id)

    async def check_lock(self, job_id: str) -> bool:
        """检查审核锁是否仍然有效。"""
        agent = self._get_agent()
        return await agent.check_lock(job_id)

    async def chat(self, job_id: str, message: str, history: list[dict], current_data):
        """非流式聊天。"""
        agent = self._get_agent()
        return await agent.chat(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        )

    async def chat_stream(self, job_id: str, message: str, history: list[dict], current_data):
        """流式聊天。"""
        agent = self._get_agent()
        async for chunk in agent.chat_stream(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        ):
            yield chunk

    def to_state(self, job_id: str, **kwargs) -> ReviewState:
        """构造标准审核状态对象。"""
        return ReviewState(job_id=job_id, **kwargs)

    def serialize_state(self, state: ReviewState) -> dict[str, Any]:
        """序列化审核状态。"""
        return asdict(state)

    def get_compiled_graph(self):
        """按需构造最小 LangGraph 图。"""
        if self._compiled_graph is not None:
            return self._compiled_graph

        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            logger.info("当前环境未启用 LangGraph，继续使用审核门面模式")
            return None

        graph = StateGraph(dict)
        graph.add_node("passthrough", lambda state: state)
        graph.add_edge(START, "passthrough")
        graph.add_edge("passthrough", END)
        self._compiled_graph = graph.compile()
        return self._compiled_graph

    @staticmethod
    def _get_agent():
        """懒加载 InteractionAgent。"""
        from agents.interaction_agent import InteractionAgent

        return InteractionAgent()


review_graph = ReviewGraph()
