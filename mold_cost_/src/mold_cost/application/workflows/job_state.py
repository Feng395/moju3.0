"""State objects for the main job workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class JobState:
    job_id: str
    user_id: str | None = None
    status: str = "created"
    dwg_file_path: str | None = None
    prt_file_path: str | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
