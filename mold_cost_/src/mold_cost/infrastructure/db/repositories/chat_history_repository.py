"""Src 侧聊天历史仓储实现。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.timezone_utils import now_shanghai

from ....core.logging import get_logger

logger = get_logger(__name__)


def _json_serializer(value: Any) -> str:
    """将 datetime 等对象序列化为 JSON 字符串。"""
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _isoformat(value: Any) -> str | None:
    """兼容数据库返回的 datetime / None。"""
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class ChatHistoryRepository:
    """聊天历史数据访问层。"""

    async def create_session(
        self,
        db_session: AsyncSession,
        session_id: str,
        job_id: str,
        user_id: str,
        session_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sql = text(
            """
            INSERT INTO chat_sessions (
                session_id, job_id, user_id, name, metadata, created_at, updated_at
            )
            VALUES (
                :session_id, :job_id, :user_id, :name, :metadata, :created_at, :updated_at
            )
            ON CONFLICT (session_id) DO UPDATE
            SET updated_at = :updated_at,
                name = COALESCE(EXCLUDED.name, chat_sessions.name)
            RETURNING session_id, job_id, user_id, name, created_at, status
            """
        )
        current_time = now_shanghai()
        result = await db_session.execute(
            sql,
            {
                "session_id": session_id,
                "job_id": job_id,
                "user_id": user_id,
                "name": session_name,
                "metadata": json.dumps(metadata or {}, default=_json_serializer, ensure_ascii=False),
                "created_at": current_time,
                "updated_at": current_time,
            },
        )
        row = result.fetchone()
        logger.info("聊天会话已创建或刷新: session_id=%s", session_id)
        return {
            "session_id": row[0],
            "job_id": row[1],
            "user_id": row[2],
            "name": row[3],
            "created_at": _isoformat(row[4]),
            "status": row[5],
        }

    async def add_message(
        self,
        db_session: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sql = text(
            """
            INSERT INTO chat_messages (session_id, role, content, metadata, timestamp)
            VALUES (:session_id, :role, :content, :metadata, :timestamp)
            RETURNING message_id, session_id, role, content, timestamp
            """
        )
        result = await db_session.execute(
            sql,
            {
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": json.dumps(metadata or {}, default=_json_serializer, ensure_ascii=False),
                "timestamp": now_shanghai(),
            },
        )
        row = result.fetchone()
        logger.info("聊天消息已写入: session_id=%s, role=%s", session_id, role)
        return {
            "message_id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "timestamp": _isoformat(row[4]),
        }

    async def get_session_history(
        self,
        db_session: AsyncSession,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT message_id, role, content, timestamp, metadata
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY timestamp ASC, message_id ASC
            LIMIT :limit
            OFFSET :offset
            """
        )
        result = await db_session.execute(
            sql,
            {"session_id": session_id, "limit": limit, "offset": offset},
        )
        return [
            {
                "message_id": row[0],
                "role": row[1],
                "content": row[2],
                "timestamp": _isoformat(row[3]),
                "metadata": row[4] or {},
            }
            for row in result.fetchall()
        ]

    async def get_recent_session_history(
        self,
        db_session: AsyncSession,
        session_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        # 中文注释：先倒序截取最近 N 条，再升序返回，保持调用方按对话时间顺序消费。
        sql = text(
            """
            SELECT message_id, role, content, timestamp, metadata
            FROM (
                SELECT message_id, role, content, timestamp, metadata
                FROM chat_messages
                WHERE session_id = :session_id
                ORDER BY timestamp DESC, message_id DESC
                LIMIT :limit
            ) AS recent_messages
            ORDER BY timestamp ASC, message_id ASC
            """
        )
        result = await db_session.execute(sql, {"session_id": session_id, "limit": limit})
        return [
            {
                "message_id": row[0],
                "role": row[1],
                "content": row[2],
                "timestamp": _isoformat(row[3]),
                "metadata": row[4] or {},
            }
            for row in result.fetchall()
        ]

    async def get_session_message_count(
        self,
        db_session: AsyncSession,
        session_id: str,
    ) -> int:
        sql = text(
            """
            SELECT COUNT(*) AS total
            FROM chat_messages
            WHERE session_id = :session_id
            """
        )
        result = await db_session.execute(sql, {"session_id": session_id})
        row = result.fetchone()
        return row[0] if row else 0

    async def get_session_info(
        self,
        db_session: AsyncSession,
        session_id: str,
    ) -> dict[str, Any] | None:
        sql = text(
            """
            SELECT session_id, job_id, user_id, name, created_at, updated_at, status, metadata
            FROM chat_sessions
            WHERE session_id = :session_id
            """
        )
        result = await db_session.execute(sql, {"session_id": session_id})
        row = result.fetchone()
        if not row:
            return None

        return {
            "session_id": row[0],
            "job_id": row[1],
            "user_id": row[2],
            "name": row[3],
            "created_at": _isoformat(row[4]),
            "updated_at": _isoformat(row[5]),
            "status": row[6],
            "metadata": row[7] or {},
        }

    async def get_user_sessions(
        self,
        db_session: AsyncSession,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT
                s.session_id,
                s.job_id,
                s.name,
                s.created_at,
                s.updated_at,
                s.status,
                s.metadata,
                COUNT(m.message_id) AS message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON s.session_id = m.session_id
            WHERE s.user_id = :user_id
            GROUP BY s.session_id, s.job_id, s.name, s.created_at, s.updated_at, s.status, s.metadata
            ORDER BY s.updated_at DESC
            LIMIT :limit
            """
        )
        result = await db_session.execute(sql, {"user_id": user_id, "limit": limit})
        return [
            {
                "session_id": row[0],
                "job_id": row[1],
                "name": row[2],
                "created_at": _isoformat(row[3]),
                "updated_at": _isoformat(row[4]),
                "status": row[5],
                "metadata": row[6] or {},
                "message_count": row[7],
            }
            for row in result.fetchall()
        ]

    async def archive_session(
        self,
        db_session: AsyncSession,
        session_id: str,
    ) -> bool:
        sql = text(
            """
            UPDATE chat_sessions
            SET status = 'archived', updated_at = :updated_at
            WHERE session_id = :session_id
            """
        )
        try:
            await db_session.execute(
                sql,
                {
                    "session_id": session_id,
                    "updated_at": now_shanghai(),
                },
            )
            logger.info("聊天会话已归档: session_id=%s", session_id)
            return True
        except Exception as exc:  # pragma: no cover - 保持兼容行为，失败时返回 False。
            logger.error("聊天会话归档失败: session_id=%s, error=%s", session_id, exc, exc_info=True)
            return False
