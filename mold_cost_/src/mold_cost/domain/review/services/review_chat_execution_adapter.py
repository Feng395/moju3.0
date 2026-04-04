"""Adapters for chat-oriented review execution."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, AsyncIterator

import httpx

from ....core.logging import get_logger
from ...review.ports import ReviewChatExecutionAdapter

logger = get_logger(__name__)


class InteractionAgentReviewChatExecutor(ReviewChatExecutionAdapter):
    """Keep route-compatible review chat while shrinking non-chat InteractionAgent usage."""

    def __init__(self, agent_factory: Callable[[], Any] | None = None):
        self._agent_factory = agent_factory or self._default_agent_factory
        self._llm_base_url = os.getenv("OPENAI_BASE_URL", "https://qwen3.qyagent.top/v1")
        self._llm_api_key = os.getenv("OPENAI_API_KEY", "sk-xxx")
        self._llm_model = os.getenv("OPENAI_MODEL", "Qwen3-30B-A3B-Instruct")
        self._llm_timeout = float(os.getenv("LLM_TIMEOUT", "30"))

    async def generate_completion_suggestion(
        self,
        prompt: str,
        context_data: dict[str, Any],
    ) -> str:
        # 中文注释：补全建议不再穿过 InteractionAgent 私有方法，直接走同源 LLM 配置。
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
            async with httpx.AsyncClient(
                timeout=self._llm_timeout,
                headers={"User-Agent": "curl/8.0"},
            ) as client:
                response = await client.post(
                    f"{self._llm_base_url}/chat/completions",
                    json={
                        "model": self._llm_model,
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 500,
                    },
                    headers={
                        "Authorization": f"Bearer {self._llm_api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Fallback to InteractionAgent completion suggestion: %s", exc, exc_info=True)
            agent = self._agent_factory()
            return await agent._generate_completion_suggestion(prompt, context_data)

    async def chat(
        self,
        job_id: str,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any] | None,
    ) -> str:
        # 中文注释：review/chat 路由仍保持 legacy 协议，先不在本轮重写会话式 chat。
        agent = self._agent_factory()
        return await agent.chat(job_id=job_id, message=message, history=history, current_data=current_data)

    async def chat_stream(
        self,
        job_id: str,
        message: str,
        history: list[dict[str, Any]],
        current_data: dict[str, Any] | None,
    ) -> AsyncIterator[str]:
        agent = self._agent_factory()
        async for chunk in agent.chat_stream(
            job_id=job_id,
            message=message,
            history=history,
            current_data=current_data,
        ):
            yield chunk

    @staticmethod
    def _default_agent_factory():
        from agents.interaction_agent import InteractionAgent

        return InteractionAgent()
