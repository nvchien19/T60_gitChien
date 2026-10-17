"""
run_rx_eval.py - Chấm chức năng KIỂM TRA ĐƠN (run_check) trên bộ ca dựng từ đơn thật và nguồn công bố độc lập

Cách dùng (chạy từ gốc repo, cần CSDL `ddi` đang chạy):
    python eval/run_rx_eval.py              # chạy run_check trên mọi bộ ca rồi chấm
    python eval/run_rx_eval.py --rescore    # chỉ chấm lại từ eval/results/rx_predictions.jsonl

Bộ ca (dựng bằng eval/golden/build_rx_golden.py, đã đóng băng):
    pair_set_alashwal.jsonl   255 cặp, nhãn Micromedex và Drugs.com (Al-Ashwal 2023). ≥ trung bình là dương tính,
                              nhẹ hoặc không có là âm tính, như trong bài báo.
    pair_set_onc.jsonl        469 cặp thuộc 14 quy tắc "luôn phải cảnh báo" của ONC (Phansalkar 2012).
    rx_golden_set.jsonl       249 đơn nội trú MIMIC-IV Demo + 4 đơn thật Việt Nam.

Đầu ra:
    eval/results/rx_predictions.jsonl   kết quả thô của run_check cho từng ca (để chấm lại, phân tích lỗi)
    eval/results/rx_metrics.json        chỉ số + so sánh + mô phỏng phương án (giao diện "Chất lượng AI" đọc file này)
    eval/results/rx_report.md           báo cáo nội bộ, có danh sách ca sai (không hiện trên giao diện)

Không gọi LLM, không ghi CSDL. Không chỉnh hệ thống theo kết quả của các bộ này: muốn thử sửa thì đo trên bộ ca khác.
"""
import argparse
import asyncio
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "eval" / "golden"
RESULTS = ROOT / "eval" / "results"
PRED = RESULTS / "rx_predictions.jsonl"
NOT_DRUG = "__not_drug__"

SEV_RANK = {"contraindicated": 4, "major": 3, "moderate": 2, "minor": 1}
DDI_SEVS = set(SEV_RANK)
CUTOFFS = {"minor": 1, "moderate": 2, "major": 3}

# ------------------------------------------------------------------ so tên hoạt chất
# Tên chung giữa RxNorm (Mỹ), INN và cách ghi trong CSDL. Chỉ để so tên, không dùng trong hệ thống.
SYNONYMS = [
    {"acetaminophen", "paracetamol"}, {"calcipotriene", "calcipotriol"}, {"cyclosporine", "ciclosporin"},
    {"albuterol", "salbutamol"}, {"epinephrine", "adrenaline"}, {"norepinephrine", "noradrenaline"},
    {"rifampin", "rifampicin"}, {"meperidine", "pethidine"}, {"glyburide", "glibenclamide"},
    {"lidocaine", "lignocaine"}, {"phytonadione", "phytomenadione", "vitamin k1", "vitamin k"},
    {"senna", "sennosides", "sennoside a and b"}, {"cholecalciferol", "vitamin d3", "colecalciferol"},
    {"ergocalciferol", "vitamin d2"}, {"magnesium hydroxide", "milk of magnesia"},
    {"cyanocobalamin", "vitamin b12"}, {"thiamine", "vitamin b1"}, {"pyridoxine", "vitamin b6"},
    {"ascorbic acid", "vitamin c"}, {"niacin", "nicotinic acid"}, {"isoproterenol", "isoprenaline"},
    {"methylergonovine", "methylergometrine"}, {"dothiepin", "dosulepin"}, {"amineptin", "amineptine"},
    {"st. john's wort", "hypericum perforatum", "st john's wort"}, {"methylene blue", "methylthioninium"},
    {"levothyroxine", "thyroxine"}, {"nitroglycerin", "glyceryl trinitrate"}, {"furosemide", "frusemide"},
    {"sulfamethoxazole", "sulphamethoxazole"}, {"valproic acid", "valproate"},
    {"aspirin", "acetylsalicylic acid"}, {"vitamin d", "cholecalciferol"}, {"clavulanate", "clavulanic acid"},
    {"polyethylene glycol 3350", "polyethylene glycol", "macrogol"}, {"ursodiol", "ursodeoxycholate",
                                                                     "ursodeoxycholic acid"},
    {"6 aminocaproic acid", "aminocaproic acid"}, {"albumin human usp", "albumin human", "albumin"},
    {"insulin regular human", "insulin human", "insulin human regular"}, {"isosorbide", "isosorbide mononitrate"},
    {"ethinyl estradiol", "ethinylestradiol"},
]
# Tên tiếng Việt trong danh mục -> tiếng Anh, để so với RxNorm
VI_TOKENS = {"natri": "sodium", "kali": "potassium", "calci": "calcium", "magnesi": "magnesium", "clorid": "chloride",
             "fluorid": "fluoride", "sulfat": "sulfate", "hydroclorid": "hydrochloride", "carbonat": "carbonate",
             "oxyd": "oxide", "hydroxyd": "hydroxide", "acid": "acid", "sắt": "ferrous", "kẽm": "zinc",
             "gluconat": "gluconate", "phosphat": "phosphate", "citrat": "citrate", "acetat": "acetate"}
_SYN = {n: i for i, group in enumerate(SYNONYMS) for n in group}
SALTS = {"hydrochloride", "hcl", "hydroclorid", "sodium", "natri", "tartrate", "succinate", "besylate", "besilate",
         "maleate", "mesylate", "mesilat", "citrate", "phosphate", "sulfate", "sulphate", "acetate", "calcium",
         "monohydrate", "monohydrat", "dipropionate", "dipropionat", "propionate", "valerate", "bromide", "fumarate",
         "dihydrate", "potassium", "kali", "hyclate", "trihydrate", "disodium", "magnesium", "decanoate",
         "hydrobromide", "bitartrate", "gluconate", "lactate", "anhydrous", "base"}
ANIONS = {"chloride", "bicarbonate", "phosphate", "sulfate", "gluconate", "citrate", "carbonate", "acetate",
          "oxide", "hydroxide", "lactate", "iodide"}


def _clean(name: str) -> str:
    name = re.sub(r"\(.*?\)|\[.*?\]", " ", name.lower())
    words = name.replace("-", " ").replace(",", " ").replace(".", " ").split()
    return " ".join(VI_TOKENS.get(w, w) for w in words)


def _same_key(a: str, b: str) -> bool:
    """Bằng nhau, cùng nhóm tên đồng nghĩa, hoặc cùng tập từ ('acid folic' = 'folic acid')."""
    return bool(a and b) and (a == b or sorted(a.split()) == sorted(b.split())
                              or (a in _SYN and _SYN.get(a) == _SYN.get(b)))


def same_ingredient(a: str, b: str) -> bool:
    ka, kb = _clean(a), _clean(b)
    if _same_key(ka, kb):
        return True
    sa = " ".join(w for w in ka.split() if w not in SALTS)
    sb = " ".join(w for w in kb.split() if w not in SALTS)
    return sa not in ANIONS and sb not in ANIONS and _same_key(sa, sb)


def names_match(expected: list[str], predicted: list[str]) -> bool:
    """Cùng tập hoạt chất (mỗi tên mong đợi khớp một tên hệ thống trả về và ngược lại)."""
    return all(any(same_ingredient(e, p) for p in predicted) for e in expected) and \
        all(any(same_ingredient(p, e) for e in expected) for p in predicted)


# ------------------------------------------------------------------ thống kê
def wilson(k: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def ratio(k: int, n: int) -> float | None:
    return round(k / n, 3) if n else None


def binary(truth: list[bool], pred: list[bool]) -> dict:
    tp = sum(t and p for t, p in zip(truth, pred))
    fp = sum((not t) and p for t, p in zip(truth, pred))
    fn = sum(t and not p for t, p in zip(truth, pred))
    tn = sum((not t) and not p for t, p in zip(truth, pred))
    sens, spec = ratio(tp, tp + fn), ratio(tn, tn + fp)
    ppv, npv = ratio(tp, tp + fp), ratio(tn, tn + fn)
    f1 = round(2 * ppv * sens / (ppv + sens), 3) if ppv and sens else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": len(truth),
            "sensitivity": sens, "sensitivity_ci": wilson(tp, tp + fn),
            "specificity": spec, "specificity_ci": wilson(tn, tn + fp),
            "ppv": ppv, "ppv_ci": wilson(tp, tp + fp), "npv": npv, "npv_ci": wilson(tn, tn + fn),
            "accuracy": ratio(tp + tn, len(truth)), "f1": f1}


def weighted_kappa(a: list[int], b: list[int], levels: list[int]) -> float | None:
    """Kappa có trọng số tuyến tính cho mức độ (1 không có, 2 nhẹ, 3 trung bình, 4 nặng/chống chỉ định)."""
    n, k = len(a), len(levels)
    if n == 0:
        return None
    idx = {v: i for i, v in enumerate(levels)}
    obs = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1
    ra = [sum(row) for row in obs]
    cb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[abs(i - j) / (k - 1) for j in range(k)] for i in range(k)]
    po = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w[i][j] * ra[i] * cb[j] for i in range(k) for j in range(k)) / (n * n)
    return round(1 - po / pe, 3) if pe else None


def pct(values: list[float], q: float) -> float:
    s = sorted(values)
    if not s:
        return 0.0
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return round(s[lo] + (s[hi] - s[lo]) * (pos - lo), 1)


# ------------------------------------------------------------------ chạy run_check
def _load(name: str) -> list[dict]:
    return [json.loads(line) for line in (GOLDEN / name).open(encoding="utf-8")]


def _summarize(res) -> dict:
    def finding(f):
        return {"pair": f.pair, "severity": f.severity,
                "sources": sorted({c.source_id for c in f.citations if c.source_id})}
    return {
        "normalized": [{"input": n.input, "status": n.status, "canonical_name": n.canonical_name,
                        "drug_ids": n.drug_ids or ([n.drug_id] if n.drug_id else []),
                        "suggestions": [s.get("canonical_name", "") for s in n.suggestions[:3]]}
                       for n in res.normalized],
        "findings": [finding(f) for f in res.findings if f.severity in DDI_SEVS],
        "no_record_pairs": len(res.no_record_pairs),
        "duplicates": [finding(f) for f in res.duplicate_findings],
        "food": [finding(f) for f in res.food_findings],
    }


async def predict() -> None:
    sys.path.insert(0, str(ROOT))
    from interface.backend.db.session import SessionLocal, engine
    from interface.backend.services.check_service import run_check

    jobs = [("alashwal", p["pair_id"], [p["drug_a"], p["drug_b"]], False) for p in _load("pair_set_alashwal.jsonl")]
    jobs += [("onc", p["pair_id"], [p["drug_a"], p["drug_b"]], False) for p in _load("pair_set_onc.jsonl")]
    jobs += [("rx", c["id"], c["drugs"], True) for c in _load("rx_golden_set.jsonl")]
    RESULTS.mkdir(parents=True, exist_ok=True)
    try:
        async with SessionLocal() as db:
            with PRED.open("w", encoding="utf-8") as out:
                for i, (kind, cid, drugs, food) in enumerate(jobs, 1):
                    res = await run_check(db, drugs, include_food=food)
                    out.write(json.dumps({"set": kind, "id": cid, **_summarize(res)}, ensure_ascii=False) + "\n")
                    if i % 100 == 0:
                        print(f"  {i}/{len(jobs)}", file=sys.stderr)
    finally:
        await engine.dispose()


# ------------------------------------------------------------------ chấm
def _sys_level(pred: dict, sources: set[str] | None = None) -> int:
    """Mức cao nhất hệ thống báo cho một cặp, theo thang của Al-Ashwal (1 không, 2 nhẹ, 3 TB, 4 nặng/CCĐ)."""
    ranks = [SEV_RANK[f["severity"]] for f in pred["findings"]
             if sources is None or set(f["sources"]) & sources]
    top = max(ranks, default=0)
    return {0: 1, 1: 2, 2: 3, 3: 4, 4: 4}[top]


def _pair_reason(pred: dict) -> str:
    if any(n["status"] != "ok" for n in pred["normalized"]):
        return "name_not_recognized"
    return "no_record" if not pred["findings"] else "severity_lower"


def score_alashwal(cases: list[dict], preds: dict, cutoff: int = 3, sources: set[str] | None = None) -> dict:
    out = {}
    for ref in ("drugscom", "micromedex"):
        truth = [c[ref] >= 3 for c in cases]
        sys_lv = [_sys_level(preds[c["pair_id"]], sources) for c in cases]
        res = binary(truth, [lv >= cutoff for lv in sys_lv])
        res["kappa_weighted"] = weighted_kappa([min(c[ref], 4) for c in cases], sys_lv, [1, 2, 3, 4])
        out[ref] = res
    return out


def comparators(cases: list[dict]) -> dict:
    """Các công cụ trong bài báo, trên đúng 255 cặp (mã 7 'không phân loại được' tính là không cảnh báo)."""
    out = {}
    for ref in ("drugscom", "micromedex"):
        truth = [c[ref] >= 3 for c in cases]
        out[ref] = {}
        for key, label in TOOLS.items():
            if key == ref:
                continue
            pred = [c[key] in (3, 4, 5) for c in cases]
            out[ref][key] = {"label": label, **binary(truth, pred)}
    return out


TOOLS = {"micromedex": "Micromedex", "drugscom": "Drugs.com", "chatgpt4": "ChatGPT-4", "chatgpt35": "ChatGPT-3.5",
         "bingai": "Bing AI", "bard": "Bard"}
# Chuẩn tổng hợp (eval/golden/build_authoritative_ref.py): tên -> (mô tả, hàm chọn dương tính)
AUTH_REFS = {
    "any": ("Ít nhất 1 nguồn có thẩm quyền: Micromedex, nhãn thuốc FDA hoặc nhãn thuốc Nhật Bản (PMDA, qua KEGG)",
            lambda r: r["ref_any"]),
    "two": ("Ít nhất 2 trong 3 nguồn trên", lambda r: r["ref_two"]),
    "labels": ("Chỉ nhãn thuốc được cơ quan quản lý duyệt (FDA hoặc Nhật Bản), không dùng Micromedex",
               lambda r: r["votes"]["fda_label"] or r["votes"]["japan_label"]),
}


def score_authoritative(cases: list[dict], preds: dict) -> dict | None:
    """Chấm hệ thống và mọi công cụ trong bài báo theo chuẩn tổng hợp từ các nguồn có thẩm quyền."""
    path = GOLDEN / "pair_ref_authoritative.jsonl"
    if not path.exists():
        return None
    ref = {r["pair_id"]: r for r in _load(path.name)}
    sys_pred = [_sys_level(preds[c["pair_id"]]) >= 3 for c in cases]
    out = {"n": len(cases), "refs": {}}
    for key, (label, pick) in AUTH_REFS.items():
        truth = [bool(pick(ref[c["pair_id"]])) for c in cases]
        block = {"label": label, "positives": sum(truth), "system": binary(truth, sys_pred), "tools": {}}
        for tool, name in TOOLS.items():
            # Micromedex nằm trong chuẩn "any"/"two" nên được lợi; vẫn tính nhưng đánh dấu để giao diện ghi chú
            block["tools"][tool] = {"label": name, "in_reference": key != "labels" and tool == "micromedex",
                                    **binary(truth, [c[tool] in (3, 4, 5) for c in cases])}
        out["refs"][key] = block
    rows = [ref[c["pair_id"]] for c in cases]
    out["sources"] = {
        "micromedex": sum(r["votes"]["micromedex"] for r in rows),
        "fda_label": sum(r["votes"]["fda_label"] for r in rows),
        "japan_label": sum(r["votes"]["japan_label"] for r in rows),
        "fda_no_label": sum(r["fda_label"] == "no_label" for r in rows),
    }
    out["by_n_sources"] = dict(sorted(Counter(r["n_sources"] for r in rows).items()))
    # Cảnh báo bị tính là thừa khi so riêng với Micromedex nhưng có nhãn thuốc làm cơ sở
    fp_mm = [c for c, p in zip(cases, sys_pred) if p and c["micromedex"] < 3]
    out["fp_vs_micromedex"] = {"n": len(fp_mm),
                               "supported_by_label": sum(AUTH_REFS["labels"][1](ref[c["pair_id"]]) for c in fp_mm)}
    return out


# Hệ thống thương mại khác: không có số từng cặp công khai nên chỉ chép kết quả các nghiên cứu (KHÁC bộ ca, không so
# trực tiếp với số của Rà Thuốc ở trên).
LITERATURE = [
    {"study": "Marcath LA et al. J Oncol Pract 2018;14(6):e368-e374, doi:10.1200/JOP.18.00086",
     "setting": "145 cặp thuốc ung thư đường uống với thuốc khác; chuẩn: Stockley's Drug Interactions, dược sĩ thẩm định",
     "columns": ["sensitivity", "specificity", "ppv", "npv"],
     "rows": [["Lexicomp", 0.96, 0.80, 0.95, 0.83], ["Micromedex", 0.86, 0.87, 0.96, 0.62],
              ["Facts & Comparisons", 0.67, 0.93, 0.97, 0.42], ["PEPID", 0.90, 0.53, 0.88, 0.59],
              ["Drugs.com", 0.93, 0.73, 0.93, 0.73], ["Epocrates (miễn phí)", 0.73, 0.83, 0.94, 0.45],
              ["Medscape", 0.79, 0.73, 0.92, 0.48], ["RxList", 0.65, 0.83, 0.94, 0.38],
              ["WebMD", 0.79, 0.77, 0.93, 0.49]]},
    {"study": "Kheshti R et al. J Res Pharm Pract 2016;5(4):257-263, PMC5084483",
     "setting": "360 cặp từ đơn thật + 40 cặp đã biết; chuẩn: dược sĩ lâm sàng cùng Stockley's",
     "summary": "Lexi-Interact độ nhạy cao nhất (0,77), Micromedex độ đặc hiệu cao nhất (0,78); tỷ lệ trả lời đúng: "
                "Lexi-Interact 69,8%, Epocrates 60,3%, Micromedex 50,8%, Medscape 49%, iFacts 36,7%."},
    {"study": "Bossaer JB et al. J Oncol Pharm Pract 2022, doi:10.1177/1078155220984244",
     "setting": "229 cặp thật (chuẩn: nhãn thuốc FDA, dược sĩ ung thư phân xử) + 64 cặp không có tương tác",
     "summary": "Điểm tổng hợp độ chính xác: Lexicomp 355, Drugs.com 352, Epocrates 344, Medscape 280, Micromedex 270."},
    {"study": "Xu et al. Front Pharmacol 2025, PMC12504084",
     "setting": "So mức độ giữa Micromedex, Lexicomp, Epocrates, Medscape, Drugs.com",
     "summary": "Các phần mềm thương mại đồng thuận rất thấp với nhau (Gwet AC1 0,16–0,24): không có phần mềm nào là "
                "đáp án tuyệt đối."},
]


def score_onc(cases: list[dict], preds: dict) -> dict:
    n = len(cases)
    rec = [c for c in cases if all(x["status"] == "ok" for x in preds[c["pair_id"]]["normalized"])]
    lv = {c["pair_id"]: _sys_level(preds[c["pair_id"]]) for c in cases}
    any_hit = sum(lv[c["pair_id"]] >= 2 for c in cases)
    major = sum(lv[c["pair_id"]] >= 4 for c in cases)
    rec_major = sum(lv[c["pair_id"]] >= 4 for c in rec)
    by_rule = defaultdict(lambda: {"n": 0, "recognized": 0, "alert": 0, "major": 0})
    for c in cases:
        r = by_rule[c["rule"]]
        r["name"] = c["rule_name"]
        r["n"] += 1
        r["recognized"] += c in rec
        r["alert"] += lv[c["pair_id"]] >= 2
        r["major"] += lv[c["pair_id"]] >= 4
    return {"n": n, "recognized": len(rec), "alert_any": any_hit, "alert_major": major,
            "alert_any_rate": ratio(any_hit, n), "alert_major_rate": ratio(major, n),
            "alert_major_rate_ci": wilson(major, n),
            "alert_major_rate_recognized": ratio(rec_major, len(rec)),
            "alert_major_rate_recognized_ci": wilson(rec_major, len(rec)),
            "by_rule": dict(sorted(by_rule.items()))}


def score_rx(cases: list[dict], preds: dict) -> dict:
    items = defaultdict(lambda: Counter())
    wrong_examples, missed_dups = [], []
    must_total = must_hit = dup_total = dup_hit = dup_pred = dup_pred_ok = 0
    burden = defaultdict(list)
    cited = total_findings = 0
    for c in cases:
        p = preds[c["id"]]
        norm = {n["input"]: n for n in p["normalized"]}
        names_of = {k: [s.strip() for s in n["canonical_name"].split(" + ") if s.strip()]
                    for k, n in norm.items() if n["status"] == "ok"}
        group = "vn" if c["source"] == "don_that_vn" else "mimic"
        for it in c["expected_items"]:
            n = norm.get(it["input"], {"status": "unknown"})
            exp = it["ingredients"]
            if not exp:
                continue
            ctr = items[group]
            ctr["total"] += 1
            if exp == [NOT_DRUG]:
                ctr["not_drug"] += 1
                ctr["not_drug_ok"] += n["status"] != "ok"
                continue
            ctr["drug"] += 1
            ctr[n["status"]] += 1
            if n["status"] == "ok":
                if names_match(exp, names_of[it["input"]]):
                    ctr["correct"] += 1
                else:
                    ctr["wrong"] += 1
                    wrong_examples.append({"case": c["id"], "input": it["input"], "expected": exp,
                                           "got": n["canonical_name"]})

        def flagged(a: str, b: str) -> int:
            na, nb = names_of.get(a, []), names_of.get(b, [])
            best = 0
            for f in p["findings"]:
                x, y = f["pair"][0], f["pair"][1]
                if (x in na and y in nb) or (x in nb and y in na):
                    best = max(best, SEV_RANK[f["severity"]])
            return best
        for m in c["must_alert"]:
            must_total += 1
            must_hit += flagged(*m["pair"]) >= 3
        exp_dups = {frozenset(d["pair"]) for d in c["expected_duplicates"]}
        got_dups = set()
        for f in p["duplicates"]:
            if f["severity"] == "duplicate_active":
                ins = [x for x in f["pair"] if x in norm]
                got_dups |= {frozenset((a, b)) for i, a in enumerate(ins) for b in ins[i + 1:]}
        dup_total += len(exp_dups)
        dup_hit += len(exp_dups & got_dups)
        known = {it["input"]: it["ingredients"] for it in c["expected_items"]
                 if it["ingredients"] and it["ingredients"] != [NOT_DRUG]}
        for pair in got_dups:
            a, b = tuple(pair)
            if a in known and b in known:
                dup_pred += 1
                dup_pred_ok += any(same_ingredient(x, y) for x in known[a] for y in known[b])
        for e in exp_dups - got_dups:
            missed_dups.append({"case": c["id"], "pair": sorted(e)})
        if group == "mimic":
            sev = Counter(f["severity"] for f in p["findings"])
            burden["ddi"].append(len(p["findings"]))
            burden["major_plus"].append(sev["major"] + sev["contraindicated"])
            burden["moderate"].append(sev["moderate"])
            burden["minor"].append(sev["minor"])
            burden["food"].append(len(p["food"]))
            burden["dup"].append(len(p["duplicates"]))
            burden["n_drugs"].append(len(c["drugs"]))
        for f in p["findings"] + p["duplicates"] + p["food"]:
            total_findings += 1
            cited += bool(f["sources"])

    def norm_block(ctr: Counter) -> dict:
        d = ctr["drug"]
        return {"items": ctr["total"], "drug_items": d,
                "correct_rate": ratio(ctr["correct"], d), "correct_rate_ci": wilson(ctr["correct"], d),
                "recognized_rate": ratio(ctr["ok"], d), "wrong_rate": ratio(ctr["wrong"], d),
                "suggest_rate": ratio(ctr["suggest"], d), "unknown_rate": ratio(ctr["unknown"], d),
                "precision_when_recognized": ratio(ctr["correct"], ctr["ok"]),
                "not_drug_items": ctr["not_drug"], "not_drug_rejected": ctr["not_drug_ok"]}
    all_ctr = items["mimic"] + items["vn"]
    n_rx = len(burden["ddi"])
    return {
        "n_prescriptions": len(cases), "n_mimic": n_rx, "n_vn": sum(c["source"] == "don_that_vn" for c in cases),
        "median_drugs": statistics.median(burden["n_drugs"]) if n_rx else None,
        "normalization": {"all": norm_block(all_ctr), "mimic": norm_block(items["mimic"]),
                          "vn": norm_block(items["vn"])},
        "must_alert": {"n": must_total, "hit_major": must_hit},
        "duplicates": {"expected": dup_total, "detected": dup_hit, "recall": ratio(dup_hit, dup_total),
                       "recall_ci": wilson(dup_hit, dup_total), "flagged_checkable": dup_pred,
                       "flagged_confirmed": dup_pred_ok, "precision": ratio(dup_pred_ok, dup_pred)},
        "burden": {k: {"mean": round(statistics.mean(v), 2), "median": statistics.median(v), "p90": pct(v, 0.9)}
                   for k, v in burden.items()} | {
            "rx_with_major_plus": ratio(sum(x > 0 for x in burden["major_plus"]), n_rx),
            "rx_with_any_ddi": ratio(sum(x > 0 for x in burden["ddi"]), n_rx)},
        "citation_rate": ratio(cited, total_findings), "findings_total": total_findings,
        "_wrong_examples": wrong_examples, "_missed_dups": missed_dups,
    }


def options(aa: list[dict], preds: dict, rx_cases: list[dict], onc_cases: list[dict]) -> list[dict]:
    """Mô phỏng các phương án trên kết quả đã có (không sửa hệ thống) để thấy đánh đổi."""
    rows = []
    burden = {}
    mimic = [preds[c["id"]] for c in rx_cases if c["source"] == "mimic_iv_demo"]
    for name, cut in CUTOFFS.items():
        per_rx = [sum(SEV_RANK[f["severity"]] >= cut for f in p["findings"]) for p in mimic]
        burden[name] = (statistics.median(per_rx), pct(per_rx, 0.9))
    for name, cut in CUTOFFS.items():
        s = score_alashwal(aa, preds, cutoff=cut + 1)
        rows.append({"option": f"cutoff_{name}", "drugscom": _brief(s["drugscom"]), "micromedex": _brief(s["micromedex"]),
                     "alerts_per_rx_median": burden[name][0], "alerts_per_rx_p90": burden[name][1]})
    # nguồn: chỉ DDInter so với DDInter + các lớp khác
    sources = Counter(src for p in preds.values() for f in p["findings"] for src in f["sources"])
    if len(sources) > 1:
        s = score_alashwal(aa, preds, sources={"ddinter"})
        rows.append({"option": "source_ddinter_only", "drugscom": _brief(s["drugscom"]),
                     "micromedex": _brief(s["micromedex"])})
    # trần nếu nhận ra được mọi tên thuốc đang bị bỏ sót (chưa sửa, chỉ đếm)
    for ref in ("drugscom", "micromedex"):
        fn = [c for c in aa if c[ref] >= 3 and _sys_level(preds[c["pair_id"]]) < 3]
        reasons = Counter(_pair_reason(preds[c["pair_id"]]) for c in fn)
        rows.append({"option": f"fn_breakdown_{ref}", "reasons": dict(reasons)})
    fp = [c for c in aa if c["drugscom"] < 3 and _sys_level(preds[c["pair_id"]]) >= 3]
    rows.append({"option": "fp_vs_drugscom_but_micromedex_pos",
                 "n_fp": len(fp), "micromedex_positive": sum(c["micromedex"] >= 3 for c in fp)})
    onc_lv = [_sys_level(preds[c["pair_id"]]) for c in onc_cases]
    rows.append({"option": "onc_alert_moderate_or_more", "rate": ratio(sum(x >= 3 for x in onc_lv), len(onc_lv))})
    rows.append({"option": "sources_seen", "sources": dict(sources)})
    return rows


def _brief(m: dict) -> dict:
    return {k: m[k] for k in ("sensitivity", "specificity", "ppv", "npv", "f1", "tp", "fp", "fn", "tn")}


def rescore() -> dict:
    preds = {}
    for line in PRED.open(encoding="utf-8"):
        p = json.loads(line)
        preds[p["id"]] = p
    aa = _load("pair_set_alashwal.jsonl")
    onc = _load("pair_set_onc.jsonl")
    rx = _load("rx_golden_set.jsonl")
    result = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "function": "run_check (kiểm tra đơn), không qua LLM",
        "alashwal": {"n": len(aa), "positives": {r: sum(c[r] >= 3 for c in aa) for r in ("drugscom", "micromedex")},
                     "system": score_alashwal(aa, preds), "comparators": comparators(aa),
                     "reference_agreement": binary([c["micromedex"] >= 3 for c in aa], [c["drugscom"] >= 3 for c in aa])},
        "authoritative": score_authoritative(aa, preds),
        "literature": LITERATURE,
        "_fp_ids": {c["pair_id"]: _sys_level(preds[c["pair_id"]]) >= 3 and c["micromedex"] < 3 for c in aa},
        "onc": score_onc(onc, preds),
        "rx": score_rx(rx, preds),
        "options": options(aa, preds, rx, onc),
        "sources": {
            "alashwal": "Al-Ashwal FY et al. Drug Healthc Patient Saf 2023;15:137-147, doi:10.2147/DHPS.S425858, "
                        "phụ lục S1 (CC BY-NC 3.0)",
            "onc": "Phansalkar S et al. JAMIA 2012;19(5):735-743, doi:10.1136/amiajnl-2011-000612, Bảng 2",
            "mimic": "Johnson A et al. MIMIC-IV Clinical Database Demo v2.2, PhysioNet, doi:10.13026/dp1f-ex47 (ODbL 1.0)",
            "rxnorm": "RxNav, U.S. National Library of Medicine",
            "fda_label": "Nhãn thuốc FDA (Structured Product Labeling) qua openFDA, U.S. Food and Drug Administration; "
                         "nhãn đã dùng ghi ở eval/golden/refs/fda_labels_used.json",
            "japan_label": "KEGG DRUG / DDI (Kanehisa Laboratories), tổng hợp từ tờ hướng dẫn sử dụng thuốc được PMDA "
                           "Nhật Bản duyệt; chỉ dùng học thuật",
        },
    }
    return result


def write_report(r: dict) -> None:
    a, o, x = r["alashwal"], r["onc"], r["rx"]
    lines = ["# Đánh giá chức năng kiểm tra đơn (nội bộ)", "", f"Sinh lúc {r['generated']} bởi `eval/run_rx_eval.py`. "
             "Báo cáo này có danh sách ca sai, **không** hiện trên giao diện.", "",
             "## 1. Al-Ashwal 2023 (255 cặp, bộ công bố độc lập)", "",
             "| So với | Độ nhạy | Độ đặc hiệu | PPV | NPV | F1 | Kappa mức độ |", "|---|---|---|---|---|---|---|"]
    for ref in ("drugscom", "micromedex"):
        m = a["system"][ref]
        lines.append(f"| {ref} | {m['sensitivity']} {m['sensitivity_ci']} | {m['specificity']} {m['specificity_ci']} | "
                     f"{m['ppv']} | {m['npv']} | {m['f1']} | {m['kappa_weighted']} |")
    au = r.get("authoritative")
    if au:
        lines += ["", "### Chuẩn tổng hợp từ nguồn có thẩm quyền", "",
                  f"Số cặp mỗi nguồn ghi nhận: {au['sources']}; số nguồn mỗi cặp: {au['by_n_sources']}. "
                  f"Cảnh báo thừa so với Micromedex có nhãn thuốc làm cơ sở: {au['fp_vs_micromedex']['supported_by_label']}"
                  f"/{au['fp_vs_micromedex']['n']}.", ""]
        for key, blk in au["refs"].items():
            lines += [f"**{key}** ({blk['label']}; {blk['positives']} cặp dương tính)", "",
                      "| Công cụ | Độ nhạy | Độ đặc hiệu | PPV | F1 | TP/FP/FN/TN |", "|---|---|---|---|---|---|"]
            for name, m in [("Rà Thuốc", blk["system"])] + [(t["label"] + (" *" if t["in_reference"] else ""), t)
                                                          for t in blk["tools"].values()]:
                lines.append(f"| {name} | {m['sensitivity']} | {m['specificity']} | {m['ppv']} | {m['f1']} | "
                             f"{m['tp']}/{m['fp']}/{m['fn']}/{m['tn']} |")
            lines.append("")
        lines.append("\\* nằm trong chuẩn nên được lợi.")
        ev = GOLDEN / "refs" / "fda_label_evidence_alashwal.jsonl"
        if ev.exists():
            fp_ids = {c for c, v in r.get("_fp_ids", {}).items() if v}
            lines += ["", "### Cảnh báo thừa so với Micromedex và bằng chứng nhãn thuốc", ""]
            for row in map(json.loads, ev.open(encoding="utf-8")):
                if row["pair_id"] not in fp_ids:
                    continue
                pos = [s for s in row["sides"] if s.get("status") == "positive"]
                txt = "; ".join(f"nhãn {s['label_of']} ({s['action']}): \"{s['quote'][:160]}\"" for s in pos) or "không"
                lines.append(f"- {row['pair_id']} {row['drug_a']} + {row['drug_b']}: {txt}")
    lines += ["", "Các công cụ khác trên cùng 255 cặp (so với Drugs.com):", "",
              "| Công cụ | Độ nhạy | Độ đặc hiệu | PPV | F1 |", "|---|---|---|---|---|"]
    for v in a["comparators"]["drugscom"].values():
        lines.append(f"| {v['label']} | {v['sensitivity']} | {v['specificity']} | {v['ppv']} | {v['f1']} |")
    lines += ["", f"## 2. ONC 2012 ({o['n']} cặp bắt buộc cảnh báo)", "",
              f"Nhận ra cả hai tên: {o['recognized']}/{o['n']}. Báo ở mức Nghiêm trọng trở lên: {o['alert_major']} "
              f"({o['alert_major_rate']}); có báo ở mọi mức: {o['alert_any']}.", "",
              "| Quy tắc | Số cặp | Nhận ra tên | Có cảnh báo | ≥ Nghiêm trọng |", "|---|---|---|---|---|"]
    for k, v in o["by_rule"].items():
        lines.append(f"| {k} {v['name']} | {v['n']} | {v['recognized']} | {v['alert']} | {v['major']} |")
    nm = x["normalization"]
    lines += ["", f"## 3. Đơn thật ({x['n_mimic']} đơn MIMIC-IV Demo, {x['n_vn']} đơn Việt Nam)", "",
              "| Nhóm | Thuốc có đáp án | Nhận đúng | Nhận nhầm | Gợi ý | Không nhận ra |", "|---|---|---|---|---|---|"]
    for g in ("mimic", "vn", "all"):
        v = nm[g]
        lines.append(f"| {g} | {v['drug_items']} | {v['correct_rate']} | {v['wrong_rate']} | {v['suggest_rate']} | "
                     f"{v['unknown_rate']} |")
    b = x["burden"]
    lines += ["", f"Trùng hoạt chất: bắt được {x['duplicates']['detected']}/{x['duplicates']['expected']}; "
              f"cảnh báo bắt buộc ONC trên đơn: {x['must_alert']['hit_major']}/{x['must_alert']['n']}.",
              f"Gánh cảnh báo mỗi đơn (trung vị / P90): thuốc–thuốc {b['ddi']['median']} / {b['ddi']['p90']}, "
              f"mức Nghiêm trọng trở lên {b['major_plus']['median']} / {b['major_plus']['p90']}, "
              f"thực phẩm {b['food']['median']} / {b['food']['p90']}. Đơn có ≥ 1 cảnh báo Nghiêm trọng: "
              f"{b['rx_with_major_plus']}. Cảnh báo có nguồn: {x['citation_rate']}.", "",
              "### Thuốc bị nhận nhầm (tối đa 40)", ""]
    for w in x["_wrong_examples"][:40]:
        lines.append(f"- {w['case']}: `{w['input']}` → {w['got']} (đáp án {', '.join(w['expected'])})")
    lines += ["", "### Trùng hoạt chất bị sót (tối đa 30)", ""]
    for m in x["_missed_dups"][:30]:
        lines.append(f"- {m['case']}: {' + '.join(m['pair'])}")
    lines += ["", "## 4. Mô phỏng phương án", "", "```json", json.dumps(r["options"], ensure_ascii=False, indent=1),
              "```", ""]
    (RESULTS / "rx_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rescore", action="store_true", help="chỉ chấm lại từ rx_predictions.jsonl")
    args = ap.parse_args()
    if not args.rescore:
        asyncio.run(predict())
    r = rescore()
    write_report(r)
    public = json.loads(json.dumps(r))
    for block in (public, public["rx"]):
        for k in [k for k in block if k.startswith("_")]:
            block.pop(k)
    (RESULTS / "rx_metrics.json").write_text(json.dumps(public, ensure_ascii=False, indent=1), encoding="utf-8")
    s = r["alashwal"]["system"]["micromedex"]
    print(f"Al-Ashwal (Micromedex): độ nhạy {s['sensitivity']}, độ đặc hiệu {s['specificity']}, PPV {s['ppv']}")
    if r["authoritative"]:
        s = r["authoritative"]["refs"]["any"]["system"]
        print(f"Al-Ashwal (chuẩn tổng hợp): độ nhạy {s['sensitivity']}, độ đặc hiệu {s['specificity']}, "
              f"PPV {s['ppv']}, F1 {s['f1']}")
    print(f"ONC: ≥ Nghiêm trọng {r['onc']['alert_major_rate']}; tên thuốc đơn thật nhận đúng "
          f"{r['rx']['normalization']['all']['correct_rate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
