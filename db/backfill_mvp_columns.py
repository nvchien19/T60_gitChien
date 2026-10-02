"""Backfill cot moi them (migration b7e2c1d94a30) tu data/mvp/*.csv vao Postgres.

Migration Alembic chi them cot rong nen can script nay de nap gia tri that.
Chay lai duoc nhieu lan (idempotent), khong xoa du lieu hien co.

Cach dung:
    python db/backfill_mvp_columns.py

Ghi chu: `data/` bi .gitignore nen migration khong duoc phu thuoc CSV;
script rieng giup clone moi / moi may deu backfill duoc.
"""

import csv
import os
import pathlib
import sys

import psycopg2
import psycopg2.extras

ROOT = pathlib.Path(__file__).resolve().parent.parent
MVP = ROOT / "data" / "mvp"


def _db_url() -> str:
    """Lay DATABASE_URL tu env, bo driver async de dung psycopg2."""
    url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/rathuoc"
    )
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )


def _rows(table: str) -> list[dict]:
    path = MVP / f"{table}.csv"
    if not path.exists():
        sys.exit(f"thieu {path}: can data/mvp/*.csv de backfill")
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return value.strip().lower() in {"true", "1", "yes", "y", "t"}


def _int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def backfill_drugs(cur) -> int:
    sql = """
        UPDATE drugs d SET source_id = s.source_id, n_products = s.n_products
        FROM (VALUES %s) AS s(drug_id, source_id, n_products)
        WHERE d.drug_id = s.drug_id
    """
    data = [(r["drug_id"], r["source_id"] or None, _int(r["n_products"])) for r in _rows("drugs")]
    return _exec(cur, sql, data, ("text", "text", "integer"))


def backfill_products(cur) -> int:
    sql = """
        UPDATE products p SET packaging = s.packaging
        FROM (VALUES %s) AS s(product_id, packaging)
        WHERE p.product_id = s.product_id
    """
    data = [(_int(r["product_id"]), r["packaging"] or None) for r in _rows("products")]
    return _exec(cur, sql, data, ("bigint", "text"))


def backfill_food(cur) -> int:
    sql = """
        UPDATE food_interactions f SET drug_name = s.drug_name
        FROM (VALUES %s) AS s(drug_id, food, drug_name)
        WHERE f.drug_id = s.drug_id AND f.food = s.food
    """
    data = [(r["drug_id"], r["food"], r["drug_name"] or None) for r in _rows("food_interactions")]
    return _exec(cur, sql, data, ("text", "text", "text"))


def backfill_disease(cur) -> int:
    sql = """
        UPDATE disease_interactions d SET drug_name = s.drug_name
        FROM (VALUES %s) AS s(drug_id, disease, drug_name)
        WHERE d.drug_id = s.drug_id AND d.disease = s.disease
    """
    data = [
        (r["drug_id"], r["disease"], r["drug_name"] or None)
        for r in _rows("disease_interactions")
    ]
    return _exec(cur, sql, data, ("text", "text", "text"))


def backfill_ara(cur) -> int:
    sql = """
        UPDATE ara_interactions a SET victim = s.victim, ara_text = s.ara_text
        FROM (VALUES %s) AS s("table", ara_class, victim, ara_text)
        WHERE a."table" = s."table" AND a.ara_class = s.ara_class
    """
    data = [
        (r["table"], r["ara_class"], r["victim"] or None, r["ara_text"] or None)
        for r in _rows("ara_interactions")
    ]
    return _exec(cur, sql, data, ("text", "text", "text", "text"))


def backfill_pk(cur) -> int:
    sql = """
        UPDATE pk_ddi p
        SET perpetrator_name = s.perpetrator_name,
            perpetrator_drugbank = s.perpetrator_drugbank,
            victim_name = s.victim_name,
            victim_drugbank = s.victim_drugbank
        FROM (VALUES %s)
             AS s(perpetrator_id, perpetrator_name, perpetrator_drugbank,
                  victim_id, victim_name, victim_drugbank)
        WHERE p.perpetrator_id = s.perpetrator_id AND p.victim_id = s.victim_id
    """
    data = [
        (
            r["perpetrator_id"],
            r["perpetrator_name"] or None,
            r["perpetrator_drugbank"] or None,
            r["victim_id"],
            r["victim_name"] or None,
            r["victim_drugbank"] or None,
        )
        for r in _rows("pk_ddi")
    ]
    return _exec(cur, sql, data, ("text", "text", "text", "text", "text", "text"))


def backfill_fda(cur) -> int:
    sql = """
        UPDATE fda_labels f
        SET product_type = s.product_type,
            all_substances_mapped = s.all_substances_mapped,
            do_not_use = s.do_not_use,
            ask_doctor_or_pharmacist = s.ask_doctor_or_pharmacist,
            n_labels = s.n_labels,
            source_url = s.source_url
        FROM (VALUES %s)
             AS s(label_set_id, product_type, all_substances_mapped, do_not_use,
                  ask_doctor_or_pharmacist, n_labels, source_url)
        WHERE f.label_set_id = s.label_set_id
    """
    data = [
        (
            r["label_set_id"],
            r["product_type"] or None,
            _bool(r["all_substances_mapped"]),
            r["do_not_use"] or None,
            r["ask_doctor_or_pharmacist"] or None,
            _int(r["n_labels"]),
            r["source_url"] or None,
        )
        for r in _rows("fda_labels")
    ]
    return _exec(
        cur,
        sql,
        data,
        ("text", "text", "boolean", "text", "text", "integer", "text"),
    )


def backfill_dosage(cur) -> int:
    sql = """
        UPDATE dosage_form_rules r
        SET drug_name = s.drug_name, other_drug_name = s.other_drug_name
        FROM (VALUES %s) AS s(rule_id, other_drug_id, drug_name, other_drug_name)
        WHERE r.rule_id = s.rule_id AND r.other_drug_id = s.other_drug_id
    """
    data = [
        (
            r["rule_id"],
            r["other_drug_id"],
            r["drug_name"] or None,
            r["other_drug_name"] or None,
        )
        for r in _rows("dosage_form_rules")
    ]
    return _exec(cur, sql, data, ("text", "text", "text", "text"))


def load_ingredient_map(cur) -> int:
    cur.execute("TRUNCATE ingredient_map")
    sql = """
        INSERT INTO ingredient_map
            (key, example_name, n_products, method, score, status,
             drug_ids, drug_names, dav_drug_id)
        VALUES %s
    """
    data = [
        (
            r["key"],
            r["example_name"],
            _int(r["n_products"]) or 0,
            r["method"],
            _int(r["score"]) or 0,
            r["status"],
            r["drug_ids"] or None,
            r["drug_names"] or None,
            r["dav_drug_id"] or None,
        )
        for r in _rows("ingredient_map")
    ]
    psycopg2.extras.execute_values(cur, sql, data, page_size=500)
    return len(data)


def _exec(cur, sql: str, data: list, casts: tuple[str, ...]) -> int:
    """UPDATE ... FROM (VALUES ...) bang execute_values.

    Cast tuong minh bat buoc: Postgres suy literals trong VALUES thanh `text`,
    neu khong se loi `operator does not exist: bigint = text` khi join khoa so.
    """
    if not data:
        return 0
    template = "(" + ", ".join(f"%s::{c}" for c in casts) + ")"
    psycopg2.extras.execute_values(cur, sql, data, template=template, page_size=1000)
    return len(data)


TASKS = [
    ("drugs", backfill_drugs),
    ("products", backfill_products),
    ("food_interactions", backfill_food),
    ("disease_interactions", backfill_disease),
    ("ara_interactions", backfill_ara),
    ("pk_ddi", backfill_pk),
    ("fda_labels", backfill_fda),
    ("dosage_form_rules", backfill_dosage),
    ("ingredient_map", load_ingredient_map),
]


def main() -> None:
    conn = psycopg2.connect(_db_url())
    try:
        with conn, conn.cursor() as cur:
            for name, fn in TASKS:
                print(f"{name:22s} {fn(cur):>7d} dong")
    finally:
        conn.close()
    print("backfill xong")


if __name__ == "__main__":
    main()