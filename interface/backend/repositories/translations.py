"""Read translations only; API requests never call a translation provider."""
import hashlib

from sqlalchemy import select
from interface.backend.db.models.tables import ContentTranslation

def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

async def localize(db, table: str, records: list[dict]) -> list[dict]:
    if not records:
        return []
    ids = {str(record["id"]) for record in records}
    result = await db.execute(select(ContentTranslation).where(
        ContentTranslation.source_table == table,
        ContentTranslation.source_id.in_(ids), ContentTranslation.language == "vi"))
    cached = {(t.source_id, t.field): t for t in result.scalars().all()}
    output = []
    for record in records:
        values = {}
        missing = []
        machine = False
        for field, original in record["fields"].items():
            original = original or ""
            translation = cached.get((str(record["id"]), field))
            if original and translation and translation.source_hash == source_hash(original) and translation.translated_text.strip():
                values[field] = translation.translated_text
                machine = machine or not translation.reviewed
            else:
                values[field] = original
                if original:
                    missing.append(field)
        output.append({**values, "untranslated_fields": missing, "machine_translation": machine})
    return output
