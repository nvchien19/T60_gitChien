"""Chỉ số chất lượng của agent (precision / recall / F1 / tỉ lệ bỏ sót) cho giao diện.

Chỉ đọc ảnh chụp do `eval/run_eval.py` ghi ra (`eval/results/metrics_latest.json`);
không chạy đánh giá trong request. `/eval/metrics/all` đọc bảng gộp nhiều bộ ca kèm benchmark
do `eval/compare_runs.py` ghi ra (`eval/results/metrics_all.json`). `/eval/metrics/rx` đọc chỉ số của chức
năng kiểm tra đơn trên bộ ca đơn thật và nguồn công bố, do `eval/run_rx_eval.py` ghi ra (`eval/results/rx_metrics.json`).
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["evaluation"])

RESULTS = Path(__file__).resolve().parents[4] / "eval" / "results"
SNAPSHOT = RESULTS / "metrics_latest.json"
SNAPSHOT_ALL = RESULTS / "metrics_all.json"
SNAPSHOT_RX = RESULTS / "rx_metrics.json"


@router.get("/eval/metrics")
async def eval_metrics():
    if not SNAPSHOT.exists():
        raise HTTPException(404, "Chưa có kết quả đánh giá. Chạy `python eval/run_eval.py --pred ...` trước.")
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


@router.get("/eval/metrics/all")
async def eval_metrics_all():
    if not SNAPSHOT_ALL.exists():
        raise HTTPException(404, "Chưa có bảng gộp các lượt đánh giá. Chạy `python eval/compare_runs.py` trước.")
    return json.loads(SNAPSHOT_ALL.read_text(encoding="utf-8"))


@router.get("/eval/metrics/rx")
async def eval_metrics_rx():
    if not SNAPSHOT_RX.exists():
        raise HTTPException(404, "Chưa có chỉ số kiểm tra đơn. Chạy `python eval/run_rx_eval.py` trước.")
    return json.loads(SNAPSHOT_RX.read_text(encoding="utf-8"))
