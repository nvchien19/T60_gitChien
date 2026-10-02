"""Node `lookup` — ghép bản ghi tương tác vào từng cặp thuốc (thuần, không DB).

Cặp không có bản ghi được ghi rõ `no_record` — KHÔNG bao giờ kết luận "an toàn".
"""

from typing import Any

from src.agents.state import AgentState
from src.core.guardrails import NO_RECORD_MSG
from src.tools.lookup_core import all_pairs


def _pair_key(pair: list[str]) -> frozenset[str]:
    return frozenset(pair)


async def lookup_node(state: AgentState) -> dict[str, Any]:
    ok_ids = [
        n["drug_id"]
        for n in state.get("normalized", [])
        if n.get("status") == "ok" and n.get("drug_id")
    ]
    if len(ok_ids) < 2:
        return {"interactions": [], "duplicate_acts": state.get("duplicate_acts", [])}

    by_pair: dict[frozenset[str], list[dict[str, Any]]] = {}
    for rec in state.get("interactions") or []:
        pair = rec.get("pair") or []
        if len(pair) == 2:
            by_pair.setdefault(_pair_key(pair), []).append(rec)

    name_by_id = {
        n["drug_id"]: (n.get("canonical_name") or n.get("input") or n["drug_id"])
        for n in state.get("normalized", [])
        if n.get("drug_id")
    }

    matched: list[dict[str, Any]] = []
    for a, b in all_pairs(ok_ids):
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

    return {"interactions": matched, "duplicate_acts": state.get("duplicate_acts", [])}
