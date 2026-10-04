# Evaluation Report

> Báo cáo đánh giá chất lượng sản phẩm theo tiêu chí BTC.

---

## 1. Metrics

Định nghĩa, căn cứ ngưỡng và nguồn: [eval/README.md](../README.md).

**Lần chạy 2026-10-04** (`run_20261004-152010.json`): chấm LangGraph agent thật trên golden set 48 ca, dữ liệu đã làm
sạch trong Postgres. Dự đoán sinh bằng `python eval/predict.py`, chấm bằng
`python eval/run_eval.py --pred eval/results/predictions.jsonl`. Kết quả: **10/18 metric tất định đạt ngưỡng**.
Chưa chạy Ragas và LLM-as-a-judge.

| Nhóm | Metric | Target | Actual | Status |
|------|--------|--------|--------|--------|
| Phát hiện tương tác | Độ nhạy (sensitivity) | ≥ 0,96 | 0,778 | ❌ |
| | Độ đặc hiệu (specificity) | ≥ 0,84 | 0,933 | ✅ |
| | PPV / NPV | ≥ 0,97 / ≥ 0,83 | 0,972 / 0,583 | ✅ / ❌ |
| | Recall tương tác nghiêm trọng | ≥ 95% | 80,0% | ❌ |
| | Recall chống chỉ định | 100% | 100% | ✅ |
| | Đúng mức độ so với CSDL | ≥ 95% | 100% | ✅ |
| | Phát hiện trùng hoạt chất / nhóm | 100% | 0% | ❌ |
| Chuẩn hóa tên | Đúng hoạt chất và trạng thái | ≥ 95% | 93,7% | ❌ |
| | Đúng luồng xử lý (lookup / clarify / unknown) | ≥ 95% | 91,7% | ❌ |
| An toàn | Qua câu bẫy guardrail | 100% | 100% | ✅ |
| | Không khuyên dùng thuốc (regex) | 100% | 100% | ✅ |
| | Không kết luận "an toàn" khi không có bản ghi | 100% | 100% | ✅ |
| | Có disclaimer | 100% | 100% | ✅ |
| | Lộ PII | 0% | 0% | ✅ |
| Trích dẫn | Trích dẫn hợp lệ / đủ trích dẫn | 100% / 100% | 82,9% / 100% | ❌ / ✅ |
| Ragas | Faithfulness | ≥ 0,90 | — | ⏳ |
| | Factual correctness (F1) | ≥ 0,70 | — | ⏳ |
| | Context recall / precision | ≥ 0,95 / ≥ 0,80 | — | ⏳ |
| | Tool call F1 | ≥ 0,90 | — | ⏳ |
| LLM-as-a-judge | Điểm rubric (kiểu HealthBench) | ≥ 0,80 | — | ⏳ |
| Vận hành | Latency p95 | ≤ 10 s | 0,06 s (p50 0,03 s) | ✅ |
| | User satisfaction | > 4/5 | — | ⏳ |
| | Test coverage | > 60% | — | ⏳ |

Latency đo trong tiến trình, sau khi danh mục tên thuốc đã nạp vào bộ nhớ (lần gọi đầu mất khoảng 2 giây), chưa tính
mạng và chưa có bước LLM giải thích.

### Nguyên nhân các metric chưa đạt

| Nguyên nhân | Ca | Metric bị kéo xuống |
|---|---|---|
| Biệt dược phối hợp (Augmentin, Biseptol, Tiffy, Decolgen, Hoạt huyết dưỡng não) trỏ tới nhiều hoạt chất nên bộ chuẩn hóa trả `suggest` thay vì `ok`; agent dừng ở bước hỏi lại và không tra tương tác | GS-016, GS-017, GS-027, GS-033 | Độ nhạy, NPV, recall nghiêm trọng, chuẩn hóa, luồng |
| Graph chưa có bước tra thuốc - thức ăn, thuốc - bệnh, trùng hoạt chất và trùng nhóm (dịch vụ `run_check` của `/interactions/check` có tra thức ăn và trùng nhóm, nhưng agent thì chưa) | GS-034 đến GS-038, nhóm duplicate | Độ nhạy, NPV, phát hiện trùng |
| Bản ghi lớp 2 (Patel 2020, quy tắc dạng bào chế) không mang mã bản ghi (`rule_id`) trong trích dẫn, nên không đối chiếu được với CSDL | GS-003, GS-018 đến GS-022, GS-024 | Trích dẫn hợp lệ |
| Quy tắc "dạng này không bị tương tác" vẫn hiện mức Trung bình vì backend đang coi mọi thuốc là đường uống (`routes = oral`, còn TODO trong `check_service.py`) | GS-020 | Độ đặc hiệu |
| Tên sai chính tả "augmetin" chỉ gợi ý một trong hai hoạt chất của Augmentin | GS-031 | Chuẩn hóa |

Phần agent đã làm đúng: mọi cặp tìm được đều đúng mức độ so với CSDL, không có câu khuyên đổi thuốc, không có kết
luận "an toàn", mọi kết luận đều có trích dẫn và disclaimer.

## 2. Test Results

### Unit Tests
```
pytest tests -q --continue-on-collection-errors      (2026-10-04, Python 3.11)
68 passed, 1 skipped, 1 error

ERROR tests/test_api/test_interactions.py
  src/services/ddi_repository.py:15: from src.config import get_settings
  ModuleNotFoundError: No module named 'src.config'
```

`src/config.py` đã chuyển sang `interface/backend/config.py` nhưng `src/services/ddi_repository.py` và
`src/services/llm.py` vẫn import đường cũ, nên bộ test của bước LLM giải thích không nạp được. `ruff check` báo 2 lỗi
(`src/services/llm.py`: `get_settings` chưa định nghĩa; `src/api/routes.py`: thứ tự import).

### Integration Tests
- `python eval/run_eval.py --oracle`: harness tự kiểm tra bằng đáp án chuẩn, 17/17 metric tất định đạt (không tính
  latency).
- `python eval/predict.py` rồi `run_eval.py --pred`: agent thật trên Postgres, kết quả ở mục 1.
- `python db/audit_mvp.py data/mvp db/mvp_schema.sql`: dữ liệu qua mọi kiểm tra cấu trúc (khóa chính, khóa ngoại,
  kiểu, NOT NULL).

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

- [ ] Bộ chuẩn hóa: tên biệt dược phối hợp trỏ tới nhiều hoạt chất phải là `ok` với đủ các hoạt chất, không phải `suggest`
- [ ] Agent: khi còn tên chưa rõ vẫn tra các thuốc đã rõ, và nêu tên nào chưa tra được
- [ ] Thêm bước tra thuốc - thức ăn, thuốc - bệnh, trùng hoạt chất, trùng nhóm vào graph
- [ ] Trích dẫn lớp 2 mang `rule_id` hoặc mã bản ghi Patel
- [ ] Lấy đường dùng thật của thuốc thay cho giả định `oral` khi áp quy tắc dạng bào chế
- [ ] Sửa import `src.config` để bộ test bước giải thích chạy lại; nối bước LLM giải thích vào agent
- [ ] Chạy `--ragas --judge llm` sau khi có bước LLM giải thích
- [ ] Nhờ dược sĩ rà soát golden set
