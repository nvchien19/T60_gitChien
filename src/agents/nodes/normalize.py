"""Node `normalize` — chuẩn hóa danh sách thuốc người dùng nhập.

Tách query thành danh sách tên thuốc, rồi chạy `drug_name_normalizer` trên catalog
do backend inject. `suggest`/`unknown` không auto-accept — đẩy sang `clarify`.
"""

import re
from typing import Any

from src.agents.state import AgentState
from src.tools._khoa import khoa
from src.tools.normalizer import normalize_name

MAX_DRUGS = 50
_SPLIT = re.compile(r"[,;\n/]+|\bvà\b|\bcùng\b|\band\b", re.IGNORECASE)


def split_drugs(query: str) -> list[str]:
    """Tách chuỗi tự do thành danh sách tên thuốc, bỏ trùng, giữ nguyên thứ tự."""
    out: list[str] = []
    seen: set[str] = set()
    for chunk in _SPLIT.split(query or ""):
        name = " ".join(chunk.split())
        if not name or len(name) > 200:
            continue
        key = khoa(name)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(name)
        if len(out) >= MAX_DRUGS:
            break
    return out


async def normalize_node(state: AgentState) -> dict[str, Any]:
    names = state.get("raw_drugs") or split_drugs(state.get("query", ""))
    if not names:
        return {"error": "Không nhận dạng được tên thuốc nào trong câu hỏi."}

    catalog = state.get("catalog") or {}
    aliases = catalog.get("aliases") or []
    drug_names = catalog.get("drug_names") or {}

    normalized: list[dict[str, Any]] = []
    clarifications: list[dict[str, Any]] = []
    for raw in names:
        res = normalize_name(raw, aliases, drug_names)
        normalized.append({
            "input": res.input,
            "canonical_name": res.canonical_name,
            "drug_id": res.drug_id,
            "drug_ids": res.drug_ids,
            "status": res.status,
            "suggestions": res.suggestions,
            "source": res.source,
            "note": res.note,
        })
        if res.status != "ok":
            clarifications.append({
                "input": res.input,
                "status": res.status,
                "suggestions": res.suggestions,
                "note": res.note,
            })

    return {
        "raw_drugs": names,
        "normalized": normalized,
        "pending_clarifications": clarifications,
    }
