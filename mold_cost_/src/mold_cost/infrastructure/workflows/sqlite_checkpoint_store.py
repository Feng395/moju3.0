"""Shared SQLite-backed durable checkpoint store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SqliteCheckpointStore:
    """Persist workflow checkpoints into a shared SQLite database."""

    def __init__(self, db_path: Path, *, namespace: str):
        self._db_path = Path(db_path)
        self._namespace = namespace
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def save(self, *, job_id: str, state: dict[str, Any], checkpoint: dict[str, Any]) -> Path:
        payload = {
            "job_id": job_id,
            "thread_id": checkpoint.get("thread_id") or job_id,
            "state": state,
            "checkpoint": checkpoint,
        }
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_checkpoints(namespace, job_id, thread_id, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(namespace, job_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    payload_json = excluded.payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (self._namespace, job_id, payload["thread_id"], encoded_payload),
            )
            connection.commit()
        return self._db_path

    def load(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM workflow_checkpoints
                WHERE namespace = ? AND job_id = ?
                """,
                (self._namespace, job_id),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row[0])
        if not isinstance(payload, dict):
            return None
        payload.setdefault("job_id", job_id)
        payload.setdefault("thread_id", job_id)
        payload.setdefault("state", {})
        payload.setdefault("checkpoint", {})
        return payload

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                    namespace TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(namespace, job_id)
                )
                """,
            )
            connection.commit()
