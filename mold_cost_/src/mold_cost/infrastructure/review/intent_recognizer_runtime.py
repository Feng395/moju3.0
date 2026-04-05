"""Src-owned runtime for review intent recognition."""

from __future__ import annotations

import os
from typing import Any

from agents.intent_types import IntentResult, IntentType

from ...core.logging import get_logger

logger = get_logger(__name__)


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() == "true"


class SrcReviewIntentRecognizer:
    """Recognize straightforward review intents locally, then fall back to legacy."""

    _FEATURE_KEYWORDS = ("特征识别", "识别特征", "重新识别", "跑特征", "重跑特征", "识别一下", "再识别", "识别")
    _PRICE_KEYWORDS = ("重新计算", "重算", "更新价格", "计价", "算一下", "calculate", "price")
    _WEIGHT_PRICE_KEYWORDS = ("按重量计算", "重量计算", "模架按重量", "按重量算价格", "重量价格", "weight price", "weight calculation")
    _GENERAL_CHAT_KEYWORDS = ("你好", "您好", "hello", "hi", "帮助", "帮我", "怎么用", "能做什么", "你是谁")
    _CONCEPT_KEYWORDS = ("模架", "冲头", "刀口入块")

    def __init__(self, *, fallback_recognizer=None):
        self._fallback_recognizer = fallback_recognizer

    async def recognize(
        self,
        message: str,
        context: dict[str, Any],
        job_id: str | None = None,
        db_session=None,
    ) -> IntentResult:
        local_result = self._recognize_locally(message=message, context=context)
        if local_result is not None:
            return local_result

        fallback = self._fallback_recognizer
        if fallback is None:
            return IntentResult(intent_type=IntentType.UNKNOWN.value, confidence=0.0, raw_message=message)
        return await fallback.recognize(message, context, job_id=job_id, db_session=db_session)

    async def close(self) -> None:
        if self._fallback_recognizer is not None:
            await self._fallback_recognizer.close()

    def _recognize_locally(self, *, message: str, context: dict[str, Any]) -> IntentResult | None:
        normalized = message.strip()
        lowered = normalized.lower()

        if any(keyword in normalized for keyword in self._WEIGHT_PRICE_KEYWORDS) or any(
            keyword in lowered for keyword in ("weight price", "weight calculation")
        ):
            return self._build_execution_intent(
                message=normalized,
                context=context,
                intent_type=IntentType.WEIGHT_PRICE_CALCULATION.value,
                confidence=0.9,
            )

        if any(keyword in normalized for keyword in self._FEATURE_KEYWORDS):
            return self._build_execution_intent(
                message=normalized,
                context=context,
                intent_type=IntentType.FEATURE_RECOGNITION.value,
                confidence=0.85,
            )

        if any(keyword in normalized for keyword in self._PRICE_KEYWORDS) or any(
            keyword in lowered for keyword in ("calculate", "price")
        ):
            return self._build_execution_intent(
                message=normalized,
                context=context,
                intent_type=IntentType.PRICE_CALCULATION.value,
                confidence=0.8,
            )

        if self._looks_like_general_chat(normalized):
            return IntentResult(
                intent_type=IntentType.GENERAL_CHAT.value,
                confidence=0.75,
                parameters={},
                raw_message=normalized,
                reasoning="recognized by src general-chat rule",
            )

        return None

    def _build_execution_intent(
        self,
        *,
        message: str,
        context: dict[str, Any],
        intent_type: str,
        confidence: float,
    ) -> IntentResult:
        parameters = self._extract_execution_parameters(message=message, context=context)
        return IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            parameters=parameters,
            raw_message=message,
            reasoning="recognized by src execution-intent rule",
        )

    def _extract_execution_parameters(self, *, message: str, context: dict[str, Any]) -> dict[str, Any]:
        explicit_ids = self._extract_subgraph_ids(message=message, context=context)
        if explicit_ids:
            return {"subgraph_ids": explicit_ids}

        for keyword in self._CONCEPT_KEYWORDS:
            if keyword in message:
                return {"keyword": keyword}
        return {"subgraph_ids": []}

    @staticmethod
    def _get_raw_data(context: dict[str, Any]) -> dict[str, Any]:
        return context.get("raw_data") or context

    def _extract_subgraph_ids(self, *, message: str, context: dict[str, Any]) -> list[str]:
        raw_data = self._get_raw_data(context)
        found: list[str] = []
        for subgraph in raw_data.get("subgraphs", []):
            subgraph_id = subgraph.get("subgraph_id")
            if not subgraph_id:
                continue
            short_name = subgraph_id.split("_", 1)[1] if "_" in subgraph_id else subgraph_id
            if subgraph_id in message or short_name in message:
                found.append(short_name)
        return found

    def _looks_like_general_chat(self, message: str) -> bool:
        if any(keyword in message for keyword in self._GENERAL_CHAT_KEYWORDS):
            return True
        if len(message) <= 12 and not any(ch.isdigit() for ch in message):
            return message.endswith(("?", "？")) and not any(
                keyword in message for keyword in ("价格", "特征", "重量", "修改", "材质", "多少", "为什么")
            )
        return False


class LegacyIntentRecognizerFactory:
    """Create the original recognizer only when src rules cannot resolve the intent."""

    def create(self):
        from agents.intent_recognizer import IntentRecognizer

        return IntentRecognizer(
            use_llm=_env_flag("USE_LLM", default=False),
            use_chat_history=_env_flag("USE_CHAT_HISTORY", default=True),
        )


class SrcReviewIntentRecognizerFactory:
    """Build the default review recognizer with src-first detection."""

    def __init__(self, *, fallback_factory=None):
        self._fallback_factory = fallback_factory or LegacyIntentRecognizerFactory()

    def create(self) -> SrcReviewIntentRecognizer:
        fallback = self._fallback_factory.create() if self._fallback_factory is not None else None
        recognizer = SrcReviewIntentRecognizer(fallback_recognizer=fallback)
        logger.info("Created src-first review intent recognizer")
        return recognizer
