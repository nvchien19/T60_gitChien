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
    # Đọc qua Settings vì `.env` không được nạp vào os.environ; biến môi trường thật vẫn được ưu tiên.
    from src.config import get_settings

    s = get_settings()
    api_key = s.deepseek_api_key.strip()
    if not api_key:
        return None
    return ChatOpenAI(
        model=s.deepseek_model or DEFAULT_DEEPSEEK_MODEL,
        api_key=api_key,
        base_url=s.deepseek_base_url or DEFAULT_DEEPSEEK_BASE_URL,
        temperature=s.explain_temperature,
        timeout=s.explain_timeout_s,
        max_retries=1,
    )
