"""Tool 1 — drug_name_normalizer (ham thuan, khong FastAPI/DB session).

Logic theo docs/BE_DEVELOPMENT.md W2 + data/mvp/README.md:
  khoa(ten) -> tra aliases exact:
    ok -> dung luon; nhieu drug_id (biet duoc phoi hop) -> ok, tra tung hoat chat
    suggest -> hoi xac nhan
  khong co -> rapidfuzz WRatio tren tap alias -> >=85 suggest top3 -> unknown.
suggest KHONG auto-accept.
"""

from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from src.tools._khoa import khoa

SUGGEST_THRESHOLD = 85


@dataclass
class AliasRow:
    alias: str
    drug_id: str
    alias_type: str | None = None
    source_id: str = ""
    status: str = "ok"
    drug_name: str = ""


@dataclass
class NormalizeResult:
    input: str
    canonical_name: str = ""
    drug_id: str = ""
    drug_ids: list[str] = field(default_factory=list)
    status: str = "unknown"  # ok | suggest | unknown
    suggestions: list[dict] = field(default_factory=list)
    source: str = ""
    note: str = ""


def normalize_name(
    raw: str,
    aliases: list[AliasRow],
    drug_names: dict[str, str] | None = None,
    threshold: int = SUGGEST_THRESHOLD,
) -> NormalizeResult:
    res = NormalizeResult(input=raw)
    key = khoa(raw)
    if not key:
        res.note = "Tên trống sau chuẩn hóa"
        return res
    exact = [a for a in aliases if a.alias == key]
    if exact:
        oks = [a for a in exact if a.status == "ok"]
        pool = oks or exact
        uniq_ids = list(dict.fromkeys(a.drug_id for a in pool))
        if len(uniq_ids) == 1:
            a = pool[0]
            res.status = "ok" if a.status == "ok" else "suggest"
            res.drug_id = uniq_ids[0]
            res.drug_ids = uniq_ids
            res.canonical_name = (drug_names or {}).get(uniq_ids[0], a.drug_name or uniq_ids[0])
            res.source = "+".join(sorted({f"aliases:{x.source_id}" for x in pool if x.source_id}))
            if res.status == "suggest":
                res.suggestions = [{"drug_id": uniq_ids[0], "canonical_name": res.canonical_name, "score": 1.0}]
                res.note = "Cần xác nhận, không tự áp dụng"
            return res
        names = [(drug_names or {}).get(did, next(x.drug_name for x in pool if x.drug_id == did) or did)
                 for did in uniq_ids]
        if oks:
            # Biet duoc phoi hop (1 alias 'ok' -> N hoat chat): tra tuong tac cho TUNG hoat chat.
            # Hoi lai o day lam agent dung truoc buoc lookup -> bo sot canh bao (false negative).
            res.status = "ok"
            res.drug_id = uniq_ids[0]
            res.drug_ids = uniq_ids
            res.canonical_name = " + ".join(names)
            res.source = "+".join(sorted({f"aliases:{x.source_id}" for x in pool if x.source_id}))
            res.note = "Thuốc phối hợp nhiều hoạt chất — kiểm tra từng hoạt chất"
            return res
        # alias chua duoc xac nhan (suggest) tro toi nhieu hoat chat -> van phai hoi lai
        res.status = "suggest"
        res.drug_ids = uniq_ids
        res.source = f"aliases:{pool[0].source_id}"
        res.suggestions = [
            {"drug_id": did, "canonical_name": name, "score": 1.0}
            for did, name in list(zip(uniq_ids, names))[:5]
        ]
        res.note = "Thuốc phối hợp nhiều hoạt chất — chọn hoạt chất đúng"
        return res
    # fuzzy tren tap alias (gioi han de chay nhanh)
    # fuzzy toan phan (ratio, khong partial de tranh khop thua tren input dai rac)
    choices = list({a.alias: a for a in aliases}.keys())
    if choices:
        hits = process.extract(key, choices, scorer=fuzz.ratio, limit=3)
        top = [(c, s) for c, s, *_ in hits if s >= threshold]
        if top:
            res.status = "suggest"
            for c, s in top:
                # alias cua biet duoc phoi hop tro toi nhieu hoat chat: goi y du tat ca
                for a in aliases:
                    if a.alias != c or any(h["drug_id"] == a.drug_id for h in res.suggestions):
                        continue
                    res.suggestions.append(
                        {
                            "drug_id": a.drug_id,
                            "canonical_name": (drug_names or {}).get(a.drug_id, a.drug_name or a.drug_id),
                            "score": round(s / 100, 3),
                        }
                    )
            res.drug_ids = [h["drug_id"] for h in res.suggestions]
            res.note = "Cần xác nhận, không tự áp dụng"
            return res
    res.status = "unknown"
    res.note = "Chưa có bản ghi trong CSDL"
    return res
