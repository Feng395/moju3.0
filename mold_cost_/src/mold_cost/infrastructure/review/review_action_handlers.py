"""Src-owned review action handlers for simple confirmation-based intents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...core.logging import get_logger
from ...core.settings import settings
from ...domain.review.services.review_chat_execution_adapter import WorkflowReviewChatExecutor
from .pending_action_store import RedisReviewPendingActionStore

logger = get_logger(__name__)


@dataclass(slots=True)
class ReviewActionResult:
    """Small action-result payload shared by src-owned review handlers."""

    status: str
    message: str
    requires_confirmation: bool = False
    pending_action: dict[str, Any] | None = None
    data: dict[str, Any] = field(default_factory=dict)


class BaseReviewActionHandler:
    """Common helpers for review handlers that only prepare pending actions."""

    # 中文注释：概念词展开沿用旧逻辑，先保证用户可见行为不回退，再逐步收口剩余复杂 handler。
    CONCEPT_KEYWORD_MAPPING = {
        "冲头": ["切边冲头", "切冲冲头", "冲子", "废料刀", "冲头"],
        "刀口入块": ["刀口入子", "切边入子", "冲孔入子", "凹模"],
        "模架": ["模座", "垫脚", "托板"],
    }

    def __init__(self, *, pending_action_store: RedisReviewPendingActionStore | None = None):
        self._pending_action_store = pending_action_store or RedisReviewPendingActionStore()

    @property
    def pending_action_store(self) -> RedisReviewPendingActionStore:
        return self._pending_action_store

    def _get_raw_data(self, context: dict[str, Any]) -> dict[str, Any]:
        return context.get("raw_data") or context

    def _get_display_view(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        display_view = context.get("display_view")
        return display_view if isinstance(display_view, list) else []

    def _get_all_subgraph_ids(self, context: dict[str, Any]) -> list[str]:
        raw_data = self._get_raw_data(context)
        subgraphs = raw_data.get("subgraphs", [])
        return [sg.get("subgraph_id") for sg in subgraphs if sg.get("subgraph_id")]

    def _resolve_subgraph_ids(self, subgraph_ids: list[str], context: dict[str, Any]) -> list[str]:
        raw_data = self._get_raw_data(context)
        short_to_full: dict[str, str] = {}
        for subgraph in raw_data.get("subgraphs", []):
            full_id = subgraph.get("subgraph_id")
            if not full_id:
                continue
            short_name = self._get_short_name(full_id)
            short_to_full[short_name] = full_id
            short_to_full[full_id] = full_id

        resolved: list[str] = []
        for name in subgraph_ids:
            resolved.append(short_to_full.get(name, name))
        return resolved

    @staticmethod
    def _get_short_name(subgraph_id: str) -> str:
        if "_" in subgraph_id:
            return subgraph_id.split("_", 1)[1]
        return subgraph_id

    def _expand_concept_to_keywords(self, keyword: str) -> list[str]:
        return self.CONCEPT_KEYWORD_MAPPING.get(keyword, [keyword])

    def _match_subgraphs_by_keyword(self, keyword: str, context: dict[str, Any]) -> list[str]:
        matched: list[str] = []
        for item in self._get_display_view(context):
            part_name = item.get("part_name") or ""
            if keyword not in part_name:
                continue
            source = item.get("_source") or {}
            subgraph_id = source.get("subgraph_id")
            if subgraph_id:
                matched.append(subgraph_id)
        return matched

    def _match_subgraphs_by_concept(
        self,
        keyword: str,
        context: dict[str, Any],
    ) -> tuple[list[str], dict[str, list[str]]]:
        expanded_keywords = self._expand_concept_to_keywords(keyword)
        match_results = {
            item_keyword: self._match_subgraphs_by_keyword(item_keyword, context)
            for item_keyword in expanded_keywords
        }

        deduped_ids: list[str] = []
        seen: set[str] = set()
        for subgraph_ids in match_results.values():
            for subgraph_id in subgraph_ids:
                if subgraph_id in seen:
                    continue
                seen.add(subgraph_id)
                deduped_ids.append(subgraph_id)
        return deduped_ids, match_results

    def _format_match_summary(self, keyword: str, match_results: dict[str, list[str]]) -> str:
        if len(match_results) == 1:
            only_ids = next(iter(match_results.values()), [])
            return f"{keyword} 匹配到 {len(only_ids)} 个零件"

        details = [f"{item_keyword}:{len(item_ids)}" for item_keyword, item_ids in match_results.items()]
        total = len({subgraph_id for ids in match_results.values() for subgraph_id in ids})
        return f"{keyword} 共匹配到 {total} 个零件（{', '.join(details)}）"

    def _resolve_target_subgraph_ids(
        self,
        *,
        intent_result,
        context: dict[str, Any],
        empty_message: str,
    ) -> tuple[list[str] | None, ReviewActionResult | None]:
        parameters = getattr(intent_result, "parameters", {}) or {}
        subgraph_ids = parameters.get("subgraph_ids")
        keyword = parameters.get("keyword")

        if keyword:
            subgraph_ids, match_results = self._match_subgraphs_by_concept(keyword, context)
            if not subgraph_ids:
                return None, ReviewActionResult(status="error", message=f"未找到包含“{keyword}”的零件")
            logger.info("Review keyword match resolved: keyword=%s, summary=%s", keyword, self._format_match_summary(keyword, match_results))
        elif not subgraph_ids:
            subgraph_ids = self._get_all_subgraph_ids(context)
        else:
            subgraph_ids = self._resolve_subgraph_ids(list(subgraph_ids), context)

        if not subgraph_ids:
            return None, ReviewActionResult(status="error", message=empty_message)
        return subgraph_ids, None

    async def _save_pending_action(self, *, job_id: str, payload: dict[str, Any]) -> None:
        await self.pending_action_store.save(job_id, payload)

    @staticmethod
    def _build_confirmation_message(*, verb: str, subgraph_ids: list[str]) -> str:
        display_names = [BaseReviewActionHandler._get_short_name(subgraph_id) for subgraph_id in subgraph_ids]
        if len(display_names) <= 5:
            return f"将{verb}以下子图：{', '.join(display_names)}，请确认"
        return f"将{verb} {len(display_names)} 个子图（{', '.join(display_names[:3])} ...），请确认"


class FeatureRecognitionReviewActionHandler(BaseReviewActionHandler):
    """Prepare feature re-recognition requests inside src/mold_cost."""

    async def handle(self, intent_result, job_id: str, context: dict[str, Any], db_session) -> ReviewActionResult:
        del db_session
        try:
            subgraph_ids, error = self._resolve_target_subgraph_ids(
                intent_result=intent_result,
                context=context,
                empty_message="当前没有可识别的子图",
            )
            if error is not None or subgraph_ids is None:
                return error or ReviewActionResult(status="error", message="当前没有可识别的子图")

            api_params = {
                "job_id": job_id,
                "subgraph_ids": subgraph_ids,
                "options": {
                    "force_reprocess": True,
                    "update_existing": True,
                },
            }
            await self._save_pending_action(
                job_id=job_id,
                payload={
                    "action_type": "FEATURE_RECOGNITION",
                    "api_params": api_params,
                    "subgraph_ids": subgraph_ids,
                },
            )
            return ReviewActionResult(
                status="ok",
                message=self._build_confirmation_message(verb="重新识别特征的", subgraph_ids=subgraph_ids),
                requires_confirmation=True,
                pending_action={"action_type": "FEATURE_RECOGNITION", "subgraph_ids": subgraph_ids},
                data={"subgraph_ids": subgraph_ids, "count": len(subgraph_ids)},
            )
        except Exception as exc:
            logger.error("Feature recognition review action failed", exc_info=True)
            return ReviewActionResult(status="error", message=f"处理特征识别请求失败：{exc}")


class PriceCalculationReviewActionHandler(BaseReviewActionHandler):
    """Prepare price recalculation requests inside src/mold_cost."""

    async def handle(self, intent_result, job_id: str, context: dict[str, Any], db_session) -> ReviewActionResult:
        del db_session
        try:
            subgraph_ids, error = self._resolve_target_subgraph_ids(
                intent_result=intent_result,
                context=context,
                empty_message="当前没有可计算的子图",
            )
            if error is not None or subgraph_ids is None:
                return error or ReviewActionResult(status="error", message="当前没有可计算的子图")

            api_params = {
                "job_id": job_id,
                "subgraph_ids": subgraph_ids,
                "options": {
                    "force_recalculate": True,
                    "skip_search": False,
                },
            }
            await self._save_pending_action(
                job_id=job_id,
                payload={
                    "action_type": "PRICE_CALCULATION",
                    "api_params": api_params,
                    "subgraph_ids": subgraph_ids,
                },
            )
            return ReviewActionResult(
                status="ok",
                message=self._build_confirmation_message(verb="重新计算价格的", subgraph_ids=subgraph_ids),
                requires_confirmation=True,
                pending_action={"action_type": "PRICE_CALCULATION", "subgraph_ids": subgraph_ids},
                data={"subgraph_ids": subgraph_ids, "count": len(subgraph_ids)},
            )
        except Exception as exc:
            logger.error("Price calculation review action failed", exc_info=True)
            return ReviewActionResult(status="error", message=f"处理价格计算请求失败：{exc}")


class WeightPriceCalculationReviewActionHandler(BaseReviewActionHandler):
    """Prepare mold-base weight-pricing requests inside src/mold_cost."""

    def __init__(
        self,
        *,
        pending_action_store: RedisReviewPendingActionStore | None = None,
        weight_price_api_url: str | None = None,
    ):
        super().__init__(pending_action_store=pending_action_store)
        self._weight_price_api_url = weight_price_api_url or settings.WEIGHT_PRICE_API_URL

    async def handle(self, intent_result, job_id: str, context: dict[str, Any], db_session) -> ReviewActionResult:
        del db_session
        try:
            subgraph_ids, error = self._resolve_target_subgraph_ids(
                intent_result=intent_result,
                context=context,
                empty_message="当前没有可计算的子图",
            )
            if error is not None or subgraph_ids is None:
                return error or ReviewActionResult(status="error", message="当前没有可计算的子图")

            api_params = {
                "job_id": job_id,
                "subgraph_ids": subgraph_ids,
                "options": {
                    "force_recalculate": True,
                    "skip_search": False,
                },
            }
            await self._save_pending_action(
                job_id=job_id,
                payload={
                    "action_type": "WEIGHT_PRICE_CALCULATION",
                    "api_url": self._weight_price_api_url,
                    "api_params": api_params,
                    "subgraph_ids": subgraph_ids,
                },
            )
            return ReviewActionResult(
                status="ok",
                message=self._build_confirmation_message(verb="按重量计算模架价格的", subgraph_ids=subgraph_ids),
                requires_confirmation=True,
                pending_action={"action_type": "WEIGHT_PRICE_CALCULATION", "subgraph_ids": subgraph_ids},
                data={"subgraph_ids": subgraph_ids, "count": len(subgraph_ids)},
            )
        except Exception as exc:
            logger.error("Weight price calculation review action failed", exc_info=True)
            return ReviewActionResult(status="error", message=f"处理按重量计算请求失败：{exc}")


class GeneralChatReviewActionHandler(BaseReviewActionHandler):
    """Reply to simple review chat directly from src-owned chat execution."""

    def __init__(
        self,
        *,
        chat_executor: WorkflowReviewChatExecutor | None = None,
    ):
        super().__init__(pending_action_store=None)
        self._chat_executor = chat_executor or WorkflowReviewChatExecutor()

    async def handle(self, intent_result, job_id: str, context: dict[str, Any], db_session) -> ReviewActionResult:
        del db_session
        try:
            # 中文注释：这里直接复用 review chat executor，避免 general chat 继续依赖 legacy action handler。
            response = await self._chat_executor.chat(
                job_id=job_id,
                message=getattr(intent_result, "raw_message", ""),
                history=[],
                current_data=self._get_raw_data(context),
            )
            return ReviewActionResult(
                status="ok",
                message=response or "您好，我可以协助您继续处理模具审核、价格计算和特征识别相关问题。",
                requires_confirmation=False,
                data={},
            )
        except Exception as exc:
            logger.error("General review chat action failed", exc_info=True)
            return ReviewActionResult(
                status="error",
                message=f"抱歉，处理您的消息时出现错误：{exc}",
                data={},
            )
