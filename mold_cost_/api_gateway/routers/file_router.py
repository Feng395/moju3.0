"""Legacy file router compatibility wrapper."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.interfaces.api.routers.files import router

__all__ = ["router"]
