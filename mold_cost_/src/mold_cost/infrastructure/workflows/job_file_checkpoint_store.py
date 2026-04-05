"""File-backed durable checkpoint store for job workflow tests and local runtime."""

from __future__ import annotations

import os
from pathlib import Path

from .file_checkpoint_store import FileCheckpointStore
from .sqlite_checkpoint_store import SqliteCheckpointStore


class JobFileCheckpointStore:
    """Persist the latest job checkpoint to a local JSON file."""

    def __init__(self, root_dir: Path | None = None):
        # 中文注释：默认仍走文件存储；只有显式配置 backend=sqlite 时才切到共享 SQLite 后端。
        backend = (os.getenv("MOLD_COST_JOB_CHECKPOINT_BACKEND") or os.getenv("MOLD_COST_CHECKPOINT_BACKEND") or "file").lower()
        configured_root = os.getenv("MOLD_COST_JOB_CHECKPOINT_ROOT")
        configured_db = os.getenv("MOLD_COST_JOB_CHECKPOINT_DB_PATH") or os.getenv("MOLD_COST_SHARED_CHECKPOINT_DB_PATH")
        base_dir = Path(__file__).resolve().parents[4] / ".runtime" / "job_checkpoints"
        default_db = Path(__file__).resolve().parents[4] / ".runtime" / "workflow_checkpoints.sqlite3"
        if backend == "sqlite":
            self._store = SqliteCheckpointStore(Path(root_dir or configured_db or default_db), namespace="job")
        else:
            self._store = FileCheckpointStore(Path(root_dir or configured_root or base_dir))

    def save(self, *, job_id: str, state: dict, checkpoint: dict) -> Path:
        return self._store.save(job_id=job_id, state=state, checkpoint=checkpoint)

    def load(self, job_id: str) -> dict | None:
        return self._store.load(job_id)
