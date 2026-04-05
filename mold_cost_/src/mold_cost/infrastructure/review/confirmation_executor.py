"""Review confirmation executor owned by src/mold_cost."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable

import httpx

from ...core.settings import settings
from ..db.repositories.review_repository_adapter import LegacyReviewRepositoryAdapter
from .pending_action_store import RedisReviewPendingActionStore

RequestExecutor = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class ReviewConfirmationExecutorAdapter:
    """Confirm pending review actions within src/mold_cost."""

    def __init__(
        self,
        *,
        pending_action_store=None,
        review_repository=None,
        request_executor: RequestExecutor | None = None,
    ):
        self._pending_action_store = pending_action_store or RedisReviewPendingActionStore()
        self._review_repository = review_repository or LegacyReviewRepositoryAdapter()
        self._request_executor = request_executor or self._post_json

    async def handle_confirmation(
        self,
        *,
        job_id: str,
        user_id: str,
        db_session,
    ) -> dict[str, Any]:
        pending_action = await self._pending_action_store.load(job_id)
        if not pending_action:
            return {
                "status": "error",
                "message": "未找到待确认的操作",
            }

        action_type = pending_action.get("action_type")
        if action_type == "DATA_MODIFICATION":
            result = await self._confirm_data_modification(job_id=job_id, pending_action=pending_action, db_session=db_session)
        elif action_type == "FEATURE_RECOGNITION":
            result = await self._confirm_api_action(
                action_type=action_type,
                pending_action=pending_action,
                api_url=settings.FEATURE_REPROCESS_API_URL,
                success_message="特征识别任务已提交",
            )
        elif action_type == "PRICE_CALCULATION":
            result = await self._confirm_api_action(
                action_type=action_type,
                pending_action=pending_action,
                api_url=settings.PRICING_RECALCULATE_API_URL,
                success_message="价格计算任务已提交",
            )
        elif action_type == "WEIGHT_PRICE_CALCULATION":
            result = await self._confirm_api_action(
                action_type=action_type,
                pending_action=pending_action,
                api_url=pending_action.get("api_url") or settings.WEIGHT_PRICE_API_URL,
                success_message="按重量计算任务已提交",
            )
        else:
            result = {
                "status": "error",
                "message": f"未知的操作类型: {action_type}",
            }

        if result.get("status") == "ok":
            await self._pending_action_store.delete(job_id)
        return result

    async def _confirm_data_modification(
        self,
        *,
        job_id: str,
        pending_action: dict[str, Any],
        db_session,
    ) -> dict[str, Any]:
        modified_data = pending_action.get("modified_data")
        if not modified_data:
            return {
                "status": "error",
                "message": "未找到修改后的数据",
            }

        try:
            normalized_data = self._convert_datetime_fields(modified_data)
            await self._review_repository.update_all_review_data(
                db_session,
                job_id,
                normalized_data,
            )
            if hasattr(db_session, "commit"):
                await db_session.commit()
            return {
                "status": "ok",
                "message": "数据修改已保存",
                "data": {
                    "action_type": "DATA_MODIFICATION",
                    "changes_count": len(pending_action.get("changes", [])),
                },
            }
        except Exception:
            if hasattr(db_session, "rollback"):
                await db_session.rollback()
            raise

    async def _confirm_api_action(
        self,
        *,
        action_type: str,
        pending_action: dict[str, Any],
        api_url: str,
        success_message: str,
    ) -> dict[str, Any]:
        api_params = pending_action.get("api_params")
        if not api_params:
            return {
                "status": "error",
                "message": "未找到 API 参数",
            }

        try:
            result = await self._request_executor(api_url, api_params)
        except httpx.TimeoutException:
            return {
                "status": "error",
                "message": f"{action_type} 服务响应超时",
            }
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "message": f"{action_type} API 调用失败: HTTP {exc.response.status_code}",
                "details": {
                    "status_code": exc.response.status_code,
                    "response": exc.response.text[:200],
                },
            }

        return {
            "status": "ok",
            "message": success_message,
            "data": {
                "action_type": action_type,
                "task_id": (result.get("data") or {}).get("task_id"),
                "subgraph_ids": api_params.get("subgraph_ids"),
                "api_response": result,
            },
        }

    @staticmethod
    def _convert_datetime_fields(data: dict[str, Any]) -> dict[str, Any]:
        datetime_fields = {"modified_at", "created_at", "updated_at"}
        for table_name, records in data.items():
            if not isinstance(records, list):
                continue
            for record in records:
                for field in datetime_fields:
                    value = record.get(field)
                    if isinstance(value, str):
                        try:
                            record[field] = datetime.fromisoformat(value)
                        except ValueError:
                            continue
        return data

    @staticmethod
    async def _post_json(api_url: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=float(settings.API_TIMEOUT)) as client:
            response = await client.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
