"""聊天会话数据访问适配层。"""

from __future__ import annotations

from typing import Any, Optional


class ChatHistoryRepository:
    """将聊天会话仓储从 application/use_cases 中剥离出来的适配器。"""

    async def create_session(
        self,
        db_session,
        session_id: str,
        job_id: str,
        user_id: str,
        session_name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        from api_gateway.repositories.chat_history_repository import (
            ChatHistoryRepository as LegacyChatHistoryRepository,
        )

        legacy_repository = LegacyChatHistoryRepository()
        return await legacy_repository.create_session(
            db_session=db_session,
            session_id=session_id,
            job_id=job_id,
            user_id=user_id,
            session_name=session_name,
            metadata=metadata,
        )

