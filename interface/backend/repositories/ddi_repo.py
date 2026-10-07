"""Repository: truy van DB duy nhat o day (theo BE_DEVELOPMENT.md W0)."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.models.tables import (
    Alias,
    AraInteraction,
    DiseaseInteraction,
    DosageFormRule,
    Drug,
    DrugInteraction,
    DuplicationClass,
    FdaLabel,
    FoodInteraction,
    InteractionMechanism,
    PkDdi,
    ProductIngredient,
    Source,
)


async def get_aliases_exact(db: AsyncSession, key: str, limit: int = 20) -> list[Alias]:
    r = await db.execute(select(Alias).where(Alias.alias == key).limit(limit))
    return list(r.scalars().all())


async def get_aliases_for_fuzzy(db: AsyncSession, limit: int = 20000) -> list[Alias]:
    # chi lay cot can thiet; 63k dong van OK, gioi han de nhe RAM
    r = await db.execute(
        select(Alias.alias, Alias.drug_id, Alias.alias_type, Alias.source_id,
               Alias.status, Alias.drug_name).limit(limit)
    )
    return r.all()


async def get_drug_names(db: AsyncSession, drug_ids: list[str]) -> dict[str, str]:
    if not drug_ids:
        return {}
    r = await db.execute(select(Drug.drug_id, Drug.name).where(Drug.drug_id.in_(drug_ids)))
    return {d: n for d, n in r.all()}


async def search_drugs(db: AsyncSession, q: str, limit: int = 10) -> list[dict]:
    like = f"%{q}%"
    r = await db.execute(
        select(Drug.drug_id, Drug.name, Drug.name_vi, Drug.base_name, Drug.atc_code)
        .where(or_(Drug.name.ilike(like), Drug.base_name.ilike(like), Drug.name_vi.ilike(like)))
        .limit(limit)
    )
    return [dict(zip(["drug_id", "name", "name_vi", "base_name", "atc_code"], row)) for row in r.all()]


async def get_pair_interactions(db: AsyncSession, a: str, b: str) -> list[dict]:
    # query ca 2 chieu (CSV sap numeric, khong dam bao string order)
    r = await db.execute(
        select(DrugInteraction, InteractionMechanism)
        .outerjoin(InteractionMechanism,
                   DrugInteraction.mechanism_id == InteractionMechanism.mechanism_id)
        .where(or_((DrugInteraction.drug_a == a) & (DrugInteraction.drug_b == b),
                   (DrugInteraction.drug_a == b) & (DrugInteraction.drug_b == a)))
    )
    out = []
    for inter, mech in r.all():
        out.append({
            "pair": [inter.drug_a, inter.drug_b], "severity": inter.severity,
            "mechanism": (mech.description if mech else ""),
            "management": (mech.management if mech else "") or "",
            "mechanism_type": inter.mechanism_type,
            "citations": [{"source_id": inter.source_id, "label": "DDInter 2.0",
                           "source_url": inter.source_url or ""}],
            "match_type": "exact", "layer": "ddi_l1",
        })
    return out


async def get_food_for_drugs(db: AsyncSession, drug_ids: list[str]) -> list[FoodInteraction]:
    if not drug_ids:
        return []
    r = await db.execute(select(FoodInteraction).where(FoodInteraction.drug_id.in_(drug_ids)))
    return list(r.scalars().all())


async def get_disease_for_drugs(db: AsyncSession, drug_ids: list[str],
                                mesh_ids: list[str]) -> list[DiseaseInteraction]:
    if not drug_ids or not mesh_ids:
        return []
    r = await db.execute(select(DiseaseInteraction).where(
        DiseaseInteraction.drug_id.in_(drug_ids), DiseaseInteraction.mesh_id.in_(mesh_ids)))
    return list(r.scalars().all())


async def get_duplication_for_drugs(db: AsyncSession, drug_ids: list[str]) -> list[DuplicationClass]:
    if not drug_ids:
        return []
    r = await db.execute(select(DuplicationClass).where(DuplicationClass.drug_id.in_(drug_ids)))
    return list(r.scalars().all())


async def get_dosage_rules_for(db: AsyncSession, drug_ids: list[str]) -> list[DosageFormRule]:
    if not drug_ids:
        return []
    s = set(drug_ids)
    r = await db.execute(
        select(DosageFormRule).where(
            or_(DosageFormRule.drug_id.in_(s), DosageFormRule.other_drug_id.in_(s)))
    )
    return list(r.scalars().all())


async def get_ara_for(db: AsyncSession, drug_ids: list[str]) -> list[AraInteraction]:
    # 272 dong: nap het roi loc o Python (mang JSON)
    r = await db.execute(select(AraInteraction))
    rows = list(r.scalars().all())
    s = set(drug_ids)
    return [x for x in rows if s.intersection(set(x.victim_drug_ids or []))
            or s.intersection(set(x.ara_drug_ids or []))]


async def get_mechanisms_with_embedding(db: AsyncSession) -> list[InteractionMechanism]:
    r = await db.execute(
        select(InteractionMechanism).where(InteractionMechanism.embedding.is_not(None)))
    return list(r.scalars().all())


async def get_pk_for_pair(db: AsyncSession, a: str, b: str) -> list[PkDdi]:
    r = await db.execute(
        select(PkDdi).where(or_(
            (PkDdi.perpetrator_id == a) & (PkDdi.victim_id == b),
            (PkDdi.perpetrator_id == b) & (PkDdi.victim_id == a))))
    return list(r.scalars().all())


async def get_fda_for_drugs(db: AsyncSession, drug_ids: list[str], limit: int = 5) -> list[FdaLabel]:
    # drug_ids la JSON list; SQLite khong query JSON array hieu qua -> nap gioi han roi loc Python
    r = await db.execute(select(FdaLabel).limit(2000))
    s = set(drug_ids)
    return [x for x in r.scalars().all() if s.intersection(set(x.drug_ids or []))][:limit]


async def get_product_drugs(db: AsyncSession, product_id: int) -> list[ProductIngredient]:
    r = await db.execute(
        select(ProductIngredient).where(ProductIngredient.product_id == product_id))
    return list(r.scalars().all())


async def list_sources(db: AsyncSession) -> list[Source]:
    r = await db.execute(select(Source))
    return list(r.scalars().all())


async def count_coverage(db: AsyncSession) -> dict:
    out = {}
    for model, key in [(Drug, "drugs"), (DrugInteraction, "pairs"),
                       (InteractionMechanism, "mechanisms"), (FoodInteraction, "foods")]:
        r = await db.execute(select(func.count()).select_from(model))
        out[key] = r.scalar() or 0
    return out
