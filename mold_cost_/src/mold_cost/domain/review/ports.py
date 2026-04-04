"""审核领域端口定义。"""

from __future__ import annotations

from typing import Any, Protocol


class ReviewService(Protocol):
    """审核服务协议。"""

    async def start(self, job_id: str, db_session) -> Any: ...

    async def modify(self, job_id: str, modification_text: str, user_id: str, db_session) -> Any: ...

    async def confirm(self, job_id: str, user_id: str, db_session) -> Any: ...

    async def refresh(self, job_id: str, db_session) -> Any: ...
