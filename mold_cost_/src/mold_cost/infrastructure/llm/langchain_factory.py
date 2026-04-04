"""Factory helpers for LangChain models."""

from __future__ import annotations

from ...core.settings import settings


def create_chat_model(**overrides):
    from langchain_openai import ChatOpenAI

    config = {
        "api_key": settings.OPENAI_API_KEY,
        "model": settings.OPENAI_MODEL,
        "base_url": settings.OPENAI_BASE_URL,
        "timeout": settings.LLM_TIMEOUT,
        "temperature": settings.LLM_TEMPERATURE,
    }
    config.update(overrides)
    return ChatOpenAI(**config)
