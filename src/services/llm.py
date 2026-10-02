"""LLM client của lõi AI.

Cấu hình do backend inject (`get_llm(model=..., api_key=..., temperature=...)`),
fallback đọc biến môi trường — `src` không import pydantic-settings của web.
"""

import os

from langchain_openai import ChatOpenAI

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7


def get_llm(
    model: str | None = None,
    api_key: str | None = None,
    temperature: float | None = None,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or os.getenv("MODEL_NAME") or DEFAULT_MODEL,
        api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
        temperature=(
            temperature if temperature is not None
            else float(os.getenv("LLM_TEMPERATURE", DEFAULT_TEMPERATURE))
        ),
    )
