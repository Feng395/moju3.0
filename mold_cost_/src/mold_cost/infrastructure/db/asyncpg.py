"""兼容旧查询代码的 asyncpg 包装器。"""

from __future__ import annotations

from typing import Any

import asyncpg

from ...core.settings import settings

DB_CONFIG = {
    "host": settings.DB_HOST,
    "port": settings.DB_PORT,
    "user": settings.DB_USER,
    "password": settings.DB_PASSWORD,
    "database": settings.DB_NAME,
}


class DatabaseWrapper:
    """保留旧接口风格，避免定价/检索模块一次性大改。"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            self._pool = await asyncpg.create_pool(**self.config, min_size=1, max_size=10)
        return self._pool

    async def fetch_all(self, query: str, *args):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetch_one(self, query: str, *args):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def execute(self, query: str, *args):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_many(self, query: str, args_list: list[tuple]):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.executemany(query, args_list)

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None


db = DatabaseWrapper(DB_CONFIG)
