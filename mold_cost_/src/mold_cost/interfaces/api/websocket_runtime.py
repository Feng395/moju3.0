"""Shared websocket runtime used by both legacy API and diagnostics."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List

from fastapi import WebSocket

from mold_cost.infrastructure.messaging.message_persistence_adapter import get_message_persistence_adapter
from mold_cost.infrastructure.messaging.redis_client import redis_client
from shared.database import get_db
from shared.logging_config import get_logger
from shared.logging_middleware import log_websocket_message

logger = get_logger(__name__)


class ConnectionManager:
    """Manage websocket connections and Redis fan-out."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.subscriber_task = None
        self.redis_client = redis_client

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        self.active_connections.setdefault(job_id, []).append(websocket)
        logger.info(
            "WebSocket connected: job_id=%s, connections=%s",
            job_id,
            len(self.active_connections[job_id]),
        )

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id not in self.active_connections:
            return
        try:
            self.active_connections[job_id].remove(websocket)
            logger.info("WebSocket disconnected: job_id=%s", job_id)
        except ValueError:
            logger.warning("WebSocket disconnect skipped for unknown connection: job_id=%s", job_id)
            return

        if not self.active_connections[job_id]:
            del self.active_connections[job_id]
            logger.info("All websocket connections removed for job_id=%s", job_id)

    async def broadcast(self, job_id: str, message: dict):
        if job_id not in self.active_connections:
            logger.warning("Broadcast skipped because no websocket clients exist: job_id=%s", job_id)
            return

        log_websocket_message(job_id, message.get("type", "unknown"), message, direction="send")
        disconnected: list[WebSocket] = []
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.error("WebSocket send failed: job_id=%s, error=%s", job_id, exc)
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection, job_id)

        logger.info(
            "Broadcast finished: job_id=%s, active_connections=%s",
            job_id,
            len(self.active_connections.get(job_id, [])),
        )

    def get_connection_count(self, job_id: str | None = None) -> int:
        if job_id is not None:
            return len(self.active_connections.get(job_id, []))
        return sum(len(connections) for connections in self.active_connections.values())

    def get_all_job_ids(self) -> List[str]:
        return list(self.active_connections.keys())

    async def start_redis_subscriber(self):
        logger.info("Starting websocket Redis subscriber")
        pubsub = await self.redis_client.subscribe("job:*:progress", "job:*:review")
        try:
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    await self._handle_redis_message(message)
        except Exception:
            logger.error("Redis subscriber crashed", exc_info=True)
            raise

    async def _handle_redis_message(self, message):
        try:
            channel = message["channel"]
            if isinstance(channel, bytes):
                channel = channel.decode("utf-8")

            parts = channel.split(":")
            if len(parts) < 3:
                logger.warning("Ignoring malformed Redis channel: %s", channel)
                return

            job_id = parts[1]
            channel_type = parts[2]

            payload = message["data"]
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            data = json.loads(payload)

            if channel_type == "progress":
                ws_message = {
                    "type": "progress",
                    "job_id": job_id,
                    "timestamp": datetime.now().isoformat(),
                    "data": data,
                }
            elif channel_type == "review":
                ws_message = data
                ws_message.setdefault("job_id", job_id)
                ws_message.setdefault("timestamp", datetime.now().isoformat())
            else:
                logger.warning("Ignoring unsupported Redis channel type: %s", channel_type)
                return

            await self.broadcast(job_id, ws_message)
            await self._save_to_history(job_id, ws_message)
            if channel_type == "progress":
                await self._persist_to_database(job_id, ws_message)
        except json.JSONDecodeError:
            logger.error("Failed to decode Redis websocket payload", exc_info=True)
        except Exception:
            logger.error("Failed to handle Redis websocket message", exc_info=True)

    async def _save_to_history(self, job_id: str, message: dict):
        try:
            if not self.redis_client.client:
                return
            key = f"job:{job_id}:messages"
            await self.redis_client.lpush(key, json.dumps(message))
            await self.redis_client.ltrim(key, 0, 9)
            await self.redis_client.expire(key, 3600)
        except Exception:
            logger.error("Failed to save websocket history", exc_info=True)

    async def _persist_to_database(self, job_id: str, ws_message: dict):
        try:
            if ws_message.get("type") != "progress":
                return

            persistence_manager = get_message_persistence_adapter()
            if not persistence_manager.should_persist(ws_message):
                return

            async for db_session in get_db():
                try:
                    await persistence_manager.persist_message(
                        job_id=job_id,
                        ws_message=ws_message,
                        db_session=db_session,
                    )
                    await db_session.commit()
                finally:
                    await db_session.close()
                break
        except Exception:
            logger.error("Failed to persist websocket message", exc_info=True)


manager = ConnectionManager()

__all__ = ["ConnectionManager", "manager"]
