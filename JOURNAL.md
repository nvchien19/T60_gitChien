# Weekly Journal — Team P-060 (Rà Thuốc)

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp.
>
> Thành viên: Nguyễn Văn Chiến, Nguyễn Ngọc Hân, Nguyễn Cảnh Duy.
> Phần "Đã hoàn thành" đối chiếu với lịch sử git; chi tiết theo ngày ở [WORKLOG.md](WORKLOG.md).

---

## Giai đoạn chuẩn bị: 10/09 - 27/09/2026

### Mục tiêu
- [x] Nhận repo từ template AI20K, cả nhóm cài được môi trường và hook ghi log AI
- [x] Chốt đề bài P-060 và nộp bộ tài liệu Gate 1 (Brief, PRD, Wireframe)

### Đã hoàn thành
- Sửa hook ghi log AI để chạy được trên Windows: bỏ phụ thuộc bash, tránh gọi nhầm bash của WSL, bỏ qua stub Python
  của Windows Store (16/09).
- Thêm hook ghi log cho opencode và Antigravity (17/09 - 19/09).
- Viết Brief, PRD, Wireframe và [Topic.md](Topic.md) cho Gate 1 (25/09).

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Hook pre-push của template gọi bash, trên Windows trỏ nhầm sang WSL hoặc không có | Viết lại phần dò đường dẫn bằng Python (`scripts/_ailog_paths.py`), sửa `_pyrun.cmd/.sh` | Cả nhóm push được và log AI lên máy chấm |
| Mỗi người dùng một công cụ AI khác nhau | Cấu hình hook riêng cho Claude Code, Cursor, Codex, Gemini, Copilot, opencode, Antigravity | Log được ghi từ mọi công cụ |

### Bài học
- Kiểm tra công cụ của template trên đúng hệ điều hành cả nhóm dùng trước khi bắt đầu viết code.

---

## Week 1: 28/09 - 1/10/2026

### Mục tiêu tuần này
- [x] Tạo features và test lên khách hàng tiềm năng
- [x] Build First UI
- [x] Chạy demo trước mặt khách hàng tiềm năng

### Đã hoàn thành
- Tất cả các mục đề ra.
- Viết lại [ARCHITECTURE.md](ARCHITECTURE.md) và tài liệu kiến trúc frontend (29/09).
- Giao diện Next.js đầu tiên, có chế độ sáng và tối (29/09).
- Thu thập và dựng dữ liệu: danh mục thuốc DAV, DDInter 2.0, Patel 2020, PK-DDIP, nhãn openFDA thành 15 bảng
  `data/mvp/` (30/09).
- Tài liệu phát triển backend [docs/BE_DEVELOPMENT.md](docs/BE_DEVELOPMENT.md) (30/09).
- Bộ đánh giá `eval/`: golden set 48 ca, metric tất định, Ragas, LLM-as-a-judge; chế độ tự kiểm tra `--oracle` đạt
  (01/10).
- Schema Postgres và script nạp dữ liệu `db/mvp_schema.sql`, `db/load_mvp.py` (01/10).

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Tên thuốc ở Việt Nam viết rất nhiều kiểu, không khớp tên hoạt chất tiếng Anh của DDInter | Nối tên theo nhiều bước: từ điển của dự án, khác chính tả Việt/Anh, bỏ tên muối, so gần đúng; tên không chắc chỉ ghi `suggest` | 62,9% dòng hoạt chất của thuốc còn hiệu lực nối chắc chắn được với nguồn tương tác |
| Người dùng thử muốn biết vì sao có tương tác, không chỉ biết là có | Thêm bước LLM giải thích, chỉ diễn giải bản ghi đã tra được | Đưa vào kế hoạch tuần 2 |
| Dữ liệu `data/` lớn và có nguồn chỉ cho dùng phi thương mại | Loại `data/` khỏi git, ghi giấy phép từng nguồn trong bảng `sources` | Repo nhẹ, giấy phép minh bạch |
| Chưa có agent thật để chấm | Dựng harness đánh giá trước, tự kiểm tra bằng đáp án chuẩn (`--oracle`) | Có sẵn thước đo khi agent chạy được |

### Bài học
- Mức độ tương tác phải lấy thẳng từ bản ghi nguồn; LLM chỉ dùng để diễn giải thì mới kiểm chứng được.
- Dựng bộ đánh giá trước khi viết agent giúp chốt sớm định dạng đầu ra giữa các thành viên.

### Kế hoạch tuần sau
- [x] Chốt API contract giữa frontend, backend và bộ đánh giá
- [x] Backend chạy thật trên dữ liệu thật
- [x] Làm sạch dữ liệu và nạp vào Postgres
- [x] Chấm agent thật, điền kết quả vào `eval/results/report.md`

---

## Week 2: 02/10 - 07/10/2026

### Mục tiêu tuần này
- [x] Backend FastAPI và LangGraph agent chạy được từ đầu đến cuối
- [x] Frontend gọi API thật, dùng được trên điện thoại
- [x] Dữ liệu sạch, nạp vào Postgres, có tài liệu mô tả
- [x] Đổi vai trò người dùng sang Bác sĩ và Dược sĩ, viết lại bộ Gate 1
- [ ] Chấm agent thật đạt ngưỡng
- [ ] Deploy, slide, video demo (hạn 12:00 ngày 07/10)

### Đã hoàn thành
- Backend `interface/backend/`: router thuốc, tương tác, đơn thuốc, nguồn dữ liệu; migration Alembic; tách lõi AI
  `src/` khỏi backend web (02/10).
- Bước giải thích bằng LLM có kiểm tra grounding (`src/services/explainer.py`, `grounding.py`) và test (03/10).
- Frontend: màn nhập đơn, giao diện di động, gọi API thật; `npm run dev` khởi động cả backend và frontend
  (03/10 - 04/10).
- Rà soát và làm sạch dữ liệu: bỏ ký tự ẩn, bản ghi trùng, mảnh câu; tách các hoạt chất bị gộp nhầm; nối lại thuốc
  kháng acid bị sót. Chi tiết ở [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md) (04/10).
- Viết lại Brief, PRD, Wireframe theo vai trò Bác sĩ và Dược sĩ; thêm [docs/USER_FLOW.md](docs/USER_FLOW.md) (04/10).
- Viết lại README theo khung của đội, sơ đồ kiến trúc, Journal, Worklog (04/10).
- Chấm agent thật trên golden set 48 ca bằng `eval/predict.py`: 10/18 metric tất định đạt; các metric an toàn
  (guardrail, không khuyên đổi thuốc, không kết luận "an toàn", trích dẫn đủ) đều đạt 100% (04/10).

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Rà lại thấy dữ liệu chưa sạch: ký tự ẩn, bản ghi trùng, khoảng 130 dòng thuốc kháng acid không nối được nguồn tương tác | Viết `db/audit_mvp.py`, sửa trong script pipeline rồi dựng lại, không sửa tay CSV | Số dòng nối chắc chắn tăng từ 54.933 lên 55.123; kết quả dựng tái lập được |
| Đổi hướng người dùng từ Dược sĩ và Bệnh nhân sang Bác sĩ và Dược sĩ | Viết lại bộ Gate 1, thêm quy trình dược sĩ chuyển ca cho bác sĩ kèm phiếu bằng chứng | Tài liệu đã xong; giao diện đang chỉnh theo |
| Chấm agent thật chỉ đạt 10/18 metric (độ nhạy 0,778): biệt dược phối hợp bị trả `suggest`, graph chưa tra thức ăn, bệnh, trùng hoạt chất | Ghi nguyên nhân từng metric và việc cần làm vào `eval/results/report.md` | Có danh sách sửa cụ thể cho các ngày còn lại |
| Hai phần mã nguồn đọc dữ liệu ở hai nơi (schema `public` và `mvp`); `src/config.py` chuyển chỗ làm hỏng import của bước LLM giải thích | Nạp dữ liệu sạch vào cả hai nơi; ghi lại trong tài liệu dữ liệu và báo cáo đánh giá | Ứng dụng chạy trên dữ liệu sạch; việc gộp và sửa import còn mở |
| GitHub Actions không chạy do tài khoản tổ chức vướng thanh toán | Chạy lint và test trên máy trước khi push; báo BTC | Chờ BTC xử lý |

### Bài học
- "Không có bản ghi" khác "an toàn": một lỗi nối tên trong dữ liệu là đủ làm mất cảnh báo, nên phải kiểm tra dữ liệu
  bằng script chứ không tin vào mắt.
- Sửa dữ liệu trong script và dựng lại thì cả nhóm mới tái lập được; sửa tay CSV sẽ mất ở lần dựng sau.

### Kế hoạch tuần sau
- [ ] Sửa các lỗi agent nêu trong `eval/results/report.md`, chấm lại
- [ ] Hoàn thiện luồng Bác sĩ và Dược sĩ trên giao diện
- [ ] Deploy lên cloud, có Live URL
- [ ] Slide và video demo cho Demo Day
- [ ] Nhờ dược sĩ rà soát golden set và nội dung cảnh báo

---

<!-- Tiếp tục copy block trên cho Week 3, 4, 5, 6 -->
