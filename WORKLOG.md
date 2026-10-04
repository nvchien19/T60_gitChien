# Worklog — Team P-060 (Rà Thuốc)

> Ghi lại tất cả công việc đã làm theo ngày. Ai làm gì, kết quả gì.
>
> Tổng hợp từ lịch sử git (người ghi là tác giả commit). Cột Time để "—" vì git không ghi thời gian làm việc; từng
> thành viên tự điền số giờ của mình.

---

## 2026-10-04

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Chiến | Lệnh `npm run dev` khởi động cả backend và frontend | ✅ Done | `interface/fontend/scripts/dev.mjs` (`d87add9`) | — |
| Duy | Viết lại Brief, PRD, Wireframe theo vai trò Bác sĩ và Dược sĩ; thêm luồng người dùng | ✅ Done | `docs/gate_01/*.docx`, `docs/USER_FLOW.md` (`6b09b40`) | — |
| Duy | Rà soát và làm sạch dữ liệu, nạp lại Postgres, viết tài liệu dữ liệu | ✅ Done | `db/audit_mvp.py`, `docs/DATA_PIPELINE.md` (`0a1debf`) | — |
| Duy | Viết lại README theo khung của đội, sơ đồ kiến trúc, Journal, Worklog | ✅ Done | `README.md`, `docs/architecture_diagram.md`, `JOURNAL.md`, `WORKLOG.md` | — |
| Duy | Chấm agent thật trên golden set 48 ca | 🔄 WIP | `eval/predict.py`, `eval/results/report.md`: 10/18 metric đạt, độ nhạy 0,778 | — |
| Cả nhóm | CI trên GitHub Actions | ❌ Blocked | Job không khởi động do tài khoản tổ chức vướng thanh toán; cần BTC xử lý | - |

**Tổng kết ngày:** Dữ liệu sạch đã vào Database và có tài liệu đầy đủ. Lần đầu chấm agent thật: các metric an toàn
đạt 100%, nhưng độ nhạy chưa đạt vì biệt dược phối hợp và các loại tương tác ngoài thuốc - thuốc.

---

## 2026-10-03

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Duy | Bước LLM giải thích tương tác có kiểm tra grounding; schema và script nạp Postgres | ✅ Done | `src/services/{ddi_check,ddi_repository,explainer,grounding,guardrail}.py`, `db/mvp_schema.sql`, `tests/test_api/test_interactions.py` (`d51556b`) | — |
| Duy | Kế hoạch công việc đến 07/10 | ✅ Done | `docs/KE_HOACH_DEN_07-10.md` | — |
| Chiến | Màn nhập đơn thuốc | ✅ Done | `PrescriptionEditor.tsx`, `prescription-normalize.ts` (`8dfaca2`) | — |
| Chiến | Giao diện di động | ✅ Done | `d8d3388`, `40358cd` | — |
| Chiến | Frontend gọi API thật; thêm trường HITL cho ca xem xét | ✅ Done | `interface/fontend/lib/api.ts`, 2 migration Alembic, `tests/test_api/test_reviews.py` (`7dab186`) | — |
| Chiến | Sửa cấu hình hook ghi log | ✅ Done | `0415453` | — |

**Tổng kết ngày:** Frontend chuyển từ dữ liệu giả sang API thật. Bước LLM giải thích có mã nguồn và test, nhưng chưa
nối vào ứng dụng đang chạy.

---

## 2026-10-02

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Chiến | Backend FastAPI: router thuốc, tương tác, đơn thuốc, nguồn; tách lõi AI `src/` khỏi backend; Alembic | ✅ Done | `interface/backend/`, `alembic/` (`d551b2b`, 78 file) | — |
| Chiến | Bổ sung cột còn thiếu cho bảng dữ liệu, script backfill | ✅ Done | `db/backfill_mvp_columns.py`, 2 migration (`ec3cbfb`) | — |

**Tổng kết ngày:** Có backend chạy được trên dữ liệu thật và LangGraph agent
`normalize → lookup → rank → explain → guardrail`.

---

## 2026-10-01

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Hân | Cập nhật Journal tuần 1 | ✅ Done | `JOURNAL.md` (`7d2f29d`) | — |
| Duy | Bộ đánh giá: golden set 48 ca, metric tất định, Ragas, LLM judge | ✅ Done | `eval/` (`f4ea53e`); `--oracle` đạt | — |
| Duy | Schema Postgres, script nạp dữ liệu, dịch vụ `db` trong docker-compose | ✅ Done | `db/mvp_schema.sql`, `db/load_mvp.py` (`3cfc8b4`) | — |
| Duy | Sửa ghi log AI | ✅ Done | `ab7c098`, `63f839e` | — |

**Tổng kết ngày:** Có thước đo cho agent trước khi viết agent. Dữ liệu nạp được vào Postgres.

---

## 2026-09-30

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Chiến | Tài liệu phát triển backend | ✅ Done | `docs/BE_DEVELOPMENT.md` (`d30dd6d`) | — |
| Duy | Thu thập và dựng dữ liệu: DAV, DDInter, Patel 2020, PK-DDIP, openFDA | ✅ Done | `data/mvp/` 15 bảng (không nằm trong git) | — |
| Duy | Cơ sở tri thức tham chiếu cho đánh giá | ✅ Done | `eval/golden/reference_kb.json` (`76bdba7`) | — |

**Tổng kết ngày:** Có bộ dữ liệu tương tác thuốc đầu tiên nối với danh mục thuốc Việt Nam.

---

## 2026-09-29

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Chiến | Viết lại kiến trúc hệ thống và kiến trúc frontend | ✅ Done | `ARCHITECTURE.md`, `docs/architecture/frontend.md` (`ca40a56`) | — |
| Chiến | Giao diện Next.js đầu tiên, chế độ sáng và tối | ✅ Done | `interface/fontend/` (`eb1be56`, `e10459e`) | — |
| Chiến | Sửa hook ghi log cho opencode | ✅ Done | `b8248f8` | — |

**Tổng kết ngày:** Có kiến trúc đích và bản UI đầu tiên để demo.

---

## 2026-09-25

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Duy | Brief, PRD, Wireframe cho Gate 1; đề bài | ✅ Done | `Topic.md`, bộ PDF Gate 1 (`de8b8d0`, `fb84d21`) | — |

**Tổng kết ngày:** Nộp Gate 1.

---

## 2026-09-16 đến 2026-09-19

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Duy | Sửa hook ghi log AI chạy trên Windows (bash WSL, stub Python của Windows Store) | ✅ Done | `scripts/_ailog_paths.py`, `_pyrun.*` (`91d9098`, `5fe823f`, `889d308`) | — |
| Chiến | Hook ghi log cho opencode | ✅ Done | `ae4b996`, `25f8edc` | — |
| Hân | Bản nháp brief; sửa `.env.example` và script ghi log Antigravity | ✅ Done | `2268841`, `b782e31` | — |
| Duy | Ghi chú hướng dẫn dùng template | ✅ Done | `project-template-guide.md` (`6e9b275`) | — |

**Tổng kết:** Cả nhóm cài xong môi trường, hook ghi log AI chạy trên máy từng người.

---

<!-- Format: copy block trên cho mỗi ngày làm việc -->
