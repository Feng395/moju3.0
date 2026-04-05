"""Best-effort websocket activity tracking for local monitoring tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any


@dataclass(slots=True)
class WebSocketActivity:
    job_id: str
    last_seen_at: float
    channel: str
    message_type: str
    message_count: int = 0
    last_payload: dict[str, Any] = field(default_factory=dict)


class RedisWebSocketActivityTracker:
    """Track websocket-like activity from Redis pub/sub messages."""

    def __init__(self, *, activity_timeout_seconds: int = 5):
        self.activity_timeout_seconds = activity_timeout_seconds
        self._jobs: dict[str, WebSocketActivity] = {}

    def mark_seen(
        self,
        *,
        job_id: str,
        channel: str,
        message_type: str,
        payload: dict[str, Any] | None = None,
        now: float | None = None,
    ) -> bool:
        now = monotonic() if now is None else now
        became_active = job_id not in self._jobs or self._is_stale(job_id, now=now)
        activity = self._jobs.get(job_id)
        if activity is None:
            activity = WebSocketActivity(
                job_id=job_id,
                last_seen_at=now,
                channel=channel,
                message_type=message_type,
            )
            self._jobs[job_id] = activity
        activity.last_seen_at = now
        activity.channel = channel
        activity.message_type = message_type
        activity.message_count += 1
        if payload is not None:
            activity.last_payload = dict(payload)
        return became_active

    def prune_stale(self, now: float | None = None) -> list[str]:
        now = monotonic() if now is None else now
        expired = [job_id for job_id in list(self._jobs) if self._is_stale(job_id, now=now)]
        for job_id in expired:
            self._jobs.pop(job_id, None)
        return expired

    def get_connection_count(self, job_id: str | None = None, now: float | None = None) -> int:
        now = monotonic() if now is None else now
        if job_id is not None:
            return 1 if not self._is_stale(job_id, now=now) else 0
        return sum(1 for current_job_id in self._jobs if not self._is_stale(current_job_id, now=now))

    def get_all_job_ids(self, now: float | None = None) -> list[str]:
        now = monotonic() if now is None else now
        return sorted(job_id for job_id in self._jobs if not self._is_stale(job_id, now=now))

    def snapshot(self, now: float | None = None) -> dict[str, int]:
        now = monotonic() if now is None else now
        return {job_id: self.get_connection_count(job_id, now=now) for job_id in self.get_all_job_ids(now=now)}

    def describe(self, job_id: str) -> dict[str, Any] | None:
        activity = self._jobs.get(job_id)
        if activity is None:
            return None
        return {
            "job_id": activity.job_id,
            "channel": activity.channel,
            "message_type": activity.message_type,
            "message_count": activity.message_count,
            "last_seen_at": activity.last_seen_at,
            "active": not self._is_stale(job_id),
        }

    def _is_stale(self, job_id: str, now: float | None = None) -> bool:
        now = monotonic() if now is None else now
        activity = self._jobs.get(job_id)
        if activity is None:
            return True
        return (now - activity.last_seen_at) > self.activity_timeout_seconds
