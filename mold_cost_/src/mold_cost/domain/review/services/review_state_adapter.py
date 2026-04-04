"""Review state adapter backed by Redis."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from ....application.workflows.review_state import ReviewState
from ....core.logging import get_logger
from ...review.ports import ReviewStateStore

logger = get_logger(__name__)


class RedisReviewStateStore(ReviewStateStore):
    """Serialize workflow state without coupling the graph to Redis details."""

    def __init__(self):
        self._redis_client = None

    @property
    def redis_client(self):
        if self._redis_client is None:
            from api_gateway.utils.redis_client import redis_client

            self._redis_client = redis_client
        return self._redis_client

    @staticmethod
    def _state_key(job_id: str) -> str:
        return f"review:state:{job_id}"

    def build_state(self, job_id: str, **kwargs: Any) -> ReviewState:
        return ReviewState(job_id=job_id, **kwargs)

    def calculate_data_version(self, raw_data: dict[str, Any]) -> dict[str, str]:
        version: dict[str, str] = {}
        for table_name, records in raw_data.items():
            if not isinstance(records, list):
                continue
            for record in records:
                record_id = record.get("subgraph_id") or record.get("feature_id") or record.get("snapshot_id")
                if not record_id:
                    continue
                record_str = json.dumps(record, sort_keys=True, ensure_ascii=False)
                version[f"{table_name}:{record_id}"] = hashlib.md5(record_str.encode("utf-8")).hexdigest()
        return version

    def serialize(self, state: ReviewState) -> dict[str, Any]:
        return state.to_payload()

    async def load(self, job_id: str) -> ReviewState | None:
        data = await self.redis_client.get(self._state_key(job_id))
        if not data:
            return None
        return ReviewState.from_payload(job_id=job_id, payload=json.loads(data))

    async def save(self, state: ReviewState, ex: int = 3600) -> None:
        if ex < 300:
            ex = 300
        await self.redis_client.set(
            self._state_key(state.job_id),
            self._serialize_json(state.to_payload()),
            ex=ex,
        )

    async def renew(self, job_id: str, timeout: int = 3600) -> bool:
        key = self._state_key(job_id)
        if not await self.redis_client.exists(key):
            return False
        await self.redis_client.expire(key, timeout)
        return True

    @staticmethod
    def _serialize_json(data: Any) -> str:
        def default_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        return json.dumps(data, ensure_ascii=False, default=default_handler)
