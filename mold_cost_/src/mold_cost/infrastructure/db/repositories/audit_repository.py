"""Src-owned audit repository."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.logging import get_logger

logger = get_logger(__name__)


class AuditRepository:
    """审计日志数据访问层。"""

    async def create_audit_log(
        self,
        db: AsyncSession,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        changes: dict[str, Any],
    ) -> None:
        sql = text(
            """
            INSERT INTO audit_logs (
                user_id, action, resource_type, resource_id,
                changes, created_at
            ) VALUES (
                :user_id, :action, :resource_type, :resource_id,
                :changes, :created_at
            )
            """
        )
        await db.execute(
            sql,
            {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "changes": json.dumps(changes),
                "created_at": datetime.now(),
            },
        )
        logger.info("Audit log created: %s - %s", action, resource_id)
