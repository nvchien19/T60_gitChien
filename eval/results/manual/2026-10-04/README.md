# Bằng chứng manual API — 2026-10-04

Năm ca được gọi trực tiếp tới backend local (`http://127.0.0.1:8000`). Request/response JSON UTF-8 nguyên bản được
lưu để có thể đối chiếu; chỉ dùng tên thuốc tổng hợp, không chứa thông tin cá nhân.

| Ca | Mục tiêu | Kết quả |
|---|---|---|
| [TC-01](TC-01/) | Aspirin + Warfarin: `major`, có citation | PASS |
| [TC-02](TC-02/) | Panadol chuẩn hóa thành Acetaminophen; `moderate` | PASS |
| [TC-03](TC-03/) | Thuốc không nhận diện trả `unknown`, không kết luận an toàn | PASS |
| [TC-04](TC-04/) | Tên gần đúng trả `suggest` và gợi ý cần xác nhận | PASS |
| [TC-05](TC-05/) | Tạo đơn, chạy check, tải chi tiết finding/citation | PASS |

Kết quả tổng hợp: [case-results.json](case-results.json). Metadata nguồn và ngày cập nhật: [sources-response.json](sources-response.json).
Thời điểm chạy và môi trường: [run-meta.json](run-meta.json).

## Giới hạn

- Đây là kiểm thử API, không phải kiểm định lâm sàng.
- API chưa có trường LLM confidence; ngưỡng >90% chưa được triển khai hoặc đo.
- Ngày cập nhật trả theo nguồn ở endpoint `/api/v1/sources`, chưa gắn vào từng citation/finding.
- Giao diện có mã mở popup chi tiết khi chọn finding; browser run lần này gặp HTTP 403 khi tải dữ liệu qua proxy nên chưa xác nhận thao tác click end-to-end và chưa có screenshot UI.
- TC-05 tạo đơn test tổng hợp `RX-D81A6D` và check `CHECK-7BAF8B` trong database của máy chạy thử.
