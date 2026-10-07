"""
predict.py - Chạy agent thật trên golden set, ghi predictions.jsonl cho run_eval.py

Gọi LangGraph agent qua `interface.backend.agent_adapter.run_agent` (đúng đường mà POST /api/v1/chat dùng), nên cần
Postgres đã có dữ liệu (DATABASE_URL trong .env). Không gọi LLM: node explain của graph là tất định.

Cách dùng (chạy từ gốc repo):
    python eval/predict.py                                   # -> eval/results/predictions.jsonl
    python eval/run_eval.py --pred eval/results/predictions.jsonl

Định dạng đầu ra: eval/README.md mục 6.
"""
import argparse
import asyncio
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from interface.backend.agent_adapter import run_agent  # noqa: E402
from interface.backend.db.session import SessionLocal  # noqa: E402

GOLDEN = ROOT / "eval" / "golden" / "golden_set.jsonl"
OUT = ROOT / "eval" / "results" / "predictions.jsonl"
DDINTER_ID = re.compile(r"/interact/(\d+)/")
RANKED = {"contraindicated", "major", "moderate", "minor"}


def record_id(cite):
    """Mã bản ghi nếu trích dẫn có sẵn; `interaction_id` của DDInter lấy từ đường dẫn nguồn; còn lại dùng nhãn."""
    if cite.get("record_id"):
        return str(cite["record_id"])
    m = DDINTER_ID.search(cite.get("source_url") or "")
    return m.group(1) if m else (cite.get("label") or "")


def flow(state):
    """Luồng agent thực sự đi: còn tên `suggest` -> clarify; chỉ còn tên `unknown` -> unknown; còn lại -> lookup."""
    statuses = [n["status"] for n in state.get("normalized", [])]
    if "suggest" in statuses:
        return "clarify"
    return "unknown" if any(s != "ok" for s in statuses) else "lookup"


def to_prediction(case_id, state, latency_ms):
    findings = []
    for f in state.get("ranked_findings") or []:
        kind = f.get("kind") or "interaction"         # interaction | food | disease | duplicate_active | duplicate_class
        dup = kind.startswith("duplicate")
        if f.get("severity") not in RANKED and not dup:
            continue                                  # no_record không phải một phát hiện
        for c in f.get("citations") or [{}]:
            findings.append(dict(type=kind, drug_ids=f.get("drug_ids") or f["pair"], target=f.get("target", ""),
                                 severity="duplicate" if dup else f["severity"],
                                 source_id=c.get("source_id", ""), record_id=record_id(c)))
    return dict(
        id=case_id,
        response=state.get("response", ""),
        normalized=[dict(input=n["input"], status=n["status"],
                         drug_ids=n.get("drug_ids") or ([n["drug_id"]] if n.get("drug_id") else []))
                    for n in state.get("normalized", [])],
        flow=flow(state),
        findings=findings,
        retrieved_contexts=[f["mechanism"] for f in state.get("ranked_findings") or []
                            if f.get("severity") in RANKED and f.get("mechanism")],
        citations=[dict(source_id=c.get("source_id", ""), record_id=record_id(c)) for c in state.get("citations") or []],
        tool_calls=[],
        latency_ms=latency_ms,
    )


async def main(out):
    cases = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    out.parent.mkdir(parents=True, exist_ok=True)
    async with SessionLocal() as db:
        await run_agent(db, "Paracetamol, Warfarin", ["Paracetamol", "Warfarin"])   # nạp cache danh mục tên thuốc
        with open(out, "w", encoding="utf-8") as f:
            for case in cases:
                start = time.perf_counter()
                state = await run_agent(db, case["question"], case["input_drugs"])
                latency = round((time.perf_counter() - start) * 1000)
                f.write(json.dumps(to_prediction(case["id"], state, latency), ensure_ascii=False) + "\n")
    print(f"Đã ghi {len(cases)} dự đoán vào {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    asyncio.run(main(ap.parse_args().out))
