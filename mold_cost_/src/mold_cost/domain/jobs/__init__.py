"""任务领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class JobSummary:
    """任务摘要。

    中文注释：当前阶段先提供轻量领域对象，后续再逐步扩展为完整聚合。
    """

    job_id: str
    status: str
    progress: int = 0
    current_stage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["JobSummary"]
