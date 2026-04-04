"""Ports exposed by the CAD domain."""

from __future__ import annotations

from typing import Protocol


class CadSplitService(Protocol):
    async def split(self, dwg_url: str | None, job_id: str, minio_client=None) -> dict: ...
