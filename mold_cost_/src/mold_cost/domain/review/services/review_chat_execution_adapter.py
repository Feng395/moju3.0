"""Adapters for chat-oriented review execution."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from ....core.logging import get_logger
from ....core.settings import settings
from ...review.ports import ReviewChatExecutionAdapter

logger = get_logger(__name__)


class WorkflowReviewChatExecutor(ReviewChatExecutionAdapter):
    """Review chat executor backed by the shared LLM configuration."""

    def __init__(self, *, max_history_rounds: int = 5):
        self._max_history_rounds = max_history_rounds

    async def generate_completion_suggestion(
        self,
        prompt: str,
        context_data: dict[str, Any],
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个模具制造领域的专家，擅长根据零件信息推理缺失的参数。"
                    "请根据零件编号、加工说明、热处理等信息，推理出合理的尺寸和材质。"
                    "回答要简洁明了，直接给出补全建议。"
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
        try:
            return await self._call_llm(messages, temperature=0.2, max_tokens=500)
        except Exception as exc:
            logger.warning("Fallback to local completion suggestion: %s", exc, exc_info=True)
            missing_fields = context_data.get("missing_fields") or []
            if missing_fields:
                joined = "、".join(str(field) for field in missing_fields)
                return f"请优先补全以下字段：{joined}。"
            return "请根据当前零件信息补全缺失字段后继续审核。"

    async def chat(
        self,
        job_id: str,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any] | None,
    ) -> str:
        response = ""
        async for chunk in self.chat_stream(job_id=job_id, message=message, history=history, current_data=current_data):
            response += chunk
        return response

    async def chat_stream(
        self,
        job_id: str,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any] | None,
    ) -> AsyncIterator[str]:
        messages = self._build_chat_messages(message=message, history=history, current_data=current_data or {})
        try:
            async for chunk in self._call_llm_stream(messages):
                yield chunk
        except Exception as exc:
            logger.error("Review chat stream failed: %s", exc, exc_info=True)
            yield f"\n\n抱歉，处理您的消息时出现错误：{exc}"

    def _build_chat_messages(
        self,
        *,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any],
    ) -> list[dict[str, str]]:
        context_info = self._build_context_info(current_data)
        system_prompt = (
            "你是一个模具数据审核助手。\n\n"
            f"当前审核数据概览：\n{context_info}\n\n"
            "你的职责：\n"
            "1. 理解用户的修改需求\n"
            "2. 解析自然语言指令\n"
            "3. 提供友好的确认和建议\n"
            "4. 支持多轮对话\n\n"
            "重要限制：\n"
            "- 你只能回答与模具数据核算、审核、修改、价格计算相关的问题\n"
            "- 对于与核算无关的话题，请礼貌说明你只能处理审核相关问题\n"
            "- 请使用简洁、专业的语言回答用户"
        )
        messages = [{"role": "system", "content": system_prompt}]
        for item in history[-self._max_history_rounds :]:
            role = str(item.get("role", "user"))
            content = str(item.get("content", ""))
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})
        return messages

    @staticmethod
    def _build_context_info(data: dict[str, Any]) -> str:
        info_parts: list[str] = []
        for table_name, records in data.items():
            if records:
                info_parts.append(f"- {table_name}: {len(records)} 条记录")

        if data.get("subgraphs"):
            info_parts.append("\n子图详情：")
            for subgraph in data["subgraphs"][:3]:
                info_parts.append(
                    f"  - {subgraph.get('subgraph_id')}: "
                    f"材质={subgraph.get('material')}, "
                    f"重量={subgraph.get('weight')}kg"
                )

        return "\n".join(info_parts) if info_parts else "暂无数据"

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> str:
        from openai import AsyncOpenAI

        http_client = httpx.AsyncClient(timeout=settings.LLM_TIMEOUT, headers={"User-Agent": "curl/8.0"})
        try:
            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                http_client=http_client,
                default_headers={"User-Agent": "curl/8.0"},
            )
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        finally:
            await http_client.aclose()

    async def _call_llm_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        from openai import AsyncOpenAI

        http_client = httpx.AsyncClient(timeout=settings.LLM_TIMEOUT, headers={"User-Agent": "curl/8.0"})
        try:
            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                http_client=http_client,
                default_headers={"User-Agent": "curl/8.0"},
            )
            stream = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                stream=True,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=2000,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        finally:
            await http_client.aclose()


InteractionAgentReviewChatExecutor = WorkflowReviewChatExecutor
