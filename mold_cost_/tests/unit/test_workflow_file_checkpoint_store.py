"""Unit tests for the shared workflow file checkpoint store."""

from __future__ import annotations

import shutil
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_shared_file_checkpoint_store_round_trips_payload():
    from mold_cost.infrastructure.workflows.file_checkpoint_store import FileCheckpointStore

    temp_dir = Path(__file__).resolve().parent / ".workflow-checkpoint-runtime"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    store = FileCheckpointStore(temp_dir)
    target = store.save(
        job_id="job/shared-1",
        state={"status": "waiting"},
        checkpoint={"thread_id": "job/shared-1", "checkpoint_id": "confirm"},
    )

    payload = store.load("job/shared-1")

    assert target.exists()
    assert payload is not None
    assert payload["job_id"] == "job/shared-1"
    assert payload["thread_id"] == "job/shared-1"
    assert payload["state"]["status"] == "waiting"
    assert payload["checkpoint"]["checkpoint_id"] == "confirm"
    shutil.rmtree(temp_dir, ignore_errors=True)
