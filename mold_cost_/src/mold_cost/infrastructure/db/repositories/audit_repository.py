"""审计日志数据访问适配层。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class AuditRepository:
    """将审计仓储从 application/use_cases 中剥离出来的适配器。"""

    async def create_audit_log(
        self,
        db: AsyncSession,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        changes: dict[str, Any],
    ) -> None:
        from api_gateway.repositories.audit_repository import AuditRepository as LegacyAuditRepository

        return await LegacyAuditRepository.create_audit_log(
            db=db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
        )

