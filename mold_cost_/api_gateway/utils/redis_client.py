"""Compatibility wrapper for the refactored Redis client."""

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.messaging.redis_client import RedisClient, redis_client

__all__ = ["RedisClient", "redis_client"]
