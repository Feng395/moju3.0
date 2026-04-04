"""State objects for the main job workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

JobAction = Literal["start", "continue"]
JobWorkflowStep = Literal[
    "bootstrap",
    "load_context",
    "validate_start",
    "validate_continue",
    "execute_start",
    "execute_continue",
    "collect_post_run",
    "finalize",
    "completed",
    "failed",
]


@dataclass(slots=True)
class JobState:
    # 中文注释：这里固化 workflow 的最小稳定状态面，后续接 LangGraph
    # checkpoint / interrupt 时，优先围绕这些字段扩展，而不是继续把细节散落到 worker。
    job_id: str
    action: JobAction = "start"
    current_step: JobWorkflowStep = "bootstrap"
    status: str = "created"
    checkpoint_ns: str = "job_workflow"
    checkpoint_id: str | None = None
    resume_from: str | None = None
    dwg_path: str | None = None
    prt_path: str | None = None
    subgraph_ids: list[str] = field(default_factory=list)
    feature_summary: dict[str, Any] = field(default_factory=dict)
    review_status: str | None = None
    pricing_summary: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None

    @property
    def dwg_file_path(self) -> str | None:
        """Compatibility alias for older callers."""
        return self.dwg_path

    @property
    def prt_file_path(self) -> str | None:
        """Compatibility alias for older callers."""
        return self.prt_path
