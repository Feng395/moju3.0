"""Src-owned runtime for review intent recognition."""

from __future__ import annotations

import os
import re
from typing import Any

from agents.intent_types import INTENT_KEYWORDS, IntentResult, IntentType

from ...core.logging import get_logger

logger = get_logger(__name__)


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() == "true"


class SrcReviewIntentRecognizer:
    """Recognize straightforward review intents locally, then fall back to legacy."""

    _VERIFICATION_KEYWORDS = ("对吗", "正确吗", "是否正确", "有问题吗", "是不是", "对不对")
    _DATA_MODIFICATION_KEYWORDS = ("改为", "修改为", "设置为", "改成", "换成", "变成", "调整为")
    _DATA_MODIFICATION_ACTION_KEYWORDS = ("修改", "更改", "调整", "改一下", "改", "换", "设成", "设为")
    _FEATURE_KEYWORDS = ("特征识别", "识别特征", "重新识别", "跑特征", "重跑特征", "识别一下", "再识别", "识别")
    _PRICE_KEYWORDS = ("重新计算", "重算", "更新价格", "计价", "算一下", "calculate", "price")
    _QUERY_KEYWORDS = tuple(INTENT_KEYWORDS[IntentType.QUERY_DETAILS])
    _WEIGHT_PRICE_KEYWORDS = ("按重量计算", "重量计算", "模架按重量", "按重量算价格", "重量价格", "weight price", "weight calculation")
    _WEIGHT_PRICE_QUERY_KEYWORDS = tuple(INTENT_KEYWORDS[IntentType.WEIGHT_PRICE_QUERY])
    _GENERAL_CHAT_KEYWORDS = ("你好", "您好", "hello", "hi", "帮助", "帮我", "怎么用", "能做什么", "你是谁")
    _FEATURE_PRICE_CONCEPT_KEYWORDS = ("模板", "模架", "冲头", "刀口入块")
    _WEIGHT_PRICE_CONCEPT_KEYWORDS = ("模架", "冲头", "刀口入块")
    _CONTEXT_REFERENCE_KEYWORDS = ("刚才", "刚刚", "上次", "之前", "刚才那个", "按刚才", "按上次", "延续", "继续")
    _CONTEXT_TARGET_KEYWORDS = ("这个零件", "那个零件", "该零件", "这个", "那个", "它", "这条", "那条")
    _CONTEXT_QUERY_KEYWORDS = ("判断逻辑", "逻辑", "规则", "依据", "怎么判", "怎么判断", "为什么", "按哪套")
    _STRUCTURED_QUERY_KEYWORDS = (
        "多少",
        "几",
        "吗",
        "呢",
        "？",
        "?",
        "怎么算",
        "怎么来的",
        "费用",
        "价格",
        "时间",
        "总价",
        "总费用",
        "线长",
        "数据",
    )
    _FOLLOW_UP_QUERY_PREFIXES = ("那", "这", "它", "这个", "那个", "这边", "那边")
    _FOLLOW_UP_QUERY_SUFFIXES = ("呢", "吗", "呀", "啊", "？", "?")
    _SINGLE_CODE_PATTERN = r"(?<![A-Z0-9])([LWMGKZ])(?![A-Z0-9])"

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

        if any(keyword in normalized for keyword in self._VERIFICATION_KEYWORDS):
            return self._build_query_intent(message=normalized, context=context, confidence=0.9)

        if self._looks_like_weight_price_query(normalized, lowered):
            subgraph_id = self._extract_single_subgraph_id(message=normalized, context=context)
            return IntentResult(
                intent_type=IntentType.WEIGHT_PRICE_QUERY.value,
                confidence=0.88,
                parameters={"subgraph_id": subgraph_id} if subgraph_id else {},
                raw_message=normalized,
                reasoning="recognized by src weight-price-query rule",
            )

        if any(keyword in normalized for keyword in self._WEIGHT_PRICE_KEYWORDS) or any(
            keyword in lowered for keyword in ("weight price", "weight calculation")
        ):
            return self._build_execution_intent(
                message=normalized,
                context=context,
                intent_type=IntentType.WEIGHT_PRICE_CALCULATION.value,
                confidence=0.9,
                concept_keywords=self._WEIGHT_PRICE_CONCEPT_KEYWORDS,
            )

        contextual_intent = self._recognize_contextual_reference_intent(message=normalized, context=context)
        if contextual_intent is not None:
            return contextual_intent

        if self._looks_like_short_follow_up_query(normalized):
            # 中文注释：这类“那材料费呢”短追问只在 src 侧识别查询类型，具体零件继续交给 handler 走历史推断。
            return self._build_query_intent(message=normalized, context=context, confidence=0.76)

        if self._looks_like_query_details(normalized, lowered):
            return self._build_query_intent(message=normalized, context=context, confidence=0.82)

        if any(keyword in normalized for keyword in self._FEATURE_KEYWORDS):
            return self._build_execution_intent(
                message=normalized,
                context=context,
                intent_type=IntentType.FEATURE_RECOGNITION.value,
                confidence=0.85,
                concept_keywords=self._FEATURE_PRICE_CONCEPT_KEYWORDS,
            )

        if any(keyword in normalized for keyword in self._PRICE_KEYWORDS) or any(
            keyword in lowered for keyword in ("calculate", "price")
        ):
            return self._build_execution_intent(
                message=normalized,
                context=context,
                intent_type=IntentType.PRICE_CALCULATION.value,
                confidence=0.8,
                concept_keywords=self._FEATURE_PRICE_CONCEPT_KEYWORDS,
            )

        if self._looks_like_data_modification(normalized):
            return IntentResult(
                intent_type=IntentType.DATA_MODIFICATION.value,
                confidence=0.76,
                parameters={},
                raw_message=normalized,
                reasoning="recognized by src data-modification rule",
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
        concept_keywords: tuple[str, ...] = (),
    ) -> IntentResult:
        parameters = self._extract_execution_parameters(
            message=message,
            context=context,
            concept_keywords=concept_keywords,
        )
        return IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            parameters=parameters,
            raw_message=message,
            reasoning="recognized by src execution-intent rule",
        )

    def _extract_execution_parameters(
        self,
        *,
        message: str,
        context: dict[str, Any],
        concept_keywords: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        explicit_ids = self._extract_subgraph_ids(message=message, context=context)
        if explicit_ids:
            return {"subgraph_ids": explicit_ids}

        for keyword in concept_keywords:
            if keyword in message:
                return {"keyword": keyword}
        return {"subgraph_ids": []}

    def _build_query_intent(self, *, message: str, context: dict[str, Any], confidence: float) -> IntentResult:
        subgraph_id = self._extract_single_subgraph_id(message=message, context=context)
        query_type = self._extract_query_type(message)
        parameters: dict[str, Any] = {}
        if subgraph_id:
            parameters["subgraph_id"] = subgraph_id
        if query_type:
            parameters["query_type"] = query_type
        return IntentResult(
            intent_type=IntentType.QUERY_DETAILS.value,
            confidence=confidence,
            parameters=parameters,
            raw_message=message,
            reasoning="recognized by src query-details rule",
        )

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

    def _extract_single_subgraph_id(self, *, message: str, context: dict[str, Any]) -> str | None:
        # 中文注释：单个工艺代码（如 L/W/M）不是子图 ID，必须交给后续 handler 通过历史消息推断。
        if self._mentions_single_machining_code(message, context):
            return None

        explicit_ids = self._extract_subgraph_ids(message=message, context=context)
        if explicit_ids:
            return explicit_ids[0]
        return None

    def _looks_like_query_details(self, message: str, lowered: str) -> bool:
        if any(keyword in message for keyword in self._QUERY_KEYWORDS):
            return True
        if any(keyword in lowered for keyword in ("why", "detail", "details", "breakdown")):
            return True
        query_type = self._extract_query_type(message)
        if query_type and any(keyword in message for keyword in self._STRUCTURED_QUERY_KEYWORDS):
            return True
        return False

    def _looks_like_weight_price_query(self, message: str, lowered: str) -> bool:
        if any(keyword in message for keyword in self._WEIGHT_PRICE_QUERY_KEYWORDS):
            return True
        return any(keyword in lowered for keyword in ("weight price details", "weight calculation details"))

    def _looks_like_data_modification(self, message: str) -> bool:
        if any(keyword in message for keyword in self._DATA_MODIFICATION_KEYWORDS):
            return True
        return "修改" in message and any(token in message for token in ("为", "成", "到"))

    def _looks_like_short_follow_up_query(self, message: str) -> bool:
        compact = re.sub(r"\s+", "", message)
        query_type = self._extract_query_type(compact)
        if query_type is None:
            return False
        if self._looks_like_data_modification(compact) or self._looks_like_contextual_data_modification(compact):
            return False

        has_follow_up_prefix = any(compact.startswith(prefix) for prefix in self._FOLLOW_UP_QUERY_PREFIXES)
        has_question_suffix = compact.endswith(self._FOLLOW_UP_QUERY_SUFFIXES)
        return len(compact) <= 12 and (has_follow_up_prefix or has_question_suffix)

    def _extract_query_type(self, message: str) -> str | None:
        if any(keyword in message for keyword in ("线割总价", "线割总费用")):
            return "wire_total"
        if any(keyword in message for keyword in ("线割基础", "基础线割", "线割基础费", "基础加工费")):
            return "wire_base"
        if any(keyword in message for keyword in ("线割特殊", "特殊线割", "特殊工艺费", "特殊加工费")):
            return "wire_special"
        if "线割标准" in message:
            return "wire_standard"
        if any(keyword in message for keyword in ("标准基本费", "标准费")):
            return "standard"
        if any(keyword in message for keyword in ("自找料", "自动找料")):
            return "add_auto_material"
        if "牙孔" in message:
            return "tooth_hole_time"
        if any(keyword in message for keyword in ("NC基本", "NC基础", "NC基准")):
            return "nc_base"
        if any(keyword in message for keyword in ("正面的背面", "正面的背面加工", "正面的背面时间", "正面的背面费用")):
            return "nc_b_view"
        if any(keyword in message for keyword in ("正面", "正面加工", "正面时间", "正面费用")):
            return "nc_z_view"
        if any(keyword in message for keyword in ("侧背", "侧背加工", "侧背时间", "侧背费用")):
            return "nc_c_b"
        if any(keyword in message for keyword in ("主视图", "主视图加工", "主视图时间", "主视图费用")):
            return "nc_z"
        if any(keyword in message for keyword in ("背面", "背面加工", "背面时间", "背面费用")):
            return "nc_b"
        if any(keyword in message for keyword in ("侧面", "侧面加工", "侧面时间", "侧面费用")):
            return "nc_c"
        if any(keyword in message for keyword in ("NC开粗",)):
            return "nc_roughing"
        if any(keyword in message for keyword in ("NC精铣",)):
            return "nc_milling"
        if any(keyword in message for keyword in ("NC钻床", "钻床")):
            return "nc_drilling"
        if any(keyword in message for keyword in ("NC", "主视图", "背面", "侧面", "侧背", "正面的背面", "正面")):
            return "nc"
        if "水磨" in message:
            return "water_mill"
        if "线长" in message:
            return "wire"
        if "线割" in message:
            return "wire"
        if "材料费" in message:
            return "material"
        if "热处理" in message:
            return "heat"
        if "重量" in message and "按重量" not in message:
            return "weight"
        if any(keyword in message for keyword in ("总价", "总费用")):
            return "total"
        return None

    def _mentions_single_machining_code(self, message: str, context: dict[str, Any]) -> bool:
        if not re.search(self._SINGLE_CODE_PATTERN, message):
            return False
        explicit_ids = self._extract_subgraph_ids(message=message, context=context)
        return not explicit_ids

    def _looks_like_general_chat(self, message: str) -> bool:
        if any(keyword in message for keyword in self._GENERAL_CHAT_KEYWORDS):
            return True
        if len(message) <= 12 and not any(ch.isdigit() for ch in message):
            return message.endswith(("?", "？")) and not any(
                keyword in message for keyword in ("价格", "特征", "重量", "修改", "材质", "多少", "为什么")
            )
        return False

    def _recognize_contextual_reference_intent(
        self,
        *,
        message: str,
        context: dict[str, Any],
    ) -> IntentResult | None:
        if not self._looks_like_contextual_reference(message):
            return None

        if self._looks_like_contextual_data_modification(message):
            return IntentResult(
                intent_type=IntentType.DATA_MODIFICATION.value,
                confidence=0.72,
                parameters={},
                raw_message=message,
                reasoning="recognized by src contextual data-modification rule",
            )

        if any(keyword in message for keyword in self._FEATURE_KEYWORDS):
            return self._build_execution_intent(
                message=message,
                context=context,
                intent_type=IntentType.FEATURE_RECOGNITION.value,
                confidence=0.74,
            )

        if any(keyword in message for keyword in self._PRICE_KEYWORDS):
            return self._build_execution_intent(
                message=message,
                context=context,
                intent_type=IntentType.PRICE_CALCULATION.value,
                confidence=0.74,
            )

        if any(keyword in message for keyword in self._WEIGHT_PRICE_KEYWORDS):
            return self._build_execution_intent(
                message=message,
                context=context,
                intent_type=IntentType.WEIGHT_PRICE_CALCULATION.value,
                confidence=0.74,
            )

        if self._looks_like_contextual_query(message):
            return self._build_query_intent(message=message, context=context, confidence=0.7)
        return None

    def _looks_like_contextual_reference(self, message: str) -> bool:
        return any(keyword in message for keyword in self._CONTEXT_REFERENCE_KEYWORDS) or any(
            keyword in message for keyword in self._CONTEXT_TARGET_KEYWORDS
        )

    def _looks_like_contextual_data_modification(self, message: str) -> bool:
        if any(keyword in message for keyword in self._DATA_MODIFICATION_KEYWORDS):
            return True
        return any(keyword in message for keyword in self._DATA_MODIFICATION_ACTION_KEYWORDS) and any(
            token in message for token in ("材质", "长度", "宽度", "厚度", "数量", "热处理", "工艺", "备注")
        )

    def _looks_like_contextual_query(self, message: str) -> bool:
        if any(keyword in message for keyword in self._CONTEXT_QUERY_KEYWORDS):
            return True
        return "处理" in message and any(keyword in message for keyword in self._CONTEXT_TARGET_KEYWORDS)


class LegacyIntentRecognizerFactory:
    """Create the original recognizer only when src rules cannot resolve the intent."""

    def create(self):
        from agents.intent_recognizer import IntentRecognizer

        return IntentRecognizer(
            use_llm=_env_flag("USE_LLM", default=False),
            use_chat_history=_env_flag("USE_CHAT_HISTORY", default=True),
        )


class LazyFallbackRecognizer:
    """Delay legacy recognizer construction until src rules真的无法命中。"""

    def __init__(self, factory):
        self._factory = factory
        self._instance = None

    def _ensure_instance(self):
        if self._instance is None and self._factory is not None:
            self._instance = self._factory.create()
        return self._instance

    async def recognize(self, message, context, job_id=None, db_session=None):
        instance = self._ensure_instance()
        if instance is None:
            return IntentResult(intent_type=IntentType.UNKNOWN.value, confidence=0.0, raw_message=message)
        return await instance.recognize(message, context, job_id=job_id, db_session=db_session)

    async def close(self) -> None:
        if self._instance is not None:
            await self._instance.close()


class SrcReviewIntentRecognizerFactory:
    """Build the default review recognizer with src-first detection."""

    def __init__(self, *, fallback_factory=None):
        self._fallback_factory = fallback_factory or LegacyIntentRecognizerFactory()

    def create(self) -> SrcReviewIntentRecognizer:
        fallback = LazyFallbackRecognizer(self._fallback_factory) if self._fallback_factory is not None else None
        recognizer = SrcReviewIntentRecognizer(fallback_recognizer=fallback)
        logger.info("Created src-first review intent recognizer")
        return recognizer
