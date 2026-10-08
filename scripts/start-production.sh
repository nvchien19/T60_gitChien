#!/bin/sh
set -eu
alembic upgrade heads
python scripts/import_food_translations.py
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
