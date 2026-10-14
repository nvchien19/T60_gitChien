"""Read-only, bound database access available to the assistant."""
import re

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.models.tables import Alias, Check, Drug, FdaLabel, Medication, Prescription
from interface.backend.repositories.translations import localize
from src.tools._khoa import khoa


async def localized_drug_labels(db: AsyncSession, name: str) -> list[dict]:
    """Match actual label identity; catalog names alone are not label evidence."""
    aliases = list((await db.scalars(select(Alias.drug_id).where(
        Alias.alias == khoa(name), Alias.status == "ok"))).all())
    ids = set(aliases)
    ids.update((await db.scalars(select(Drug.drug_id).where(or_(
        func.lower(Drug.name) == name.casefold(), func.lower(Drug.name_vi) == name.casefold(),
        func.lower(Drug.base_name) == name.casefold())))).all())
    conditions = [func.lower(FdaLabel.brand_names).contains(name.casefold(), autoescape=True)]
    conditions.extend(cast(FdaLabel.drug_ids, String).contains(f'"{drug_id}"', autoescape=True)
                      for drug_id in ids)
    rows = list((await db.scalars(select(FdaLabel).where(
        FdaLabel.source_id == "openfda", or_(*conditions))
        .order_by(FdaLabel.effective_time.desc(), FdaLabel.label_set_id).limit(20))).all())
    rows = [row for row in rows if khoa(name) in {
        khoa(part.strip()) for part in re.split(r"[;|,\n]+", row.brand_names or "")}
        or (ids and row.all_substances_mapped and set(row.drug_ids or []) == ids)]
    fields = ("boxed_warning", "contraindications", "drug_interactions", "do_not_use",
              "ask_doctor_or_pharmacist")
    translated = await localize(db, "fda_labels", [
        {"id": row.label_set_id, "fields": {key: getattr(row, key) or "" for key in fields}}
        for row in rows])
    return [{"id": row.label_set_id, "date": row.effective_time or "", **vi}
            for row, vi in zip(rows, translated)]


async def drug_in_catalog(db: AsyncSession, name: str) -> bool:
    """Exact catalog presence only: fuzzy suggestions never authorize a match."""
    alias = await db.scalar(select(Alias.drug_id).where(Alias.alias == khoa(name)).limit(1))
    if alias:
        return True
    drug = await db.scalar(select(Drug.drug_id).where(or_(
        func.lower(Drug.name) == name.casefold(),
        func.lower(Drug.name_vi) == name.casefold(),
        func.lower(Drug.base_name) == name.casefold(),
    )).limit(1))
    return bool(drug)


async def assistant_context(db: AsyncSession, prescription_id: str, check_id: str):
    prescription = await db.get(Prescription, prescription_id)
    if prescription is None:
        return None, None, []
    if check_id:
        check = await db.get(Check, check_id)
    else:
        result = await db.execute(
            select(Check).where(Check.prescription_id == prescription_id)
            .order_by(Check.created_at.desc(), Check.id.desc()).limit(1)
        )
        check = result.scalar_one_or_none()
    result = await db.execute(
        select(Medication).where(Medication.prescription_id == prescription_id)
        .order_by(Medication.id)
    )
    return prescription, check, list(result.scalars().all())
