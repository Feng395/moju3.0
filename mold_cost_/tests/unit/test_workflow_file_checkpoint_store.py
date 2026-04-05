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


def test_shared_sqlite_checkpoint_store_round_trips_payload():
    from mold_cost.infrastructure.workflows.sqlite_checkpoint_store import SqliteCheckpointStore

    temp_dir = Path(__file__).resolve().parent / ".workflow-sqlite-runtime"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_path = temp_dir / "workflow.sqlite3"

    store = SqliteCheckpointStore(db_path, namespace="job")
    target = store.save(
        job_id="job/sqlite-1",
        state={"status": "waiting"},
        checkpoint={"thread_id": "job/sqlite-1", "checkpoint_id": "confirm"},
    )

    payload = store.load("job/sqlite-1")

    assert target.exists()
    assert payload is not None
    assert payload["job_id"] == "job/sqlite-1"
    assert payload["thread_id"] == "job/sqlite-1"
    assert payload["state"]["status"] == "waiting"
    assert payload["checkpoint"]["checkpoint_id"] == "confirm"
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_job_and_review_checkpoint_wrappers_can_share_one_sqlite_backend(monkeypatch):
    from mold_cost.infrastructure.workflows.job_file_checkpoint_store import JobFileCheckpointStore
    from mold_cost.infrastructure.workflows.review_file_checkpoint_store import ReviewFileCheckpointStore

    temp_dir = Path(__file__).resolve().parent / ".workflow-wrapper-sqlite-runtime"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_path = temp_dir / "shared.sqlite3"

    monkeypatch.setenv("MOLD_COST_CHECKPOINT_BACKEND", "sqlite")
    monkeypatch.setenv("MOLD_COST_SHARED_CHECKPOINT_DB_PATH", str(db_path))

    job_store = JobFileCheckpointStore()
    review_store = ReviewFileCheckpointStore()

    job_store.save(
        job_id="shared-job",
        state={"status": "job-waiting"},
        checkpoint={"thread_id": "shared-job", "checkpoint_id": "job-cp"},
    )
    review_store.save(
        job_id="shared-job",
        state={"status": "review-waiting"},
        checkpoint={"thread_id": "shared-job", "checkpoint_id": "review-cp"},
    )

    job_payload = job_store.load("shared-job")
    review_payload = review_store.load("shared-job")

    assert job_payload is not None
    assert review_payload is not None
    assert job_payload["state"]["status"] == "job-waiting"
    assert review_payload["state"]["status"] == "review-waiting"
    assert job_payload["checkpoint"]["checkpoint_id"] == "job-cp"
    assert review_payload["checkpoint"]["checkpoint_id"] == "review-cp"
    shutil.rmtree(temp_dir, ignore_errors=True)
