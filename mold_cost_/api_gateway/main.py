"""Legacy API Gateway compatibility wrapper."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.interfaces.api.app import app, get_app

__all__ = ["app", "get_app"]
