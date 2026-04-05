"""Shared file-backed durable checkpoint store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FileCheckpointStore:
    """Persist the latest workflow checkpoint to a local JSON file."""

    def __init__(self, root_dir: Path):
        self._root_dir = Path(root_dir)

    def save(self, *, job_id: str, state: dict[str, Any], checkpoint: dict[str, Any]) -> Path:
        self._root_dir.mkdir(parents=True, exist_ok=True)
        target = self._path_for(job_id)
        payload = {
            "job_id": job_id,
            "thread_id": checkpoint.get("thread_id") or job_id,
            "state": state,
            "checkpoint": checkpoint,
        }
        temp_path = target.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(target)
        return target

    def load(self, job_id: str) -> dict[str, Any] | None:
        path = self._path_for(job_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            return None
        payload.setdefault("job_id", job_id)
        payload.setdefault("thread_id", job_id)
        payload.setdefault("state", {})
        payload.setdefault("checkpoint", {})
        return payload

    def _path_for(self, job_id: str) -> Path:
        safe_job_id = job_id.replace("/", "_").replace("\\", "_")
        return self._root_dir / f"{safe_job_id}.json"
