"""聊天会话数据访问适配层。"""

from __future__ import annotations

from typing import Any, Optional


class ChatHistoryRepository:
    """将聊天会话仓储从 application/use_cases 中剥离出来的适配器。"""

    def __init__(self) -> None:
        self._legacy_repository = None

    @property
    def legacy_repository(self):
        # 中文注释：继续复用 legacy 仓储实现，但把导入边界收口到 src 侧。
        if self._legacy_repository is None:
            from api_gateway.repositories.chat_history_repository import (
                ChatHistoryRepository as LegacyChatHistoryRepository,
            )

            self._legacy_repository = LegacyChatHistoryRepository()
        return self._legacy_repository

    async def create_session(
        self,
        db_session,
        session_id: str,
        job_id: str,
        user_id: str,
        session_name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return await self.legacy_repository.create_session(
            db_session=db_session,
            session_id=session_id,
            job_id=job_id,
            user_id=user_id,
            session_name=session_name,
            metadata=metadata,
        )

    async def get_session_history(
        self,
        db_session,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self.legacy_repository.get_session_history(
            db_session=db_session,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

    async def get_recent_session_history(
        self,
        db_session,
        session_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return await self.legacy_repository.get_recent_session_history(
            db_session=db_session,
            session_id=session_id,
            limit=limit,
        )
