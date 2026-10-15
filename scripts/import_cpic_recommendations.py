"""Import the pinned CPIC recommendation snapshot into the application database.

Run from the repository root after migrations and drug data are present.
Existing CPIC recommendations are left unchanged; reruns skip the import.
"""

import asyncio
import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import func, select

from interface.backend.db.models.tables import Drug, GeneInteraction, Source
from interface.backend.db.session import SessionLocal

SNAPSHOT = Path(__file__).resolve().parent.parent / "data/cpic/recommendation_view_2026-10-15.json"


def _key(value: str) -> str:
    return " ".join(value.casefold().split())


def _drug_index(drugs: list[tuple[str, str, str]]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for drug_id, name, base_name in drugs:
        for label in (name, base_name):
            if label:
                index[_key(label)].add(drug_id)
    return index


def _recommendation(row: dict, drug_id: str) -> GeneInteraction | None:
    lookup = row.get("lookupkey") or {}
    phenotypes = row.get("phenotypes") or {}
    if not isinstance(lookup, dict) or not isinstance(phenotypes, dict):
        return None
    genes = {gene: value for gene, value in lookup.items()
             if isinstance(gene, str) and isinstance(value, str) and value}
    genes.update({gene: value for gene, value in phenotypes.items()
                  if isinstance(gene, str) and isinstance(value, str) and value})
    if not genes or all(value == "No Result" for value in genes.values()):
        return None
    implications = row.get("implications") or {}
    if not isinstance(implications, dict):
        return None
    return GeneInteraction(
        id=row["recommendationid"], drug_id=drug_id, drug_name=row["drugname"],
        genes=genes, lookupkey=lookup,
        implication_text="; ".join(str(value) for value in implications.values() if value),
        recommendation=row.get("drugrecommendation"),
        classification=row.get("classification"), population=row.get("population"),
        comments=row.get("comments"), guideline_name=row.get("guidelinename"),
        guideline_url=row.get("guidelineurl"), source_id="cpic",
    )


async def main() -> None:
    async with SessionLocal() as db:
        if await db.scalar(select(func.count()).select_from(GeneInteraction)):
            print("CPIC: recommendations already present; skipping import")
            return
        rows = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        ids = [row["recommendationid"] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("CPIC snapshot contains duplicate recommendation IDs")
        drugs = (await db.execute(select(Drug.drug_id, Drug.name, Drug.base_name))).all()
        index = _drug_index(drugs)
        imported = 0
        unmatched: set[str] = set()
        ambiguous: set[str] = set()
        recommendations = []
        for row in rows:
            name = row["drugname"]
            matches = index.get(_key(name), set())
            if not matches:
                unmatched.add(name)
                continue
            if len(matches) != 1:
                ambiguous.add(name)
                continue
            recommendation = _recommendation(row, next(iter(matches)))
            if recommendation is not None:
                recommendations.append(recommendation)
                imported += 1
        if recommendations:
            if await db.get(Source, "cpic") is None:
                db.add(Source(source_id="cpic", name="Clinical Pharmacogenetics Implementation Consortium",
                              citation="CPIC recommendation view, snapshot 2026-10-15",
                              url="https://api.cpicpgx.org/v1/recommendation_view",
                              license="Creative Commons public domain"))
                await db.flush()
            db.add_all(recommendations)
            await db.commit()
        print(f"CPIC: {imported} imported, "
              f"{len(unmatched)} unmatched drugs, {len(ambiguous)} ambiguous drugs")


if __name__ == "__main__":
    asyncio.run(main())
