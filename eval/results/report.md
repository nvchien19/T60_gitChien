# Evaluation Report

> Báo cáo đánh giá chất lượng sản phẩm theo tiêu chí BTC.

---

## 1. Metrics

Định nghĩa, căn cứ ngưỡng và nguồn: [eval/README.md](../README.md). Số liệu điền từ `eval/results/latest.md` sau khi chạy `python eval/run_eval.py --pred ... --ragas --judge llm` trên golden set 48 ca.

| Nhóm | Metric | Target | Actual | Status |
|------|--------|--------|--------|--------|
| Phát hiện tương tác | Độ nhạy (sensitivity) | ≥ 0,96 | — | ⏳ |
| | Độ đặc hiệu (specificity) | ≥ 0,84 | — | ⏳ |
| | PPV / NPV | ≥ 0,97 / ≥ 0,83 | — | ⏳ |
| | Recall tương tác nghiêm trọng | ≥ 95% | — | ⏳ |
| | Recall chống chỉ định | 100% | — | ⏳ |
| | Đúng mức độ so với CSDL | ≥ 95% | — | ⏳ |
| | Phát hiện trùng hoạt chất / nhóm | 100% | — | ⏳ |
| Chuẩn hóa tên | Đúng hoạt chất và trạng thái | ≥ 95% | — | ⏳ |
| An toàn | Qua câu bẫy guardrail | 100% | — | ⏳ |
| | Không khuyên dùng thuốc (regex + judge) | 100% | — | ⏳ |
| | Không kết luận "an toàn" khi không có bản ghi | 100% | — | ⏳ |
| | Có disclaimer | 100% | — | ⏳ |
| | Lộ PII | 0% | — | ⏳ |
| Trích dẫn | Trích dẫn hợp lệ / đủ trích dẫn | 100% / 100% | — | ⏳ |
| Ragas | Faithfulness | ≥ 0,90 | — | ⏳ |
| | Factual correctness (F1) | ≥ 0,70 | — | ⏳ |
| | Context recall / precision | ≥ 0,95 / ≥ 0,80 | — | ⏳ |
| | Tool call F1 | ≥ 0,90 | — | ⏳ |
| LLM-as-a-judge | Điểm rubric (kiểu HealthBench) | ≥ 0,80 | — | ⏳ |
| Vận hành | Latency p95 | ≤ 10 s | — | ⏳ |
| | User satisfaction | > 4/5 | — | ⏳ |
| | Test coverage | > 60% | — | ⏳ |

## 2. Test Results

### Unit Tests
```
pytest tests/ -v
# Paste output here
```

### Integration Tests
```
# Mô tả test scenarios và kết quả
```

## 3. User Feedback

| User | Feedback | Rating |
|------|----------|--------|
| [User 1] | [feedback] | [1-5] |
| [User 2] | [feedback] | [1-5] |

## 4. Demo Results

- Ngày demo: [YYYY-MM-DD]
- Người tham gia: [số người]
- Feedback chung: [tóm tắt]
- Issues phát hiện: [danh sách]

## 5. Action Items

- [ ] [Cần cải thiện 1]
- [ ] [Cần cải thiện 2]
