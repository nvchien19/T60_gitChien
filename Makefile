.PHONY: run test lint format typecheck check clean

CORE := src/
WEB := interface/backend/

run:
	uvicorn interface.backend.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

# ruff tach 2 lop: loi rieng cho loi AI core, rieng cho loi backend web
lint:
	ruff check $(CORE) tests/
	ruff check $(WEB)

format:
	ruff format $(CORE) $(WEB) tests/

typecheck:
	mypy $(CORE)

check: lint format test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
