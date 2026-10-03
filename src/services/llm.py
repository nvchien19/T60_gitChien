from langchain_openai import ChatOpenAI

from src.config import get_settings


def get_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
        temperature=settings.llm_temperature,
    )


def get_explainer_llm() -> ChatOpenAI | None:
    """LLM giải thích tương tác (DeepSeek, API tương thích OpenAI). None nếu chưa điền DEEPSEEK_API_KEY."""
    settings = get_settings()
    if not settings.deepseek_api_key.strip():
        return None
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key.strip(),
        base_url=settings.deepseek_base_url,
        temperature=settings.explain_temperature,
        timeout=settings.explain_timeout_s,
        max_retries=1,
    )
