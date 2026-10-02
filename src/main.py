"""Compatibility shim — `uvicorn src.main:app` hoạt động như template gốc.

App FastAPI thật nằm ở `interface/backend/main.py`. File này chỉ re-export
nên không kéo FastAPI/SQLAlchemy vào `src/`; rule một chiều
`interface.backend → src` (xem `ARCHITECTURE.md`) vẫn giữ nguyên về mặt code,
dù có một import ngược duy nhất tại đây.

Canonical entry point vẫn là:
    uvicorn interface.backend.main:app --reload --port 8000
"""

from interface.backend.main import app

__all__ = ["app"]
