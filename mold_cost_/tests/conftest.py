from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _configure_job_checkpoint_root():
    """Route default job checkpoint files to a repo-local temp dir on Windows."""
    checkpoint_root = Path(__file__).resolve().parent / ".pytest_runtime" / "job_checkpoints"
    if checkpoint_root.parent.exists():
        shutil.rmtree(checkpoint_root.parent, ignore_errors=True)
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get("MOLD_COST_JOB_CHECKPOINT_ROOT")
    os.environ["MOLD_COST_JOB_CHECKPOINT_ROOT"] = str(checkpoint_root)
    try:
        yield
    finally:
        shutil.rmtree(checkpoint_root.parent, ignore_errors=True)
        if previous is None:
            os.environ.pop("MOLD_COST_JOB_CHECKPOINT_ROOT", None)
        else:
            os.environ["MOLD_COST_JOB_CHECKPOINT_ROOT"] = previous
