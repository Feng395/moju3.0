"""审核工作流占位实现。

当前阶段先提供稳定导入点，后续再替换为 LangGraph 真正图结构。
"""

from __future__ import annotations

from .review_state import ReviewState


class ReviewGraph:
    """第一阶段的最小审核工作流对象。"""

    def invoke(self, state: ReviewState) -> ReviewState:
        return state


review_graph = ReviewGraph()
