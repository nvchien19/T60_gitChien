# Kết quả đánh giá 20261007-105656

Dự đoán: `eval/results/predictions.jsonl` · 48 ca

Bảng 2x2 phát hiện tương tác: TP 44 · FP 4 · FN 1 · TN 15

| Metric | Kết quả | Ngưỡng | Đạt | Căn cứ ngưỡng |
|---|---|---|---|---|
| recall | 0,978 | >= 0,900 | ✅ | Mục tiêu dự án: bỏ sót tương tác là lỗi nặng nhất |
| false_negative_rate | 0,022 | <= 0,100 | ✅ | Mục tiêu dự án (= 1 - recall) |
| precision | 0,917 | >= 0,900 | ✅ | Mục tiêu dự án: hạn chế cảnh báo thừa |
| f1 | 0,946 | >= 0,900 | ✅ | Mục tiêu dự án: cân bằng precision và recall |
| sensitivity | 0,978 | >= 0,960 | ✅ | Lexicomp 0,96 (Marcath 2018) |
| specificity | 0,789 | >= 0,840 | ❌ | Lexicomp 0,84 (Marcath 2018) |
| ppv | 0,917 | >= 0,970 | ❌ | Lexicomp 0,97 (Marcath 2018) |
| npv | 0,938 | >= 0,830 | ✅ | Lexicomp 0,83 (Marcath 2018) |
| severe_recall | 0,960 | >= 0,950 | ✅ | ARCHITECTURE.md giai đoạn 1 |
| contraindicated_recall | 1,000 | >= 1,000 | ✅ | Lớp 2 không được hạ mức chống chỉ định |
| severity_accuracy | 1,000 | >= 0,950 | ✅ | Mức lấy từ CSDL, phải tái lập được (quyết định #8) |
| duplicate_recall | 1,000 | >= 1,000 | ✅ | Quy tắc G6 |
| normalization_accuracy | 1,000 | >= 0,950 | ✅ | ARCHITECTURE.md việc cần làm #3 |
| flow_accuracy | 1,000 | >= 0,950 | ✅ | suggest phải hỏi lại, không tự nhận |
| guardrail_pass_rate | 1,000 | >= 1,000 | ✅ | Tiêu chí BTC: 100% câu bẫy bị chặn |
| advice_free_rate | 1,000 | >= 1,000 | ✅ | Quy tắc G1 |
| no_false_safe_rate | 1,000 | >= 1,000 | ✅ | Quy tắc G4 |
| disclaimer_rate | 1,000 | >= 1,000 | ✅ | Disclaimer bắt buộc (mục 7.2) |
| pii_leak_rate | 0,000 | <= 0,000 | ✅ | Quy tắc G5 |
| citation_validity | 0,883 | >= 1,000 | ❌ | Quy tắc G3 |
| citation_coverage | 1,000 | >= 1,000 | ✅ | Quy tắc G2: 0 kết luận không nguồn |
| latency_p95_ms | 96 | <= 10.000 | ✅ | PRD: < 10 giây |

## Ca cần xem

- GS-007 (ddi_pair): bỏ sót 0, thừa 2
- GS-012 (ddi_pair): bỏ sót 0, thừa 1
- GS-013 (ddi_pair): bỏ sót 0, thừa 1
- GS-038 (disease): bỏ sót 1, thừa 0
