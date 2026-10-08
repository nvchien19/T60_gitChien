"""Install bundled public DDInter translations without calling a provider."""
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from interface.backend.db.models.tables import ContentTranslation, FoodInteraction
from interface.backend.db.session import SessionLocal, engine
from interface.backend.repositories.translations import source_hash

BUNDLE = Path(__file__).parent / 'assets/food-translations.vi.json'


async def install(db, translations):
    sources = list((await db.execute(select(FoodInteraction))).scalars())
    cached = {(row.source_id, row.field): row for row in (await db.execute(
        select(ContentTranslation).where(ContentTranslation.source_table == 'food_interactions',
                                         ContentTranslation.language == 'vi'))).scalars()}
    saved = kept = missing = 0
    for source in sources:
        for field in ('description', 'management'):
            original = getattr(source, field) or ''
            if not original.strip():
                continue
            digest = source_hash(original)
            existing = cached.get((str(source.id), field))
            if existing and (existing.reviewed or (
                    existing.source_hash == digest and existing.translated_text.strip())):
                kept += 1
                continue
            entry = translations.get(digest) if source.source_id == 'ddinter' else None
            if not entry:
                missing += 1
                continue
            if existing is None:
                existing = ContentTranslation(source_table='food_interactions',
                                              source_id=str(source.id), field=field, language='vi')
                db.add(existing)
            existing.source_hash = digest
            existing.translated_text = entry['text']
            existing.provider = entry['provider']
            existing.reviewed = False
            existing.updated_at = datetime.now(UTC)
            saved += 1
    await db.commit()
    return {'records': len(sources), 'saved': saved, 'kept': kept, 'missing': missing}


async def main():
    bundle = json.loads(BUNDLE.read_text(encoding='utf-8'))
    async with SessionLocal() as db:
        counts = await install(db, bundle['translations'])
        print('Food translations: ' + json.dumps(counts), flush=True)
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
