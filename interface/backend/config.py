from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Ra Thuoc — DDI Safety API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # LLM (chi dung cho embed / agent sau; thieu van chay exact-match)
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    embedding_model: str = "text-embedding-3-small"
    similarity_threshold: float = 0.75

    # Database — sqlite dev/test, postgres+pgvector prod
    # dev:  sqlite+aiosqlite:///./data/app.db
    # prod: postgresql+asyncpg://postgres:postgres@db:5432/rathuoc
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    mvp_dir: str = "data/mvp"

    # Vector Store (legacy, giu de tuong thich)
    chroma_persist_dir: str = "./data/chroma"


@lru_cache
def get_settings() -> Settings:
    return Settings()
