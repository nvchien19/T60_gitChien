"""Tool 1 — drug_name_normalizer (ham thuan, khong FastAPI/DB session).

Logic theo docs/BE_DEVELOPMENT.md W2 + data/mvp/README.md:
  khoa(ten) -> tra aliases exact:
    ok -> dung luon; nhieu drug_id (biet duoc phoi hop) -> ok, tra tung hoat chat
    suggest -> hoi xac nhan
  khong co -> thu bien the cua ten (bo ham luong, dang bao che o cuoi, tach ngoac don),
             moi bien the CHI duoc nhan khi khop exact alias
  van khong co -> rapidfuzz WRatio tren tap alias -> >=85 suggest top3 -> unknown.
suggest KHONG auto-accept.
"""

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from src.tools._khoa import khoa

SUGGEST_THRESHOLD = 85

# Chay tren khoa(ten): "0.5 g" -> "0 5 g", "500mg/5ml" -> "500mg 5ml", "10%" giu nguyen.
_UNIT = r"(?:mg|mcg|ug|g|gr|ml|l|iu|ui|dvqt|meq|mmol|%)"
_STRENGTH = re.compile(rf"(?<![a-z0-9])\d+(?: \d+)? ?{_UNIT}(?![a-z0-9])")
_TRAILING_NUMBER = re.compile(r"(?: \d+)+$")
# Chi bo o cuoi ten, va chi dung khi phan con lai khop exact alias.
_FORM_WORDS = {"vien", "nen", "nang", "mem", "bao", "phim", "sui", "goi", "ong", "tab", "tabs",
               "tablet", "tablets", "cap", "caps", "capsule", "capsules"}


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


def strip_strength(key: str) -> str:
    """Bo ham luong, so le va tu chi dang bao che o cuoi mot khoa da chuan hoa."""
    s = _STRENGTH.sub(" ", key)
    s = re.sub(r"\s+", " ", s).strip()
    s = _TRAILING_NUMBER.sub("", s).strip()
    words = s.split()
    while len(words) > 1 and words[-1] in _FORM_WORDS:
        words.pop()
    return " ".join(words)


def name_variants(raw: str) -> tuple[list[str], list[str]]:
    """(bien the cua phan ngoai ngoac, bien the cua phan trong ngoac), khong gom khoa(raw)."""
    # Ngoac tron va ngoac vuong ("CTTZil 500mg [Cefprozil]") deu coi la ten thu hai.
    outer = khoa(re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", raw))
    inner = [khoa(round_ or square) for round_, square in re.findall(r"\(([^)]*)\)|\[([^\]]*)\]", raw)]
    outs = [v for v in dict.fromkeys([outer, strip_strength(outer)]) if v]
    ins = [v for x in inner for v in dict.fromkeys([x, strip_strength(x)]) if v]
    key = khoa(raw)
    return [v for v in outs if v != key], [v for v in dict.fromkeys(ins) if v != key]


def _first_exact(keys: list[str], aliases: list[AliasRow]) -> tuple[str, list[AliasRow]]:
    for k in keys:
        hit = [a for a in aliases if a.alias == k]
        if hit:
            return k, hit
    return "", []


def _with_note(res: NormalizeResult, extra: str) -> NormalizeResult:
    if extra:
        res.note = f"{res.note}. {extra}" if res.note else extra
    return res


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
    variant_note = ""
    fuzzy_key = key
    if not exact:
        # Ten tren don that thuong kem ham luong hoac hoat chat trong ngoac ("Warfarin 5mg",
        # "Voltaren (Diclofenac)"). Chi nhan bien the khop exact; khong fuzzy tren bien the.
        outer_keys, inner_keys = name_variants(raw)
        k_out, hit_out = _first_exact(outer_keys, aliases)
        k_in, hit_in = _first_exact(inner_keys, aliases)
        ids_out = {a.drug_id for a in hit_out}
        ids_in = {a.drug_id for a in hit_in}
        if hit_out and hit_in and not (ids_out <= ids_in or ids_in <= ids_out):
            # Ngoai ngoac va trong ngoac tro toi hoat chat khac nhau: khong tu chon.
            res.status = "suggest"
            for a in hit_out + hit_in:
                if any(h["drug_id"] == a.drug_id for h in res.suggestions):
                    continue
                res.suggestions.append({
                    "drug_id": a.drug_id,
                    "canonical_name": (drug_names or {}).get(a.drug_id, a.drug_name or a.drug_id),
                    "score": 1.0,
                })
            res.drug_ids = [h["drug_id"] for h in res.suggestions]
            res.note = "Tên ngoài ngoặc và trong ngoặc là hai hoạt chất khác nhau, cần xác nhận"
            return res
        if hit_out or hit_in:
            used, exact = (k_out, hit_out) if hit_out else (k_in, hit_in)
            variant_note = f"Tra theo \"{used}\" (đã bỏ hàm lượng/dạng bào chế hoặc ngoặc đơn)"
        elif outer_keys:
            fuzzy_key = outer_keys[-1]
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
            return _with_note(res, variant_note)
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
            return _with_note(res, variant_note)
        # alias chua duoc xac nhan (suggest) tro toi nhieu hoat chat -> van phai hoi lai
        res.status = "suggest"
        res.drug_ids = uniq_ids
        res.source = f"aliases:{pool[0].source_id}"
        res.suggestions = [
            {"drug_id": did, "canonical_name": name, "score": 1.0}
            for did, name in list(zip(uniq_ids, names))[:5]
        ]
        res.note = "Thuốc phối hợp nhiều hoạt chất — chọn hoạt chất đúng"
        return _with_note(res, variant_note)
    # fuzzy tren tap alias (gioi han de chay nhanh)
    # fuzzy toan phan (ratio, khong partial de tranh khop thua tren input dai rac)
    choices = list({a.alias: a for a in aliases}.keys())
    if choices:
        hits = process.extract(fuzzy_key, choices, scorer=fuzz.ratio, limit=3)
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
