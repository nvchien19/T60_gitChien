"""Ham khoa() — phai KHOP data/build_ddi.py de tra aliases.csv."""

import re
import unicodedata


def khoa(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.lower().replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9%]+", " ", s).strip()
