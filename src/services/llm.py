"""LLM client của lõi AI.

Cấu hình do backend inject (`get_llm(model=..., api_key=..., temperature=...)`),
fallback đọc biến môi trường — `src` không import pydantic-settings của web.
"""

import os

from langchain_openai import ChatOpenAI

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_EXPLAIN_TEMPERATURE = 0.2
DEFAULT_EXPLAIN_TIMEOUT_S = 60.0


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


def get_explainer_llm() -> ChatOpenAI | None:
    """LLM giải thích tương tác (DeepSeek, API tương thích OpenAI). None nếu chưa điền DEEPSEEK_API_KEY."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None
    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL,
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_DEEPSEEK_BASE_URL,
        temperature=float(os.getenv("EXPLAIN_TEMPERATURE") or DEFAULT_EXPLAIN_TEMPERATURE),
        timeout=float(os.getenv("EXPLAIN_TIMEOUT_S") or DEFAULT_EXPLAIN_TIMEOUT_S),
        max_retries=1,
    )
