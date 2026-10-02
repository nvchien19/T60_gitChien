"""Tool 3 — severity_ranker (deterministic, khong LLM).

Thu tu: contraindicated(4) > major(3) > moderate(2) > minor(1) > unknown(0).
duplicate_class / duplicate_active hien thi nhu Trung binh nhung sort sau minor.
no_record khong sort chung — tra rieng.
Nhieu nguon lech nhau -> giu muc cao nhat (merge o day).
"""

from dataclasses import dataclass, field

RANK = {"contraindicated": 4, "major": 3, "moderate": 2, "minor": 1,
        "duplicate_class": 1.5, "duplicate_active": 1.5, "unknown": 0, "no_record": 0}

SEVERITY_VI = {"contraindicated": "Chống chỉ định", "major": "Nghiêm trọng",
               "moderate": "Trung bình", "minor": "Nhẹ",
               "duplicate_class": "Trung bình", "duplicate_active": "Trung bình",
               "unknown": "Chưa có bản ghi", "no_record": "Chưa có bản ghi"}


@dataclass
class RankedFinding:
    pair: list[str]
    severity: str
    symbol: str = "!"
    summary: str = ""
    mechanism: str = ""
    management: str = ""
    citations: list[dict] = field(default_factory=list)
    match_type: str = "exact"


def rank_value(sev: str) -> float:
    return RANK.get(sev, 0)


def merge_severity(records: list[dict]) -> dict | None:
    """Nhieu record cung cap (lop1+lop2) -> giu muc cao nhat, gom citations."""
    if not records:
        return None
    best = max(records, key=lambda r: rank_value(r.get("severity", "unknown")))
    merged = dict(best)
    cites = []
    for r in records:
        cites.extend(r.get("citations", []))
    seen, uniq = set(), []
    for c in cites:
        k = (c.get("source_id"), c.get("source_url"), c.get("label"))
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    merged["citations"] = uniq
    return merged


def rank_findings(records: list[dict]) -> tuple[list[dict], str]:
    exact = [r for r in records if r.get("match_type") != "no_record"]
    # gom theo cap (a,b) sort san
    by_pair: dict[tuple, list[dict]] = {}
    for r in exact:
        by_pair.setdefault(tuple(r["pair"]), []).append(r)
    merged = [m for rs in by_pair.values() if (m := merge_severity(rs))]
    merged.sort(key=lambda r: rank_value(r.get("severity", "unknown")), reverse=True)
    max_sev = merged[0]["severity"] if merged else "unknown"
    no_record = [r["pair"] for r in records if r.get("match_type") == "no_record"]
    return merged, max_sev, no_record
