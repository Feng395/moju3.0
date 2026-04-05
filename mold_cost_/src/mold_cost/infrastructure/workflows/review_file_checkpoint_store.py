"""File-backed durable checkpoint store for review workflow state."""

from __future__ import annotations

import os
from pathlib import Path

from .file_checkpoint_store import FileCheckpointStore


class ReviewFileCheckpointStore:
    """Persist the latest review waiting state to a local JSON file."""

    def __init__(self, root_dir: Path | None = None):
        configured_root = os.getenv("MOLD_COST_REVIEW_CHECKPOINT_ROOT")
        base_dir = Path(__file__).resolve().parents[4] / ".runtime" / "review_checkpoints"
        self._store = FileCheckpointStore(Path(root_dir or configured_root or base_dir))

    def save(self, *, job_id: str, state: dict, checkpoint: dict) -> Path:
        return self._store.save(job_id=job_id, state=state, checkpoint=checkpoint)

    def load(self, job_id: str) -> dict | None:
        return self._store.load(job_id)
