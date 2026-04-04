"""Compatibility wrapper for the refactored asyncpg database module."""

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.asyncpg import DB_CONFIG, DatabaseWrapper, db

__all__ = ["DB_CONFIG", "DatabaseWrapper", "db"]
