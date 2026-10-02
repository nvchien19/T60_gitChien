"""check_service: normalize -> lookup lop1+lop2 -> vector fallback -> rank -> guardrail.

P0 chay sync (<3s voi data that nho sau loc); luu snapshot vao checks khi co rx_id.

Lớp orchestration của backend web. Lõi AI ở `src/` chỉ nhận dữ liệu đã tra cứu sẵn
qua `interface/backend/agent_adapter` — không bao giờ tự truy vấn DB.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.config import get_settings
from interface.backend.repositories import ddi_repo
from interface.backend.schemas.ddi import CheckResponse, Citation, FindingOut, NormalizedItem
from src.core.guardrails import DISCLAIMER, NO_RECORD_MSG, guardrail_assert
from src.tools._khoa import khoa
from src.tools.lookup_core import all_pairs, apply_dosage_rule, ara_applies, cosine, sorted_pair
from src.tools.normalizer import AliasRow, normalize_name
from src.tools.ranker import SEVERITY_VI, rank_findings

SOURCE_NAMES = {"ddinter": "DDInter 2.0", "patel2020": "Patel 2020",
                "openfda": "FDA Labels", "dav": "Cục Quản lý Dược",
                "pkddip": "PK-DDIP", "curated": "Từ điển dự án"}

SYMBOL = {"contraindicated": "⛔", "major": "!", "moderate": "△", "minor": "·",
          "duplicate_class": "=", "duplicate_active": "="}


_ALIASES_CACHE: list | None = None
_NAMES_CACHE: dict | None = None


async def load_catalog(db: AsyncSession) -> tuple[list[AliasRow], dict[str, str]]:
    """Cache full 63k aliases + drug names trong process (P0: duoi 10MB RAM).

    Catalog nay duoc inject cho lõi AI qua agent_adapter.
    """
    global _ALIASES_CACHE, _NAMES_CACHE
    if _ALIASES_CACHE is not None and _NAMES_CACHE is not None:
        return _ALIASES_CACHE, _NAMES_CACHE
    rows = await ddi_repo.get_aliases_for_fuzzy(db, limit=200000)
    _ALIASES_CACHE = [AliasRow(alias=r[0], drug_id=r[1], alias_type=r[2],
                               source_id=r[3] or "", status=r[4] or "ok",
                               drug_name=r[5] or "") for r in rows]
    _NAMES_CACHE = await ddi_repo.get_drug_names(db, list({a.drug_id for a in _ALIASES_CACHE}))
    return _ALIASES_CACHE, _NAMES_CACHE


async def normalize_list(db: AsyncSession, names: list[str]) -> list[NormalizedItem]:
    aliases, drug_names = await load_catalog(db)
    out = []
    for raw in names:
        key = khoa(raw)
        # exact truoc tren toan bo aliases (khong gioi han 20k)
        exact = [a for a in aliases if a.alias == key]
        r = normalize_name(raw, exact or aliases, drug_names)
        out.append(NormalizedItem(input=r.input, canonical_name=r.canonical_name,
                                  drug_id=r.drug_id, status=r.status,
                                  suggestions=r.suggestions, source=r.source, note=r.note))
    return out


def _to_finding(pair_names: list[str], rec: dict) -> FindingOut:
    cites = [Citation(source_id=c.get("source_id", ""),
                      source_name=SOURCE_NAMES.get(c.get("source_id", ""), c.get("source_id", "")),
                      label=c.get("label", ""), source_url=c.get("source_url", ""))
             for c in rec.get("citations", [])]
    sev = rec.get("severity", "unknown")
    return FindingOut(pair=pair_names, severity=sev,
                      severity_vi=SEVERITY_VI.get(sev, sev),
                      symbol=SYMBOL.get(sev, "!"),
                      summary=rec.get("summary") or rec.get("mechanism", "")[:300],
                      mechanism=rec.get("mechanism", ""),
                      management=rec.get("management", ""),
                      citations=cites, match_type=rec.get("match_type", "exact"))


async def fetch_interaction_records(db: AsyncSession, ok_ids: list[str],
                                    name_by_id: dict[str, str]) -> list[dict]:
    """Tra cac ban ghi tu CSDL cho danh sach drug_id da chuan hoa (lop 1 + lop 2).

    KHONG sinh ban ghi `no_record` — node `lookup` cua lõi AI lo phan nay
    (nho hon: agent tu biet cap nao thieu ban ghi).
    """
    settings = get_settings()
    records: list[dict] = []
    for a, b in all_pairs(ok_ids):
        a, b = sorted_pair(a, b)
        recs = await ddi_repo.get_pair_interactions(db, a, b)
        if recs:
            for r in recs:
                r["pair"] = [a, b]
                r["pair_names"] = [name_by_id.get(a, a), name_by_id.get(b, b)]
            records.extend(recs)
            continue
        # vector fallback tren mechanisms
        if settings.openai_api_key:
            mechs = await ddi_repo.get_mechanisms_with_embedding(db)
            # query embedding: can OPENAI thuc te; P0 bo qua neu khong co san embedding query.
            # Giu nhanhanh no_record khi offline (exact-match van chay).
            _ = mechs

    # Lop 2: dosage rules + ARA (co the nang len contraindicated)
    rules = await ddi_repo.get_dosage_rules_for(db, ok_ids)
    routes = {d: "oral" for d in ok_ids}  # TODO: lay route that tu medications/product khi co rx
    for r in rules:
        d1, d2 = r.drug_id, r.other_drug_id
        if d1 in routes and (d2 is None or d2 in routes):
            other = d2 or d1
            key = sorted_pair(d1, other)
            if key[0] in name_by_id and key[1] in name_by_id:
                applied = apply_dosage_rule(None, {"action": r.action, "severity": r.severity,
                                                   "effect_vi": r.effect_vi, "management_vi": r.management_vi,
                                                   "evidence": r.evidence, "source_url": r.source_url,
                                                   "source_id": r.source_id})
                if applied and not applied.get("downgrade_only"):
                    applied["pair"] = list(key)
                    applied["pair_names"] = [name_by_id[key[0]], name_by_id[key[1]]]
                    records.append(applied)

    aras = await ddi_repo.get_ara_for(db, ok_ids)
    for ara in aras:
        for v in (ara.victim_drug_ids or []):
            if v not in routes:
                continue
            if not ara_applies({"victim_drug_ids": ara.victim_drug_ids,
                                "victim_is_combination": ara.victim_is_combination,
                                "route_scope": ara.route_scope}, v, routes):
                continue
            for perp in (ara.ara_drug_ids or []):
                if perp in routes:
                    key = sorted_pair(v, perp)
                    records.append({"pair": list(key),
                                    "pair_names": [name_by_id.get(key[0], key[0]),
                                                   name_by_id.get(key[1], key[1])],
                                    "severity": ara.severity or "moderate",
                                    "mechanism": ara.mechanism or "",
                                    "management": ara.recommendation or "",
                                    "summary": ara.recommendation or ara.mechanism or "",
                                    "citations": [{"source_id": "patel2020", "label": "Patel 2020"}],
                                    "match_type": "exact", "layer": "ara"})

    return records


async def run_check(db: AsyncSession, drugs: list[str],
                    include_food: bool = True) -> CheckResponse:
    normalized = await normalize_list(db, drugs)
    ok = [n for n in normalized if n.status == "ok" and n.drug_id]
    unknown = [n for n in normalized if n.status != "ok"]
    name_by_id = {n.drug_id: (n.canonical_name or n.input) for n in ok}
    ok_ids = [n.drug_id for n in ok]

    records = await fetch_interaction_records(db, ok_ids, name_by_id)
    found_pairs = {tuple(r["pair"]) for r in records}
    for a, b in all_pairs(ok_ids):
        if (a, b) not in found_pairs:
            records.append({"pair": [a, b], "severity": "unknown", "match_type": "no_record",
                            "mechanism": NO_RECORD_MSG, "citations": [], "summary": NO_RECORD_MSG})

    merged, max_sev, no_record_ids = rank_findings(records)
    findings = [_to_finding(r.get("pair_names") or r["pair"], r) for r in merged]
    findings = guardrail_assert([f.model_dump() for f in findings])
    findings = [FindingOut(**f) for f in findings]
    no_record_pairs = [pair_name_map_get(name_by_id, p) for p in no_record_ids]

    # food
    food_findings = []
    if include_food:
        for row in await ddi_repo.get_food_for_drugs(db, ok_ids):
            food_findings.append(FindingOut(
                pair=[name_by_id.get(row.drug_id, row.drug_id), row.food_vi or row.food],
                severity=row.severity or "moderate",
                severity_vi=SEVERITY_VI.get(row.severity or "moderate", ""),
                summary=row.description or "", mechanism=row.mechanism_type or "",
                management=row.management or "",
                citations=[Citation(source_id=row.source_id or "ddinter",
                                    source_name=SOURCE_NAMES.get(row.source_id or "", ""))],
                match_type="exact"))

    # duplicate class
    dup_findings = []
    dup_rows = await ddi_repo.get_duplication_for_drugs(db, ok_ids)
    by_class: dict[str, list] = {}
    for d in dup_rows:
        by_class.setdefault(d.class_name, []).append(d)
    for cls, lst in by_class.items():
        if len(lst) >= 2:
            names = [name_by_id.get(d.drug_id, d.drug_id) for d in lst]
            dup_findings.append(FindingOut(
                pair=names[:2], severity="duplicate_class", severity_vi="Trung bình",
                symbol="=", summary=f"Trùng nhóm điều trị: {cls} ({len(lst)} thuốc)",
                mechanism=f"max_concurrent={lst[0].max_concurrent}",
                citations=[Citation(source_id="ddinter", source_name="DDInter 2.0",
                                    label=cls)], match_type="exact"))

    cov = await ddi_repo.count_coverage(db)
    coverage = (f"CSDL thật: {cov.get('drugs',0)} hoạt chất / {cov.get('pairs',0)} cặp DDInter "
                f"+ {cov.get('mechanisms',0)} cơ chế. Hoạt chất ngoài danh sách trả 'chưa có bản ghi'.")
    return CheckResponse(
        normalized=normalized, unknown=unknown,
        max_severity=max_sev, max_severity_vi=SEVERITY_VI.get(max_sev, max_sev),
        findings=findings, no_record_pairs=no_record_pairs,
        food_findings=food_findings[:20], duplicate_findings=dup_findings,
        disclaimer=DISCLAIMER, data_coverage=coverage)


def pair_name_map_get(name_by_id: dict[str, str], pair: list[str]) -> list[str]:
    return [name_by_id.get(pair[0], pair[0]), name_by_id.get(pair[1], pair[1])]


def cosine_fallback_rank(query: list[float], mechs: list[dict],
                         threshold: float = 0.75, top_k: int = 3) -> list[dict]:
    scored = [(cosine(query, m["embedding"]), m) for m in mechs if m.get("embedding")]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for s, m in scored[:top_k] if s >= threshold]
