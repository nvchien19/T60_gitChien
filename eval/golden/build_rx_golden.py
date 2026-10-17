"""
build_rx_golden.py - Dựng bộ golden cho chức năng KIỂM TRA ĐƠN (không phải chatbot), đáp án không lấy từ CSDL của hệ thống

Cách dùng (chạy từ gốc repo):
    python eval/golden/build_rx_golden.py            # dùng cache RxNav có sẵn, chỉ gọi mạng cho mã NDC mới
    python eval/golden/build_rx_golden.py --offline  # không gọi mạng; mã NDC chưa có trong cache coi như không rõ

Cần dữ liệu thô (ngoài git, xem eval/golden/refs/README.md để tải lại):
    data/raw/mimic_iv_demo/{prescriptions,admissions}.csv.gz   MIMIC-IV Clinical Database Demo v2.2 (ODbL 1.0)
    data/raw/eval_refs/alashwal2023_raw.csv                    phụ lục S1 của Al-Ashwal 2023 (CC BY-NC 3.0)

Đầu ra (đóng băng, commit vào git):
    eval/golden/rx_golden_set.jsonl / .csv   đơn thật: 249 đơn nội trú MIMIC-IV Demo + 4 đơn thật Việt Nam
    eval/golden/pair_set_alashwal.jsonl      255 cặp thuốc, nhãn Micromedex và Drugs.com (bộ công bố độc lập)
    eval/golden/pair_set_onc.jsonl           mọi cặp thuốc thuộc 14 quy tắc "luôn phải cảnh báo" của ONC 2012
    eval/golden/refs/rxnav_cache.json        cache NDC -> hoạt chất RxNorm (RxNav, NLM; dữ liệu công)

Đáp án lấy từ đâu (không có gì lấy từ CSDL DDInter mà hệ thống tra):
    - Hoạt chất của từng thuốc trên đơn MIMIC: mã NDC trên dòng y lệnh -> RxNorm (RxNav). Đơn Việt Nam: hoạt chất in
      trên chính đơn, ví dụ "Etcoxib 60mg Tab. (Etoricoxib 60mg)" -> nhập "Etcoxib 60mg Tab.", đáp án etoricoxib.
    - Cảnh báo bắt buộc: cặp thuốc trên đơn khớp một quy tắc ONC (Phansalkar 2012).
    - Trùng hoạt chất mong đợi: hai thuốc trên cùng đơn có chung hoạt chất RxNorm (hoặc chung hoạt chất in trên đơn).
    - Cặp Al-Ashwal: mức độ do Micromedex và Drugs.com ghi, chép nguyên từ phụ lục của bài báo.

Ảnh chụp đơn MIMIC: mỗi lần nhập viện lấy các dòng drug_type = MAIN, bỏ dịch truyền và dung môi, rồi lấy những thuốc
đang có hiệu lực tại thời điểm nhập viện + 48 giờ (nằm viện ngắn hơn thì lấy giữa đợt nằm viện). Tên thuốc giữ nguyên như
y lệnh, gộp tên trùng chỉ khác chữ hoa/thường. Đây là nhãn tham khảo, chưa có dược sĩ duyệt.
"""
import argparse
import csv
import itertools
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "eval" / "golden"
REFS = GOLDEN / "refs"
MIMIC = ROOT / "data" / "raw" / "mimic_iv_demo"
ALASHWAL_RAW = ROOT / "data" / "raw" / "eval_refs" / "alashwal2023_raw.csv"
RXNAV = "https://rxnav.nlm.nih.gov/REST"

FLUID_RE = re.compile(r"sodium chloride|dextrose|lactated ringer|sterile water|^bag$|^soln$|^vial$|^sw$|flush|"
                      r"iso-osmotic|^d5w|^ns$|syringe|^water", re.I)
SNAPSHOT_HOURS = 48

# Đơn thật Việt Nam (đã khử định danh, ảnh đã che ở docs/demo/anh_don_that/). Tên nhập là tên in trên đơn, bỏ phần
# trong ngoặc; đáp án là hoạt chất in trong ngoặc trên chính đơn, ghi theo tên RxNorm. NOT_DRUG = sản phẩm không phải
# thuốc (đúng khi hệ thống không nhận ra).
NOT_DRUG = "__not_drug__"
VN_CASES = [
    dict(id="VN-01", source="don_that_vn", note="Y lệnh nội trú, giảm đau (dòng thứ 4 bị che khuất trên ảnh)",
         items=[("Etcoxib 60mg Tab.", ["etoricoxib"]), ("Nefolin 30mg", ["nefopam"]),
                ("Panadol 500mg TAB.", ["acetaminophen"])]),
    dict(id="VN-02", source="don_that_vn", note="Đơn ngoại trú da liễu",
         items=[("Potriolac Gel 15g", ["calcipotriene", "betamethasone"]),
                ("Psocabet 15g", ["calcipotriene", "betamethasone"]),
                ("Cetirizine 10mg", ["cetirizine"]), ("Cyclosporin 100mg", ["cyclosporine"])]),
    dict(id="VN-03", source="don_that_vn", note="Hóa đơn mua thuốc, 2 kháng sinh",
         items=[("CTTZil 500mg", ["cefprozil"]), ("Melevox 500mg", ["levofloxacin"])]),
    dict(id="VN-04", source="don_that_vn", note="Phiếu tư vấn mỹ phẩm: không phải thuốc, hệ thống không được nhận nhầm",
         items=[("Med-Atopic D.L. Body lotion 400ml", [NOT_DRUG]), ("Adaphil 500ml", [NOT_DRUG]),
                ("Stanhome-Balance Shampoo 200ml", [NOT_DRUG])]),
]


# ---------------------------------------------------------------- RxNav
def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ingredients_of(rxcui: str) -> list[str]:
    data = _get_json(f"{RXNAV}/rxcui/{rxcui}/related.json?tty=IN")
    names = []
    for group in data.get("relatedGroup", {}).get("conceptGroup", []) or []:
        for c in group.get("conceptProperties", []) or []:
            names.append(c["name"].lower())
    return sorted(set(names))


def _lookup_ndc(ndc: str) -> dict:
    try:
        status = _get_json(f"{RXNAV}/ndcstatus.json?ndc={ndc}").get("ndcStatus", {})
        rxcui = status.get("rxcui") or ""
        if not rxcui:
            hist = status.get("ndcHistory") or []
            rxcui = next((h.get("activeRxcui") or h.get("originalRxcui") for h in hist
                          if h.get("activeRxcui") or h.get("originalRxcui")), "")
        return {"rxcui": rxcui, "ingredients": _ingredients_of(rxcui) if rxcui else []}
    except Exception as exc:  # noqa: BLE001 - lỗi mạng: không lưu cache để lần sau thử lại
        return {"error": str(exc)}


def resolve_ndcs(ndcs: set[str], cache: dict, offline: bool) -> dict:
    todo = sorted(n for n in ndcs if n not in cache)
    if todo and not offline:
        print(f"RxNav: tra {len(todo)} mã NDC mới ...", file=sys.stderr)
        with ThreadPoolExecutor(8) as pool:
            for ndc, res in zip(todo, pool.map(_lookup_ndc, todo)):
                if "error" not in res:
                    cache[ndc] = res
    return cache


def rxclass_members(class_id: str, cache: dict, offline: bool) -> list[str]:
    key = f"rxclass:{class_id}"
    if key not in cache and not offline:
        data = _get_json(f"{RXNAV}/rxclass/classMembers.json?classId={class_id}&relaSource=ATC&ttys=IN")
        members = data.get("drugMemberGroup", {}).get("drugMember", [])
        cache[key] = sorted({m["minConcept"]["name"].lower() for m in members})
    return cache.get(key, [])


# ---------------------------------------------------------------- MIMIC
def ndc11(value) -> str:
    if pd.isna(value):
        return ""
    s = str(int(float(value)))
    return "" if s == "0" else s.zfill(11)


def mimic_snapshots() -> list[dict]:
    rx = pd.read_csv(MIMIC / "prescriptions.csv.gz", parse_dates=["starttime", "stoptime"],
                     dtype={"ndc": "float64"})
    adm = pd.read_csv(MIMIC / "admissions.csv.gz", parse_dates=["admittime", "dischtime"])
    rx = rx[(rx["drug_type"] == "MAIN") & rx["drug"].notna()]
    rx = rx[~rx["drug"].str.strip().str.contains(FLUID_RE)]
    cases = []
    for a in adm.sort_values("hadm_id").itertuples():
        t = a.admittime + pd.Timedelta(hours=SNAPSHOT_HOURS)
        if t >= a.dischtime:
            t = a.admittime + (a.dischtime - a.admittime) / 2
        part = rx[(rx["hadm_id"] == a.hadm_id) & (rx["starttime"] <= t)
                  & (rx["stoptime"].isna() | (rx["stoptime"] > t))]
        items: dict[str, dict] = {}
        for r in part.itertuples():
            name = " ".join(str(r.drug).split())
            key = name.lower()
            item = items.setdefault(key, {"input": name, "ndcs": set(), "route": set()})
            if ndc11(r.ndc):
                item["ndcs"].add(ndc11(r.ndc))
            if isinstance(r.route, str):
                item["route"].add(r.route)
        if len(items) >= 2:
            cases.append({"hadm_id": int(a.hadm_id), "snapshot_hours": round((t - a.admittime).total_seconds() / 3600, 1),
                          "items": list(items.values())})
    return cases


# ---------------------------------------------------------------- quy tắc ONC
def load_onc(cache: dict, offline: bool) -> tuple[list[dict], dict[str, list[str]]]:
    onc = json.loads((REFS / "onc_high_priority_2012.json").read_text(encoding="utf-8"))
    classes = {}
    for name, members in onc["classes"].items():
        if isinstance(members, str) and members.startswith("@rxclass:"):
            members = rxclass_members(members.split(":", 1)[1], cache, offline)
        classes[name] = [m.lower() for m in members]

    def expand(side):
        return classes[side] if isinstance(side, str) else [m.lower() for m in side]
    rules = [dict(id=r["id"], name=r["name"], a=expand(r["a"]), b=expand(r["b"])) for r in onc["rules"]]
    return rules, classes


def onc_matches(ings_a: list[str], ings_b: list[str], rules: list[dict]) -> list[str]:
    hits = []
    for r in rules:
        if (set(ings_a) & set(r["a"]) and set(ings_b) & set(r["b"])) or \
           (set(ings_b) & set(r["a"]) and set(ings_a) & set(r["b"])):
            hits.append(r["id"])
    return hits


# ---------------------------------------------------------------- Al-Ashwal
def load_alashwal() -> list[dict]:
    rows = list(csv.DictReader(ALASHWAL_RAW.open(encoding="utf-8")))
    pairs = []
    for k, row in enumerate(rows, 1):
        num, rest = row["pair"].strip().split(" ", 1)
        a, b = (s.strip() for s in rest.split("_", 1))
        # số trong phụ lục đánh lại từ 1 cho mỗi thuốc chính, nên mã cặp dùng số thứ tự dòng
        pairs.append({"pair_id": f"AA-{k:03d}", "source_no": int(num), "drug_a": a, "drug_b": b,
                      **{k: int(row[k]) for k in ("micromedex", "drugscom", "chatgpt35", "chatgpt4", "bingai", "bard")}})
    return pairs


# ---------------------------------------------------------------- dựng bộ ca
def build(offline: bool) -> None:
    cache_path = REFS / "rxnav_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    rules, _ = load_onc(cache, offline)
    alashwal = load_alashwal()
    aa_index = {frozenset((p["drug_a"].lower(), p["drug_b"].lower())): p for p in alashwal}

    snaps = mimic_snapshots()
    resolve_ndcs({n for c in snaps for it in c["items"] for n in it["ndcs"]}, cache, offline)
    cache_path.write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1), encoding="utf-8")

    cases = []
    for c in snaps:
        drugs, expected = [], []
        for it in c["items"]:
            ings = sorted({i for n in it["ndcs"] for i in cache.get(n, {}).get("ingredients", [])})
            drugs.append(it["input"])
            expected.append({"input": it["input"], "ingredients": ings or None,
                             "route": sorted(it["route"]), "ndc_count": len(it["ndcs"])})
        cases.append({"id": f"MI-{c['hadm_id']}", "source": "mimic_iv_demo", "hadm_id": c["hadm_id"],
                      "snapshot_hours": c["snapshot_hours"], "drugs": drugs, "expected_items": expected})
    for v in VN_CASES:
        cases.append({"id": v["id"], "source": v["source"], "note": v["note"], "drugs": [i for i, _ in v["items"]],
                      "expected_items": [{"input": i, "ingredients": ings} for i, ings in v["items"]]})

    for case in cases:
        must, dups, aa = [], [], []
        items = case["expected_items"]
        for x, y in itertools.combinations(items, 2):
            ia, ib = x["ingredients"], y["ingredients"]
            if not ia or not ib or NOT_DRUG in ia or NOT_DRUG in ib:
                continue
            hit = onc_matches(ia, ib, rules)
            if hit:
                must.append({"pair": [x["input"], y["input"]], "rules": hit})
            shared = sorted(set(ia) & set(ib))
            if shared:
                dups.append({"pair": [x["input"], y["input"]], "shared": shared})
            for a, b in itertools.product(ia, ib):
                p = aa_index.get(frozenset((a, b)))
                if p:
                    aa.append({"pair": [x["input"], y["input"]], "pair_id": p["pair_id"],
                               "micromedex": p["micromedex"], "drugscom": p["drugscom"]})
        case["must_alert"] = must
        case["expected_duplicates"] = dups
        case["alashwal_pairs"] = aa

    with (GOLDEN / "rx_golden_set.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
    with (GOLDEN / "rx_golden_set.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "source", "input", "expected_ingredients", "must_alert_with", "duplicate_with",
                    "reviewer_ok", "reviewer_note"])
        for case in cases:
            for it in case["expected_items"]:
                must = [f"{m['pair'][1] if m['pair'][0] == it['input'] else m['pair'][0]} ({','.join(m['rules'])})"
                        for m in case["must_alert"] if it["input"] in m["pair"]]
                dup = [d["pair"][1] if d["pair"][0] == it["input"] else d["pair"][0]
                       for d in case["expected_duplicates"] if it["input"] in d["pair"]]
                w.writerow([case["id"], case["source"], it["input"], "; ".join(it["ingredients"] or ["(không rõ)"]),
                            " | ".join(must), " | ".join(dup), "", ""])

    with (GOLDEN / "pair_set_alashwal.jsonl").open("w", encoding="utf-8") as f:
        for p in alashwal:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    with (REFS / "alashwal2023_pairs.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(alashwal[0]))
        w.writeheader()
        w.writerows(alashwal)

    onc_pairs, seen = [], set()
    for r in rules:
        for a, b in itertools.product(r["a"], r["b"]):
            key = frozenset((a, b))
            if a == b or key in seen:
                continue
            seen.add(key)
            onc_pairs.append({"pair_id": f"ONC-P{len(onc_pairs) + 1:03d}", "rule": r["id"], "rule_name": r["name"],
                              "drug_a": a, "drug_b": b})
    with (GOLDEN / "pair_set_onc.jsonl").open("w", encoding="utf-8") as f:
        for p in onc_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    mimic = [c for c in cases if c["source"] == "mimic_iv_demo"]
    n_items = sum(len(c["drugs"]) for c in mimic)
    n_known = sum(1 for c in mimic for it in c["expected_items"] if it["ingredients"])
    print(f"Đơn MIMIC: {len(mimic)} đơn, {n_items} thuốc ({n_known} có đáp án hoạt chất); đơn VN: {len(VN_CASES)}")
    print(f"Cảnh báo bắt buộc ONC trên đơn: {sum(len(c['must_alert']) for c in cases)} cặp ở "
          f"{sum(1 for c in cases if c['must_alert'])} đơn; trùng hoạt chất mong đợi: "
          f"{sum(len(c['expected_duplicates']) for c in cases)}; cặp Al-Ashwal gặp trên đơn: "
          f"{sum(len(c['alashwal_pairs']) for c in cases)}")
    print(f"Cặp Al-Ashwal: {len(alashwal)}; cặp ONC: {len(onc_pairs)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="không gọi RxNav")
    build(ap.parse_args().offline)
