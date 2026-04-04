"""任务工作流占位实现。

当前阶段先提供稳定导入点，后续再替换为 LangGraph 真正图结构。
"""

from __future__ import annotations

from .job_state import JobState


class JobGraph:
    """第一阶段的最小工作流对象。"""

    def invoke(self, state: JobState) -> JobState:
        return state


job_graph = JobGraph()
