"""Compatibility wrapper for the shared websocket runtime."""

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.interfaces.api.websocket_runtime import ConnectionManager, manager

__all__ = ["ConnectionManager", "manager"]
