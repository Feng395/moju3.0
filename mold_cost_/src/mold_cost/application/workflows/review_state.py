"""State objects for the review workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReviewState:
    # raw_data / display_view 是两层数据：前者用于版本校验和落库，后者用于前端展示。
    job_id: str
    review_id: str | None = None
    status: str = "pending"
    raw_data: dict[str, Any] = field(default_factory=dict)
    display_view: list[dict[str, Any]] = field(default_factory=list)
    completeness: dict[str, Any] = field(default_factory=dict)
    data_version: dict[str, str] = field(default_factory=dict)
    modifications: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: str | None = None
    last_modified_at: str | None = None
    last_confirmed_at: str | None = None
    last_refreshed_at: str | None = None
    reloaded_at: str | None = None
    refresh_count: int = 0
    confirm_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, job_id: str, payload: dict[str, Any]) -> "ReviewState":
        # extra 保留未知字段，避免兼容迁移期间把 legacy 状态内容丢掉。
        known_fields = {
            "review_id",
            "status",
            "raw_data",
            "display_view",
            "completeness",
            "data_version",
            "modifications",
            "suggestions",
            "messages",
            "created_at",
            "last_modified_at",
            "last_confirmed_at",
            "last_refreshed_at",
            "reloaded_at",
            "refresh_count",
            "confirm_count",
        }
        extra = {key: value for key, value in payload.items() if key not in known_fields and key != "job_id"}
        return cls(
            job_id=job_id,
            review_id=payload.get("review_id"),
            status=payload.get("status", "pending"),
            raw_data=payload.get("raw_data") or payload.get("data") or {},
            display_view=payload.get("display_view") or [],
            completeness=payload.get("completeness") or {},
            data_version=payload.get("data_version") or {},
            modifications=payload.get("modifications") or [],
            suggestions=payload.get("suggestions") or [],
            messages=payload.get("messages") or [],
            created_at=payload.get("created_at"),
            last_modified_at=payload.get("last_modified_at"),
            last_confirmed_at=payload.get("last_confirmed_at"),
            last_refreshed_at=payload.get("last_refreshed_at"),
            reloaded_at=payload.get("reloaded_at"),
            refresh_count=payload.get("refresh_count", 0),
            confirm_count=payload.get("confirm_count", 0),
            extra=extra,
        )

    def to_payload(self) -> dict[str, Any]:
        # 对外仍保持 dict 形态，兼容现有 Redis 存储和路由读取方式。
        payload = {
            "job_id": self.job_id,
            "review_id": self.review_id,
            "status": self.status,
            "raw_data": self.raw_data,
            "display_view": self.display_view,
            "completeness": self.completeness,
            "data_version": self.data_version,
            "modifications": self.modifications,
            "suggestions": self.suggestions,
            "messages": self.messages,
            "created_at": self.created_at,
            "last_modified_at": self.last_modified_at,
            "last_confirmed_at": self.last_confirmed_at,
            "last_refreshed_at": self.last_refreshed_at,
            "reloaded_at": self.reloaded_at,
            "refresh_count": self.refresh_count,
            "confirm_count": self.confirm_count,
        }
        payload.update(self.extra)
        return payload
