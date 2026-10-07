"""Node `lookup` — ghép bản ghi tương tác vào từng cặp thuốc (thuần, không DB).

Cặp không có bản ghi được ghi rõ `no_record` — KHÔNG bao giờ kết luận "an toàn".
Bản ghi có `kind` (thực phẩm, bệnh nền, trùng nhóm) do backend tra sẵn được giữ nguyên.
"""

from typing import Any

from src.agents.state import AgentState
from src.core.guardrails import NO_RECORD_MSG
from src.tools.lookup_core import cross_input_pairs


def _pair_key(pair: list[str]) -> frozenset[str]:
    return frozenset(pair)


def _duplicate_actives(oks: list[dict[str, Any]], name_by_id: dict[str, str]) -> list[dict[str, Any]]:
    """Một hoạt chất xuất hiện trong từ hai tên nhập trở lên (quy tắc G6)."""
    inputs_of: dict[str, list[str]] = {}
    for n in oks:
        for i in n["ids"]:
            inputs_of.setdefault(i, []).append(n["input"])
    out = []
    for drug_id, inputs in inputs_of.items():
        if len(inputs) < 2:
            continue
        name = name_by_id.get(drug_id, drug_id)
        out.append({
            "kind": "duplicate_active",
            "pair": [f"dup:{drug_id}"],
            "pair_names": inputs,
            "drug_ids": [drug_id],
            "severity": "duplicate_active",
            "summary": f"Trùng hoạt chất: {', '.join(inputs)} cùng chứa {name}; "
                       "dùng chung có thể làm tổng lượng hoạt chất này vượt mức.",
            "citations": [{"source_id": "dav", "label": "Danh mục thuốc (Cục Quản lý Dược)",
                           "record_id": drug_id}],
            "match_type": "exact",
            "layer": "duplicate",
        })
    return out


async def lookup_node(state: AgentState) -> dict[str, Any]:
    oks = [
        {"input": n.get("input", ""), "ids": n.get("drug_ids") or [n["drug_id"]]}
        for n in state.get("normalized", [])
        if n.get("status") == "ok" and n.get("drug_id")
    ]
    catalog_names = (state.get("catalog") or {}).get("drug_names") or {}
    name_by_id = {i: catalog_names.get(i) or n["input"] or i for n in oks for i in n["ids"]}

    by_pair: dict[frozenset[str], list[dict[str, Any]]] = {}
    matched: list[dict[str, Any]] = []
    for rec in state.get("interactions") or []:
        if rec.get("kind"):
            matched.append(rec)
            continue
        pair = rec.get("pair") or []
        if len(pair) == 2:
            by_pair.setdefault(_pair_key(pair), []).append(rec)

    for a, b in cross_input_pairs([n["ids"] for n in oks]):
        key = _pair_key([a, b])
        names = [name_by_id.get(a, a), name_by_id.get(b, b)]
        hits = by_pair.get(key)
        if hits:
            for hit in hits:
                matched.append({**hit, "pair": [a, b], "pair_names": names})
        else:
            matched.append({
                "pair": [a, b],
                "pair_names": names,
                "severity": "no_record",
                "match_type": "no_record",
                "mechanism": NO_RECORD_MSG,
                "summary": NO_RECORD_MSG,
                "citations": [],
            })

    matched += _duplicate_actives(oks, name_by_id)
    return {"interactions": matched, "duplicate_acts": state.get("duplicate_acts", [])}
