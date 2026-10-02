"""Embed interaction_mechanisms.description -> embedding (8465 dong).

Co OPENAI_API_KEY: goi text-embedding-3-small. Khong co: skip (exact-match van chay).
    python scripts/embed_mechanisms.py [--database-url ...] [--limit 0]
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from interface.backend.config import get_settings
from interface.backend.db.models.tables import InteractionMechanism
from interface.backend.db.session import SessionLocal


async def main(db_url: str, limit: int):
    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-your"):
        print("SKIP: thieu OPENAI_API_KEY that — exact-match van chay.")
        return
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    async with SessionLocal() as s:
        q = select(InteractionMechanism).where(InteractionMechanism.embedding.is_(None))
        if limit:
            q = q.limit(limit)
        rows = list((await s.execute(q)).scalars().all())
        print(f"can embed: {len(rows)}")
        for r in rows:
            text = f"{r.mechanism_type or ''}: {r.description} {r.management or ''}"[:8000]
            emb = await client.embeddings.create(model=settings.embedding_model, input=text)
            r.embedding = emb.data[0].embedding
            await s.commit()
    print("DONE")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    asyncio.run(main(a.database_url, a.limit))
