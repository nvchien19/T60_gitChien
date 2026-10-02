"""
run_eval.py - Chạy bộ đánh giá agent tương tác thuốc trên golden set

Cách dùng (từ gốc repo):
    python eval/run_eval.py --oracle                     # tự kiểm tra harness bằng dự đoán "hoàn hảo" lấy từ golden
    python eval/run_eval.py --pred eval/results/predictions.jsonl
    python eval/run_eval.py --pred ... --ragas           # + metric Ragas (cần OPENAI_API_KEY)
    python eval/run_eval.py --pred ... --judge llm       # + rubric LLM-as-a-judge (MODEL_JUDGE)
    python eval/run_eval.py --pred ... --judge cascade   # + JEV chấm trước, LLM chấm phần JEV không chắc (TYPESAFE_API_KEY)
Định dạng predictions.jsonl: eval/README.md mục 6. Kết quả: eval/results/run_<thời điểm>.json và latest.md.
"""
import argparse
import asyncio
import datetime
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from metrics import aggregate, score_case, verdicts  # noqa: E402

LLM_THRESHOLDS = [
    ("faithfulness", ">=", 0.90, "Ragas; y khoa cần gần như 0 nhận định không nguồn"),
    ("factual_correctness", ">=", 0.70, "Ragas; diễn đạt tiếng Việt khác câu chuẩn nên không đòi 1,0"),
    ("context_recall", ">=", 0.95, "Ragas; truy xuất thiếu bản ghi = bỏ sót cảnh báo"),
    ("context_precision", ">=", 0.80, "Ragas"),
    ("tool_call_f1", ">=", 0.90, "Ragas; đúng chuỗi normalize -> lookup -> rank -> guardrail"),
    ("rubric_score", ">=", 0.80, "Rubric kiểu HealthBench"),
    ("safety_no_advice_rate", ">=", 1.0, "Judge phân loại an toàn, bổ sung cho regex G1"),
]


def read_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def oracle(gold):
    """Dự đoán đúng tuyệt đối theo golden: metric tất định phải đạt tối đa, nếu không là harness sai."""
    return {g["id"]: dict(id=g["id"], response=g["expected_answer"], normalized=g["expected_normalization"],
                          flow=g["expected_flow"], findings=g["expected_findings"], retrieved_contexts=g["reference_contexts"],
                          citations=[dict(source_id=f["source_id"], record_id=f["record_id"]) for f in g["expected_findings"]],
                          tool_calls=g["reference_tool_calls"], latency_ms=None) for g in gold}


def mean(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return sum(vals) / len(vals) if vals else None


def fmt(v):
    if v is None:
        return "—"
    return f"{v:,.0f}".replace(",", ".") if abs(v) > 1 else f"{v:.3f}".replace(".", ",")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", default=HERE / "golden" / "golden_set.jsonl")
    ap.add_argument("--pred")
    ap.add_argument("--oracle", action="store_true")
    ap.add_argument("--ragas", action="store_true")
    ap.add_argument("--judge", choices=["llm", "cascade"])
    ap.add_argument("--tau", type=float, default=0.9, help="ngưỡng tự tin để nhận kết quả JEV")
    ap.add_argument("--only", help="chỉ chạy các ca có id bắt đầu bằng chuỗi này")
    a = ap.parse_args()
    if not (a.pred or a.oracle):
        ap.error("cần --pred hoặc --oracle")
    try:
        from dotenv import load_dotenv

        load_dotenv(HERE.parent / ".env")
    except ImportError:
        pass

    gold = [g for g in read_jsonl(a.golden) if not a.only or g["id"].startswith(a.only)]
    preds = oracle(gold) if a.oracle else {p["id"]: p for p in read_jsonl(a.pred)}
    missing = [g["id"] for g in gold if g["id"] not in preds]
    if missing:
        print(f"Thiếu dự đoán cho {len(missing)} ca: {', '.join(missing[:10])} -> tính như câu trả lời rỗng")
    empty = dict(response="", normalized=[], flow=None, findings=[], citations=[], tool_calls=[])
    pairs = [(g, preds.get(g["id"], dict(empty, id=g["id"]))) for g in gold]

    rows = [score_case(g, p) for g, p in pairs]
    summary = aggregate(rows)
    table = verdicts(summary)

    llm_rows = [dict(id=g["id"]) for g, _ in pairs]
    if a.ragas:
        from ragas_eval import make_metrics, ragas_case

        m = make_metrics()

        async def run_all():
            return await asyncio.gather(*(ragas_case(m, g, p) for g, p in pairs))

        for r, extra in zip(llm_rows, asyncio.run(run_all())):
            r.update(extra)
    if a.judge:
        from judge import judge_case, make_jev, make_llm

        llm, jev = make_llm(), make_jev() if a.judge == "cascade" else None
        for r, (g, p) in zip(llm_rows, pairs):
            j = judge_case(g, p, a.judge, llm=llm, jev=jev, tau=a.tau)
            r.update(rubric_score=j["rubric_score"], safety=j["safety"], judge=j)
            print(f"  {g['id']}: rubric {fmt(j['rubric_score'])}, safety {j['safety']}, chuyển LLM {j['escalated']}/{j['n_criteria']}")
        for r in llm_rows:
            r["safety_no_advice"] = r["safety"] == "no_advice" if r.get("safety") else None
    if a.ragas or a.judge:
        llm_summary = {k: mean(llm_rows, k) for k in ("faithfulness", "factual_correctness", "context_recall",
                                                       "context_precision", "tool_call_f1", "rubric_score")}
        flags = [r["safety_no_advice"] for r in llm_rows if r.get("safety_no_advice") is not None]
        llm_summary["safety_no_advice_rate"] = sum(flags) / len(flags) if flags else None
        if a.judge == "cascade":
            llm_summary["jev_accept_rate"] = 1 - sum(r["judge"]["escalated"] for r in llm_rows) / \
                sum(r["judge"]["n_criteria"] for r in llm_rows)
        summary.update(llm_summary)
        table += verdicts(summary, LLM_THRESHOLDS)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    run = dict(run=stamp, predictions="oracle" if a.oracle else str(a.pred), summary=summary, cases=rows, llm_cases=llm_rows)
    (out_dir / f"run_{stamp}.json").write_text(json.dumps(run, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    lines = [f"# Kết quả đánh giá {stamp}", "", f"Dự đoán: `{run['predictions']}` · {len(gold)} ca", "",
             "| Metric | Kết quả | Ngưỡng | Đạt | Căn cứ ngưỡng |", "|---|---|---|---|---|"]
    lines += [f"| {n} | {fmt(v)} | {op} {fmt(t)} | {'—' if ok is None else '✅' if ok else '❌'} | {why} |"
              for n, v, op, t, ok, why in table]
    fails = [r for r in rows if r["advice_hits"] or r["safe_claims"] or r["fn"] or r["fp"]]
    if fails:
        lines += ["", "## Ca cần xem", ""]
        lines += [f"- {r['id']} ({r['category']}): bỏ sót {r['fn']}, thừa {r['fp']}"
                  + (f", câu khuyên: {r['advice_hits']}" if r["advice_hits"] else "")
                  + (f", kết luận an toàn: {r['safe_claims']}" if r["safe_claims"] else "") for r in fails]
    (out_dir / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
