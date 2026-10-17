"""
compare_runs.py - Chấm nhiều bộ ca, lấy trung bình và đặt cạnh benchmark đã công bố

Cách dùng (từ gốc repo, sau khi đã có dự đoán của từng bộ):
    python eval/predict.py                                                       # golden 48 ca
    python eval/predict.py --golden eval/golden/holdout_set.jsonl --out eval/results/predictions_holdout.jsonl
    python eval/compare_runs.py
Đầu ra: eval/results/metrics_all.json (GET /api/v1/eval/metrics/all, trang "Chất lượng AI").

Hai cách lấy trung bình, ghi cả hai:
    - pooled: gộp mọi ca của mọi bộ rồi tính một lần (mỗi ca nặng như nhau) - con số nên dùng khi báo cáo.
    - mean:   trung bình cộng giá trị của từng bộ (mỗi bộ nặng như nhau).
"""
import datetime
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from metrics import THRESHOLDS, aggregate, score_case  # noqa: E402
from run_eval import read_jsonl  # noqa: E402

RUNS = [
    dict(id="golden", label="Bộ golden (48 ca)", golden="golden/golden_set.jsonl", pred="results/predictions.jsonl",
         note="Agent đã được chỉnh trên chính bộ này, nên kết quả thiên về lạc quan."),
    dict(id="holdout", label="Bộ độc lập (50 ca)", golden="golden/holdout_set.jsonl",
         pred="results/predictions_holdout.jsonl",
         note="Ca viết trước khi chạy, agent không được chỉnh theo kết quả. Đáp án lấy nguyên từ CSDL."),
]

# Số liệu đã công bố (eval/README.md mục 2). Khác bộ ca, khác cách dựng đáp án: chỉ để định vị, không so trực tiếp.
# Đã đối chiếu với bảng gốc ngày 2026-10-07: Marcath 2018 bảng 2 (PMC9797246, 145 cặp thuốc ung thư đường uống,
# chuẩn Stockley + PubMed); Al-Ashwal 2023 bảng 4 (PMC10518176, N = 255 cặp, lấy Drugs.com làm chuẩn).
_M, _A = "Marcath 2018", "Al-Ashwal 2023"
BENCHMARKS = [
    dict(name="Lexicomp", kind="db", source=_M, sensitivity=0.96, specificity=0.80, ppv=0.95, npv=0.83),
    dict(name="Micromedex", kind="db", source=_M, sensitivity=0.86, specificity=0.87, ppv=0.96, npv=0.62),
    dict(name="Facts & Comparisons", kind="db", source=_M, sensitivity=0.67, specificity=0.93, ppv=0.97, npv=0.42),
    dict(name="PEPID", kind="db", source=_M, sensitivity=0.90, specificity=0.53, ppv=0.88, npv=0.59),
    dict(name="Drugs.com", kind="db", source=_M, sensitivity=0.93, specificity=0.73, ppv=0.93, npv=0.73),
    dict(name="Epocrates Free", kind="db", source=_M, sensitivity=0.73, specificity=0.83, ppv=0.94, npv=0.45),
    dict(name="Medscape", kind="db", source=_M, sensitivity=0.79, specificity=0.73, ppv=0.92, npv=0.48),
    dict(name="RxList", kind="db", source=_M, sensitivity=0.65, specificity=0.83, ppv=0.94, npv=0.38),
    dict(name="WebMD", kind="db", source=_M, sensitivity=0.79, specificity=0.77, ppv=0.93, npv=0.49),
    dict(name="Bing AI", kind="llm", source=_A, sensitivity=0.886, specificity=0.892, ppv=0.787, npv=0.946,
         accuracy=0.890),
    dict(name="Bard", kind="llm", source=_A, sensitivity=0.823, specificity=0.625, ppv=0.496, npv=0.887,
         accuracy=0.686),
    dict(name="ChatGPT-4", kind="llm", source=_A, sensitivity=0.747, specificity=0.523, ppv=0.413, npv=0.821,
         accuracy=0.592),
    dict(name="ChatGPT-3.5", kind="llm", source=_A, sensitivity=0.823, specificity=0.392, ppv=0.378, npv=0.831,
         accuracy=0.525),
]
EXTRA = ("composite", "severity_kappa", "max_severity_accuracy", "no_record_stated_rate", "citation_marker_rate",
         "latency_p50_ms")


def values(rows):
    s = aggregate(rows)
    total = s["tp"] + s["fp"] + s["fn"] + s["tn"]
    s["accuracy"] = (s["tp"] + s["tn"]) / total if total else None
    return s


def main():
    runs, everything = [], []
    for spec in RUNS:
        gold = read_jsonl(HERE / spec["golden"])
        pred = {p["id"]: p for p in read_jsonl(HERE / spec["pred"])}
        if missing := [g["id"] for g in gold if g["id"] not in pred]:
            sys.exit(f"{spec['pred']} thiếu dự đoán cho: {', '.join(missing)}")
        rows = [score_case(g, pred[g["id"]]) for g in gold]
        everything += rows
        s = values(rows)
        runs.append(dict(id=spec["id"], label=spec["label"], note=spec["note"], n_cases=len(rows),
                         confusion={k: s[k] for k in ("tp", "fp", "fn", "tn")}, values=s,
                         review_cases=[dict(id=r["id"], category=r["category"], fn=r["fn"], fp=r["fp"])
                                       for r in rows if r["fn"] or r["fp"]],
                         db_gaps=[g["id"] for g in gold if g.get("db_gap")]))
    pooled = values(everything)
    keys = [k for k in pooled if k not in ("n_cases", "tp", "fp", "fn", "tn")]
    mean = {}
    for k in keys:
        vals = [r["values"][k] for r in runs if r["values"][k] is not None]
        mean[k] = sum(vals) / len(vals) if vals else None
    spec_of = {n: (op, thr, why) for n, op, thr, why in THRESHOLDS}
    metrics = []
    for k in [n for n, *_ in THRESHOLDS] + ["accuracy", *EXTRA]:
        op, thr, why = spec_of.get(k, (None, None, ""))
        v = pooled[k]
        passed = None if v is None or op is None else (v >= thr if op == ">=" else v <= thr)
        metrics.append(dict(key=k, op=op, threshold=thr, basis=why, pooled=v, mean=mean[k], passed=passed,
                            runs={r["id"]: r["values"][k] for r in runs}))
    out = dict(generated=datetime.datetime.now().strftime("%Y%m%d-%H%M%S"), n_cases=len(everything),
               confusion={k: pooled[k] for k in ("tp", "fp", "fn", "tn")},
               runs=[{k: v for k, v in r.items() if k != "values"} for r in runs],
               metrics=metrics, benchmarks=BENCHMARKS)
    path = HERE / "results" / "metrics_all.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    f = lambda v: "—" if v is None else f"{v:.0f}" if abs(v) > 1 else f"{v:.3f}"  # noqa: E731
    print(f"{'metric':<26}" + "".join(f"{r['id']:>10}" for r in runs) + f"{'pooled':>10}{'mean':>10}  ngưỡng")
    for m in metrics:
        mark = "" if m["passed"] is None else " ĐẠT" if m["passed"] else " CHƯA ĐẠT"
        thr = f"{m['op']} {m['threshold']}" if m["op"] else ""
        print(f"{m['key']:<26}" + "".join(f"{f(m['runs'][r['id']]):>10}" for r in runs)
              + f"{f(m['pooled']):>10}{f(m['mean']):>10}  {thr}{mark}")
    for r in runs:
        print(f"{r['label']}: {r['confusion']} · cần xem lại: {[c['id'] for c in r['review_cases']]}")
    print(f"Gộp {len(everything)} ca: {out['confusion']} -> {path}")


if __name__ == "__main__":
    main()
