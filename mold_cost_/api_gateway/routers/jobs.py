"""Legacy jobs router compatibility wrapper."""

from __future__ import annotations

from fastapi import Depends

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.interfaces.api.routers.jobs import (
    JobService as _SrcJobService,
    continue_job as _src_continue_job,
    get_jobs_router,
    get_legacy_jobs_router,
    router,
    router_legacy,
)
from api_gateway.auth import get_current_user

JobService = _SrcJobService


async def continue_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Compatibility facade for legacy direct function calls and monkeypatch-based tests."""
    from mold_cost.interfaces.api.routers import jobs as src_jobs

    original_job_service = src_jobs.JobService
    try:
        src_jobs.JobService = JobService
        return await _src_continue_job(job_id=job_id, current_user=current_user)
    finally:
        src_jobs.JobService = original_job_service


__all__ = [
    "JobService",
    "continue_job",
    "get_jobs_router",
    "get_legacy_jobs_router",
    "router",
    "router_legacy",
]
