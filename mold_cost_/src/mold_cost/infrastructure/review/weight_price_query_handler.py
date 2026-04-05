"""Src 侧的按重量计算详情查询 handler。"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from sqlalchemy import select

from ...core.logging import get_logger
from ..db.repositories.chat_history_repository import ChatHistoryRepository
from .review_action_handlers import BaseReviewActionHandler, ReviewActionResult

logger = get_logger(__name__)


class WeightPriceQueryReviewActionHandler(BaseReviewActionHandler):
    """查询按重量计算详情，并优先使用 src 侧基础设施能力。"""

    _REFERENCE_PRONOUNS = ("它", "那个", "这个", "那", "这")
    _SUBGRAPH_PREFIXES = (
        r"UP_JIAT",
        r"PS_JIAT",
        r"LOW_JIAT",
        r"UP_ITEM",
        r"PSITEM",
        r"LOW_ITEM",
        r"DIE2_P",
        r"PS2_P",
        r"PPS2_P",
        r"PH2_P",
        r"LB2_P",
        r"UP_P",
        r"UB_P",
        r"PH_P",
        r"PU_P",
        r"PPS_P",
        r"PS_P",
        r"DIE_P",
        r"GU_P",
        r"LB_P",
        r"TEMP[12]",
        r"ST[123]",
        r"DIE2",
        r"PS2",
        r"PPS2",
        r"PH2",
        r"LB2",
        r"STRIP",
        r"PPS",
        r"DIE",
        r"CAM",
        r"BOL",
        r"UP",
        r"LP",
        r"PS",
        r"PH",
        r"UB",
        r"PU",
        r"LB",
        r"EB",
        r"EJ",
        r"CV",
        r"CJ",
        r"CB",
        r"GU",
        r"RP",
        r"CP",
        r"TP",
        r"BP",
        r"SP",
        r"MP",
        r"PP",
        r"U[12]",
        r"B[12]",
    )
    _SUBGRAPH_PATTERN = re.compile(
        rf"((?:{'|'.join(_SUBGRAPH_PREFIXES)})[-_]?(?:\d{{2}}|[A-Z]+\d+))",
        re.IGNORECASE,
    )
    _FIELD_LABELS = {
        "length_mm": "长度(mm)",
        "width_mm": "宽度(mm)",
        "thickness_mm": "厚度(mm)",
        "material": "材料",
        "matched_sub_category": "匹配材料子类",
        "density": "密度",
        "unit": "单位",
        "formula": "公式",
        "weight": "重量(kg)",
        "matched_range": "匹配区间",
        "rule_price": "规则单价(元/kg)",
        "sub_category": "规则子类",
        "weight_price": "按重量价格(元)",
        "category": "分类",
        "status": "状态",
    }

    def __init__(
        self,
        *,
        chat_history_repository: ChatHistoryRepository | None = None,
        use_chat_history: bool | None = None,
        history_limit: int = 50,
    ) -> None:
        super().__init__(pending_action_store=None)
        self._chat_history_repository = chat_history_repository or ChatHistoryRepository()
        self._use_chat_history = (
            use_chat_history
            if use_chat_history is not None
            else os.getenv("USE_CHAT_HISTORY", "true").lower() == "true"
        )
        self._history_limit = history_limit

    async def handle(self, intent_result, job_id: str, context: dict[str, Any], db_session) -> ReviewActionResult:
        del context
        try:
            subgraph_id = await self._resolve_subgraph_id(
                intent_result=intent_result,
                job_id=job_id,
                db_session=db_session,
            )
            if not subgraph_id:
                return ReviewActionResult(
                    status="error",
                    message="请指定要查询的子图，例如：'UP-01 按重量是怎么计算的？'",
                    requires_confirmation=False,
                    data={},
                )

            detail = await self._query_weight_price_detail(
                db_session=db_session,
                job_id=job_id,
                subgraph_id=subgraph_id,
            )
            if detail is None:
                return ReviewActionResult(
                    status="ok",
                    message=(
                        f"{subgraph_id} 暂无按重量计算详情。\n\n"
                        "可能原因：\n"
                        "1. 该子图还未执行按重量计算\n"
                        "2. 计算详情尚未保存到数据库"
                    ),
                    requires_confirmation=False,
                    data={"subgraph_id": subgraph_id},
                )

            weight_price_steps = self._normalize_weight_price_steps(getattr(detail, "weight_price_steps", None))
            if not weight_price_steps:
                return ReviewActionResult(
                    status="ok",
                    message=f"{subgraph_id} 暂无按重量计算的详情数据。",
                    requires_confirmation=False,
                    data={"subgraph_id": subgraph_id},
                )

            return ReviewActionResult(
                status="ok",
                message=self._format_weight_price_steps(subgraph_id, weight_price_steps),
                requires_confirmation=False,
                data={
                    "subgraph_id": subgraph_id,
                    "weight_price_steps": weight_price_steps,
                },
            )
        except Exception as exc:
            logger.error("Weight price query review action failed", exc_info=True)
            return ReviewActionResult(
                status="error",
                message=f"查询按重量计算详情失败：{exc}",
                requires_confirmation=False,
                data={},
            )

    async def _resolve_subgraph_id(self, *, intent_result, job_id: str, db_session) -> str | None:
        parameters = getattr(intent_result, "parameters", {}) or {}
        subgraph_id = parameters.get("subgraph_id")
        if not subgraph_id:
            subgraph_ids = parameters.get("subgraph_ids") or []
            if subgraph_ids:
                subgraph_id = subgraph_ids[0]

        if not self._use_chat_history:
            return subgraph_id

        history_subgraph_id = await self._infer_subgraph_from_history(db_session=db_session, job_id=job_id)
        if not subgraph_id:
            return history_subgraph_id

        raw_message = getattr(intent_result, "raw_message", "") or ""
        # 中文注释：用户用“它/这个”等代词追问时，优先信任最近对话上下文中的子图。
        if raw_message and any(pronoun in raw_message for pronoun in self._REFERENCE_PRONOUNS):
            return history_subgraph_id or subgraph_id
        return subgraph_id

    async def _infer_subgraph_from_history(self, *, db_session, job_id: str) -> str | None:
        history = await self._chat_history_repository.get_recent_session_history(
            db_session,
            session_id=job_id,
            limit=self._history_limit,
        )
        if not history:
            return None

        # 中文注释：先看最近用户消息，再看助手消息，尽量贴近用户当前追问对象。
        prioritized_messages = [
            *[message for message in reversed(history) if message.get("role") == "user"],
            *[message for message in reversed(history) if message.get("role") == "assistant"],
        ]
        for message in prioritized_messages:
            content = message.get("content", "")
            matches = self._SUBGRAPH_PATTERN.findall(content)
            if matches:
                return matches[0].upper()
        return None

    async def _query_weight_price_detail(self, *, db_session, job_id: str, subgraph_id: str):
        from shared.models import ProcessingCostCalculationDetail

        result = await db_session.execute(
            select(ProcessingCostCalculationDetail).where(
                ProcessingCostCalculationDetail.subgraph_id == subgraph_id,
                ProcessingCostCalculationDetail.job_id == job_id,
            )
        )
        detail = result.scalar_one_or_none()
        if detail is not None:
            return detail

        result = await db_session.execute(
            select(ProcessingCostCalculationDetail).where(
                ProcessingCostCalculationDetail.subgraph_id.like(f"%_{subgraph_id}"),
                ProcessingCostCalculationDetail.job_id == job_id,
            )
        )
        matches = result.scalars().all()
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        return min(matches, key=lambda item: len(getattr(item, "subgraph_id", "")))

    def _normalize_weight_price_steps(self, weight_price_steps: Any) -> list[dict[str, Any]]:
        if not weight_price_steps:
            return []

        steps = weight_price_steps
        if isinstance(steps, str):
            steps = json.loads(steps)

        if isinstance(steps, list) and steps and isinstance(steps[0], dict) and "steps" in steps[0]:
            steps = steps[0]["steps"]

        if not isinstance(steps, list):
            return []
        return [step for step in steps if isinstance(step, dict)]

    def _format_weight_price_steps(self, subgraph_id: str, weight_price_steps: list[dict[str, Any]]) -> str:
        lines = [f"{subgraph_id} 的按重量计算详情：", ""]
        for index, step in enumerate(weight_price_steps, start=1):
            step_name = str(step.get("step") or f"步骤 {index}")
            lines.append(f"{index}. {step_name}")
            for key, value in step.items():
                if key == "step":
                    continue
                display_key = self._FIELD_LABELS.get(key, key)
                lines.append(f"   - {display_key}: {self._stringify_value(value)}")
            lines.append("")
        return "\n".join(lines).rstrip()

    @staticmethod
    def _stringify_value(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
