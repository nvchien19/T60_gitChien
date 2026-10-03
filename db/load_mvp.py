"""Nạp data/mvp/*.csv vào Postgres (schema `mvp`) qua `docker compose exec`, không cần driver Python.

Cách dùng (từ thư mục gốc dự án, sau khi `docker compose up -d db`):
    python db/load_mvp.py
"""
import csv
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MVP = ROOT / "data" / "mvp"
PSQL = ["docker", "compose", "exec", "-T", "db", "sh", "-c",
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q']

# Thứ tự nạp theo khóa ngoại
TABLES = ["sources", "drugs", "aliases", "products", "product_ingredients", "interaction_mechanisms",
          "drug_interactions", "food_interactions", "disease_interactions", "duplication_classes",
          "ara_interactions", "pk_ddi", "fda_labels", "dosage_form_rules", "ingredient_map"]


def main():
    schema = (ROOT / "db" / "mvp_schema.sql").read_bytes()
    r = subprocess.run(PSQL[:-1] + [PSQL[-1]], cwd=ROOT, input=schema, capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode("utf-8", "replace"))
    print("schema: ok")

    csv.field_size_limit(2**30)
    for t in TABLES:
        path = MVP / f"{t}.csv"
        with open(path, encoding="utf-8-sig", newline="") as f:
            header = next(csv.reader(f))
        cols = ", ".join(f'"{c}"' for c in header)
        sql = f"COPY mvp.{t} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
        with open(path, "rb") as f:
            cmd = PSQL[:-1] + [PSQL[-1] + " -c \"" + sql.replace('"', '\\"') + "\""]
            r = subprocess.run(cmd, cwd=ROOT, stdin=f, capture_output=True)
        if r.returncode:
            sys.exit(f"{t}: {r.stderr.decode('utf-8', 'replace')}")
        with open(path, encoding="utf-8-sig", newline="") as f:
            n_csv = sum(1 for _ in csv.reader(f)) - 1
        r = subprocess.run(PSQL[:-1] + [PSQL[-1] + f" -tA -c 'SELECT count(*) FROM mvp.{t}'"], cwd=ROOT,
                           capture_output=True)
        n_db = int(r.stdout.decode().strip() or -1)
        if n_db != n_csv:
            sys.exit(f"{t}: CSV có {n_csv} dòng nhưng Postgres có {n_db}")
        print(f"{t:24s} {n_db:>8,} dòng")
    subprocess.run(PSQL[:-1] + [PSQL[-1] + " -c 'ANALYZE'"], cwd=ROOT, check=True)
    print("ANALYZE: ok")


if __name__ == "__main__":
    main()
