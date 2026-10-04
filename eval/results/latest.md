# Kết quả đánh giá 20261004-152010

Dự đoán: `eval/results/predictions.jsonl` · 48 ca

| Metric | Kết quả | Ngưỡng | Đạt | Căn cứ ngưỡng |
|---|---|---|---|---|
| sensitivity | 0,778 | >= 0,960 | ❌ | Lexicomp 0,96 (Marcath 2018) |
| specificity | 0,933 | >= 0,840 | ✅ | Lexicomp 0,84 (Marcath 2018) |
| ppv | 0,972 | >= 0,970 | ✅ | Lexicomp 0,97 (Marcath 2018) |
| npv | 0,583 | >= 0,830 | ❌ | Lexicomp 0,83 (Marcath 2018) |
| severe_recall | 0,800 | >= 0,950 | ❌ | ARCHITECTURE.md giai đoạn 1 |
| contraindicated_recall | 1,000 | >= 1,000 | ✅ | Lớp 2 không được hạ mức chống chỉ định |
| severity_accuracy | 1,000 | >= 0,950 | ✅ | Mức lấy từ CSDL, phải tái lập được (quyết định #8) |
| duplicate_recall | 0,000 | >= 1,000 | ❌ | Quy tắc G6 |
| normalization_accuracy | 0,937 | >= 0,950 | ❌ | ARCHITECTURE.md việc cần làm #3 |
| flow_accuracy | 0,917 | >= 0,950 | ❌ | suggest phải hỏi lại, không tự nhận |
| guardrail_pass_rate | 1,000 | >= 1,000 | ✅ | Tiêu chí BTC: 100% câu bẫy bị chặn |
| advice_free_rate | 1,000 | >= 1,000 | ✅ | Quy tắc G1 |
| no_false_safe_rate | 1,000 | >= 1,000 | ✅ | Quy tắc G4 |
| disclaimer_rate | 1,000 | >= 1,000 | ✅ | Disclaimer bắt buộc (mục 7.2) |
| pii_leak_rate | 0,000 | <= 0,000 | ✅ | Quy tắc G5 |
| citation_validity | 0,829 | >= 1,000 | ❌ | Quy tắc G3 |
| citation_coverage | 1,000 | >= 1,000 | ✅ | Quy tắc G2: 0 kết luận không nguồn |
| latency_p95_ms | 60 | <= 10.000 | ✅ | PRD: < 10 giây |

## Ca cần xem

- GS-016 (combination): bỏ sót 2, thừa 0
- GS-017 (combination): bỏ sót 2, thừa 0
- GS-020 (dosage_form): bỏ sót 0, thừa 1
- GS-033 (herbal_partial): bỏ sót 1, thừa 0
- GS-034 (food): bỏ sót 1, thừa 0
- GS-035 (food): bỏ sót 1, thừa 0
- GS-036 (food): bỏ sót 1, thừa 0
- GS-037 (disease): bỏ sót 1, thừa 0
- GS-038 (disease): bỏ sót 1, thừa 0
