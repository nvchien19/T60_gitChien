"""Async engine/session. SQLite (dev/test) + Postgres+pgvector (prod)."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from interface.backend.config import get_settings

settings = get_settings()

_url = settings.database_url
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _url.startswith("sqlite://") and "+aiosqlite" not in _url:
    _url = _url.replace("sqlite://", "sqlite+aiosqlite://", 1)

connect_args = {}
if _url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(_url, echo=False, connect_args=connect_args)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        yield session
