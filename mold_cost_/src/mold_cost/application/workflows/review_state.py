"""State objects for the review workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReviewState:
    job_id: str
    review_id: str | None = None
    status: str = "pending"
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
