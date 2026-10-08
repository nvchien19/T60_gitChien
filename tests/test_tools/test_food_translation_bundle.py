import json
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from interface.backend.db.base import Base
from interface.backend.db.models.tables import ContentTranslation, FoodInteraction
from interface.backend.repositories.translations import localize, source_hash
from scripts.import_food_translations import BUNDLE, install


@pytest.mark.asyncio
async def test_bundle_matches_content_preserves_review_and_skips_changed_evidence(tmp_path):
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path / "translations.db"}')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    # A different source ID must still receive the translation of identical evidence.
    text = 'Source evidence'
    digest = source_hash(text)
    translations = {digest: {'text': 'Bằng chứng nguồn', 'provider': 'deepseek'}}
    async with sessions() as db:
        db.add_all([
            FoodInteraction(id=9001, food='food', description=text, source_id='ddinter'),
            FoodInteraction(id=9002, food='food', description=text, source_id='ddinter'),
            FoodInteraction(id=9003, food='food', description='Changed evidence', source_id='ddinter'),
            FoodInteraction(id=9004, food='food', description=text, source_id='other'),
            ContentTranslation(source_table='food_interactions', source_id='9002',
                               field='description', language='vi', source_hash=digest,
                               translated_text='Chuyên gia đã duyệt', provider='human', reviewed=True),
        ])
        await db.commit()
        result = await install(db, translations)
        assert result == {'records': 4, 'saved': 1, 'kept': 1, 'missing': 2}
        assert (await install(db, translations))['saved'] == 0
        rows = await localize(db, 'food_interactions', [
            {'id': i, 'fields': {'description': text}} for i in (9001, 9002)])
        assert rows[0]['description'] == 'Bằng chứng nguồn'
        assert rows[0]['machine_translation'] and not rows[0]['untranslated_fields']
        assert rows[1]['description'] == 'Chuyên gia đã duyệt'
        assert not rows[1]['machine_translation']
    await engine.dispose()


def test_bundled_public_translations_are_complete():
    bundle = json.loads(Path(BUNDLE).read_text(encoding='utf-8'))
    assert bundle['source'] == 'DDInter 2.0'
    assert bundle['language'] == 'vi'
    assert len(bundle['translations']) == 835
    assert all(len(digest) == 64 and entry['text'].strip()
               for digest, entry in bundle['translations'].items())
