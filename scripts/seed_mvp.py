"""Seed CSDL that tu data/mvp/*.csv (xem docs/BE_DEVELOPMENT.md muc 4.3).

    python scripts/seed_mvp.py [--mvp-dir data/mvp] [--database-url sqlite+aiosqlite:///./data/app.db]

COPY theo thu tu FK. Idempotent: delete + insert theo tung bang (chon --fresh de xoa het).
Chay offline duoc (khong embed).
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from interface.backend.db.base import Base
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
    Product,
    ProductIngredient,
    Source,
)


def b(v: str) -> bool:
    return (v or "").strip().lower() in ("true", "1", "t", "yes")


def i(v: str, default: int = 0) -> int:
    try:
        return int(float((v or "").strip())) if (v or "").strip() else default
    except ValueError:
        return default


def f(v: str):
    try:
        return float((v or "").strip()) if (v or "").strip() else None
    except ValueError:
        return None


def lst(v: str) -> list:
    return [x.strip() for x in (v or "").split(";") if x.strip()]


def dt(v: str):
    """'2026-09-30' -> date; '2020' -> date(2020,1,1); '' -> None."""
    from datetime import date
    s = (v or "").strip()
    if not s:
        return None
    try:
        if len(s) == 4 and s.isdigit():
            return date(int(s), 1, 1)
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def read_csv(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)


async def seed(mvp: Path, db_url: str, fresh: bool, only: set[str] | None):
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("sqlite://") and "+aiosqlite" not in db_url:
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    eng = create_async_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    mk = async_sessionmaker(eng, expire_on_commit=False)

    seen_pk: set[tuple] = set()

    async def load(model, path: Path, fn, batch: int = 2000, dedupe: bool = False):
        if only and model.__tablename__ not in only:
            print(f"skip {model.__tablename__}")
            return
        rows = [fn(r) for r in read_csv(path)]
        if dedupe:  # pk_ddi co 124 dong trung y hets + perpetrator trong
            uniq = []
            for r in rows:
                if not (r.perpetrator_id and r.victim_id):
                    continue
                k = (r.perpetrator_id, r.victim_id, r.auc_fold_change, r.magnitude)
                if k not in seen_pk:
                    seen_pk.add(k)
                    uniq.append(r)
            rows = uniq
        async with mk() as s:
            if fresh:
                await s.execute(delete(model))
            for j in range(0, len(rows), batch):
                s.add_all(rows[j:j + batch])
                await s.flush()
            await s.commit()
        print(f"{model.__tablename__}: {len(rows)}")

    await load(Source, mvp / "sources.csv", lambda r: Source(
        source_id=r["source_id"], name=r["name"], citation=r.get("citation"),
        url=r.get("url"), license=r.get("license"),
        last_updated=dt(r.get("last_updated", ""))))
    await load(Drug, mvp / "drugs.csv", lambda r: Drug(
        drug_id=r["drug_id"], name=r["name"], name_vi=r.get("name_vi", ""),
        base_name=r.get("base_name") or r["name"], route_variant=r.get("route_variant", ""),
        drugbank_id=r.get("drugbank_id") or None, atc_code=r.get("atc_code") or None,
        drug_type=r.get("drug_type") or None, in_vn=b(r.get("in_vn", "")),
        n_products_valid=i(r.get("n_products_valid", "0")),
        n_interactions=i(r.get("n_interactions", "0"))), batch=1000)
    await load(Alias, mvp / "aliases.csv", lambda r: Alias(
        alias=r["alias"], drug_id=r["drug_id"], alias_type=r.get("alias_type"),
        source_id=r.get("source_id") or "dav", status=r.get("status") or "ok",
        drug_name=r.get("drug_name") or ""), batch=2000)
    await load(Product, mvp / "products.csv", lambda r: Product(
        product_id=i(r["product_id"]), registration_no=r.get("registration_no"),
        name=r["name"], active_ingredients=r.get("active_ingredients"),
        strength=r.get("strength"), dosage_form=r.get("dosage_form"),
        route=r.get("route"), form_group=r.get("form_group"),
        enteric_coated=b(r.get("enteric_coated", "")), modified_release=b(r.get("modified_release", "")),
        category=r.get("category"), manufacturer=r.get("manufacturer"),
        manufacturer_country=r.get("manufacturer_country"), registrant=r.get("registrant"),
        status=r.get("status"), expiry_date=dt(r.get("expiry_date", "")),
        source_id=r.get("source_id") or "dav"), batch=2000)
    await load(ProductIngredient, mvp / "product_ingredients.csv", lambda r: ProductIngredient(
        product_id=i(r["product_id"]), position=i(r.get("position", "1"), 1),
        ingredient=r.get("ingredient", ""), strength=r.get("strength"),
        drug_id=(r.get("drug_id") or None), base_drug_id=r.get("base_drug_id") or None,
        match_method=r.get("match_method"), match_score=i(r.get("match_score", "0")) or None,
        status=r.get("status"), route_match=r.get("route_match"),
        needs_review=b(r.get("needs_review", ""))), batch=2000)
    await load(InteractionMechanism, mvp / "interaction_mechanisms.csv", lambda r: InteractionMechanism(
        mechanism_id=r["mechanism_id"], severity=r.get("severity"),
        mechanism_type=r.get("mechanism_type"), description=r.get("description", ""),
        management=r.get("management") or None, refs=r.get("references") or None,
        n_pairs=i(r.get("n_pairs", "0")), source_id=r.get("source_id") or "ddinter"), batch=1000)
    await load(DrugInteraction, mvp / "drug_interactions.csv", lambda r: DrugInteraction(
        interaction_id=i(r["interaction_id"]), drug_a=r["drug_a"], drug_b=r["drug_b"],
        severity=r["severity"], mechanism_id=r.get("mechanism_id") or None,
        mechanism_type=r.get("mechanism_type"), both_in_vn=b(r.get("both_in_vn", "")),
        source_id=r.get("source_id") or "ddinter", source_url=r.get("source_url") or None), batch=2000)
    await load(FoodInteraction, mvp / "food_interactions.csv", lambda r: FoodInteraction(
        drug_id=r.get("drug_id"), food=r.get("food", ""), food_vi=r.get("food_vi"),
        severity=r.get("severity"), mechanism_type=r.get("mechanism_type"),
        description=r.get("description"), management=r.get("management"),
        refs=r.get("references"), source_id=r.get("source_id") or "ddinter"))
    await load(DiseaseInteraction, mvp / "disease_interactions.csv", lambda r: DiseaseInteraction(
        drug_id=r.get("drug_id"), disease=r.get("disease"), mesh_id=r.get("mesh_id"),
        severity=r.get("severity"), description=r.get("description"),
        refs=r.get("references"), source_id=r.get("source_id") or "ddinter"))
    await load(DuplicationClass, mvp / "duplication_classes.csv", lambda r: DuplicationClass(
        class_name=r["class_name"], drug_id=r["drug_id"], drug_name=r.get("drug_name"),
        max_concurrent=i(r.get("max_concurrent", "1"), 1),
        source_id=r.get("source_id") or "ddinter"))
    await load(AraInteraction, mvp / "ara_interactions.csv", lambda r: AraInteraction(
        table_name=r.get("table"), category=r.get("category") or None,
        victim_drug_ids=lst(r.get("victim_drug_ids", "")), victim_form=r.get("victim_form", ""),
        victim_is_combination=b(r.get("victim_is_combination", "")),
        ara_class=r.get("ara_class"), ara_drug_ids=lst(r.get("ara_drug_ids", "")),
        mechanism=r.get("mechanism"), effect=r.get("effect"), severity=r.get("severity") or None,
        recommendation=r.get("recommendation"), route_scope=r.get("route_scope") or "oral",
        source_id=r.get("source_id") or "patel2020"))
    await load(PkDdi, mvp / "pk_ddi.csv", lambda r: PkDdi(
        perpetrator_id=r["perpetrator_id"], victim_id=r["victim_id"],
        auc_fold_change=f(r.get("auc_fold_change", "")),
        magnitude=r.get("magnitude"), source_id=r.get("source_id") or "pkddip"),
        dedupe=True)
    await load(FdaLabel, mvp / "fda_labels.csv", lambda r: FdaLabel(
        label_set_id=r["label_set_id"], effective_time=r.get("effective_time"),
        route=r.get("route"), substances=r.get("substances"),
        drug_ids=lst(r.get("drug_ids", "")), brand_names=r.get("brand_names"),
        boxed_warning=r.get("boxed_warning"), contraindications=r.get("contraindications"),
        drug_interactions=r.get("drug_interactions"),
        dosage_forms_and_strengths=r.get("dosage_forms_and_strengths"),
        source_id=r.get("source_id") or "openfda"), batch=500)
    await load(DosageFormRule, mvp / "dosage_form_rules.csv", lambda r: DosageFormRule(
        rule_id=r["rule_id"], drug_id=r.get("drug_id") or None,
        drug_route=r.get("drug_route"), drug_form=r.get("drug_form"),
        other_drug_id=r.get("other_drug_id") or None, other_route=r.get("other_route"),
        severity=r.get("severity") or None, action=r.get("action"),
        effect_vi=r.get("effect_vi"), management_vi=r.get("management_vi"),
        evidence=r.get("evidence"), source_url=r.get("source_url"),
        source_id=r.get("source_id") or "openfda"))
    await eng.dispose()
    print("DONE")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mvp-dir", default="data/mvp")
    ap.add_argument("--database-url", default="sqlite+aiosqlite:///./data/app.db")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--only", default="", help="comma list of table names")
    a = ap.parse_args()
    asyncio.run(seed(Path(a.mvp_dir), a.database_url, a.fresh,
                     set(x for x in a.only.split(",") if x) or None))
