"""Chỉ số chất lượng của agent (precision / recall / F1 / tỉ lệ bỏ sót) cho giao diện.

Chỉ đọc ảnh chụp do `eval/run_eval.py` ghi ra (`eval/results/metrics_latest.json`);
không chạy đánh giá trong request.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["evaluation"])

SNAPSHOT = Path(__file__).resolve().parents[4] / "eval" / "results" / "metrics_latest.json"


@router.get("/eval/metrics")
async def eval_metrics():
    if not SNAPSHOT.exists():
        raise HTTPException(404, "Chưa có kết quả đánh giá. Chạy `python eval/run_eval.py --pred ...` trước.")
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
