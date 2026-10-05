"""Cấu hình của lõi AI (`src`).

Một nguồn sự thật duy nhất là `interface.backend.config`. Lõi AI và web cùng đọc
chung để `DATABASE_URL`, `EXPLAIN_VERIFY`, `DEEPSEEK_*`... không bị lệch nhau.

`Settings` và `get_settings` được re-export, nên `from src.config import get_settings`
vẫn chạy được như trước khi tách lớp.
"""

from interface.backend.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
