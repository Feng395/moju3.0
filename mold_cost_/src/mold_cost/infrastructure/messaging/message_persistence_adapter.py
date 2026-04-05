"""Adapters for websocket and review message persistence."""

from __future__ import annotations

from typing import Any


class LegacyMessagePersistenceAdapter:
    """Keep the legacy persistence contract behind a src-owned boundary."""

    def __init__(self, manager: Any | None = None):
        self._manager = manager

    @property
    def manager(self):
        if self._manager is None:
            from agents.message_persistence_manager import get_persistence_manager

            self._manager = get_persistence_manager()
        return self._manager

    async def push_and_persist(
        self,
        *,
        job_id: str,
        ws_message: dict[str, Any],
        db_session=None,
        ws_manager=None,
    ) -> None:
        await self.manager.push_and_persist(
            job_id=job_id,
            ws_message=ws_message,
            db_session=db_session,
            ws_manager=ws_manager,
        )

    def should_persist(self, ws_message: dict[str, Any]) -> bool:
        return self.manager.should_persist(ws_message)

    async def persist_message(self, *, job_id: str, ws_message: dict[str, Any], db_session) -> None:
        await self.manager.persist_message(
            job_id=job_id,
            ws_message=ws_message,
            db_session=db_session,
        )


_message_persistence_adapter: LegacyMessagePersistenceAdapter | None = None


def get_message_persistence_adapter() -> LegacyMessagePersistenceAdapter:
    global _message_persistence_adapter

    if _message_persistence_adapter is None:
        _message_persistence_adapter = LegacyMessagePersistenceAdapter()

    return _message_persistence_adapter
