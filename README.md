# Rà Thuốc (P-060)

> Rà một đơn nhiều thuốc bằng tay vừa chậm vừa dễ sót tương tác → AI Agent tra tương tác thuốc trên CSDL có nguồn,
> xếp mức độ và giải thích kèm trích dẫn cho **bác sĩ và dược sĩ**, những người xác nhận và quyết định cuối cùng.

Dự án của đội P-060, VinUni AI20K Build Phase (cohort 4). Đề bài: [Topic.md](Topic.md).

## Vấn đề (Problem)

- **Ai gặp vấn đề:** bác sĩ và dược sĩ chịu trách nhiệm với đơn thuốc của bệnh nhân dùng nhiều thuốc cùng lúc
  (đa bệnh, đơn từ nhiều nơi, thêm thuốc không kê đơn và thực phẩm chức năng).
- **Tốn kém ở đâu:** phải tra thủ công từng cặp thuốc. Đơn 10 thuốc có 45 cặp cần tra, trong khi dược sĩ tại quầy
  chỉ có vài phút cho mỗi đơn.
- **Vì sao giải pháp hiện tại chưa đủ:**
  - Công cụ tra cứu quốc tế dùng tên hoạt chất tiếng Anh, còn đơn ở Việt Nam ghi tên biệt dược hoặc tên Việt hóa.
    Danh mục của Cục Quản lý Dược có 54.883 số đăng ký với rất nhiều cách viết.
  - Chatbot LLM thuần có thể bịa tương tác hoặc liều, và không chỉ ra nguồn.
  - Kết quả tra cứu thường chỉ báo "có tương tác", không nói rõ vì sao, dựa trên nguồn nào, cập nhật ngày nào.

## Giải pháp (Solution)

Agent chạy chuỗi `normalize → lookup → rank → explain → guardrail`. Kết quả là **cảnh báo tham khảo có nguồn**; AI
không khuyên ngưng, đổi hay kê thuốc, và không chẩn đoán.

- **Chuẩn hóa tên thuốc:** nhận tên biệt dược, hoạt chất, cách viết Việt hóa; hỏi lại khi tên chỉ gần đúng
  (63.572 tên tra cứu, lấy từ danh mục DAV).
- **Tra và xếp mức tương tác:** 252.768 cặp hoạt chất từ DDInter 2.0, xếp ba mức Nghiêm trọng, Trung bình, Nhẹ. Mức
  độ lấy thẳng từ bản ghi, không do LLM suy ra. Có cảnh báo trùng hoạt chất và quy tắc riêng theo dạng bào chế.
- **Giải thích có nguồn:** luồng kiểm tra hiện trả giải thích từ bản ghi đã tra trong database; module LLM giải thích
  chưa được nối vào luồng này. Finding có citation; ngày cập nhật hiện lấy riêng từ API danh sách nguồn.
- **Guardrail:** chặn lời khuyên đổi thuốc, chặn kết luận không có trích dẫn. Không có bản ghi thì ghi "chưa có bản
  ghi trong CSDL", không dùng từ "an toàn".
- **Con người xác nhận (HITL):** dược sĩ duyệt đơn có hỏi lại lần cuối; ca không chắc chắn chuyển bác sĩ kèm phiếu
  bằng chứng. MVP hiện hỗ trợ gửi ca xem xét và đổi trạng thái, nhưng chưa lưu nội dung kết luận của người xem xét.

### “Trả về read”, nguồn và độ tin cậy

Trong yêu cầu “trả về read”, nên hiểu là **đọc/tra cứu bản ghi tương tác từ database** rồi trả finding có thể truy
vết — không phải tên trường hay trạng thái chuẩn của API. Finding trả về citation (nguồn, nhãn và URL khi có);
`GET /api/v1/sources` trả giấy phép và ngày cập nhật theo nguồn. Trên giao diện, bấm vào phát hiện sẽ mở chi tiết
kết luận, hướng xử lý tham khảo và bằng chứng/đường dẫn nguồn.

LLM confidence >90% hiện **chưa được triển khai hoặc đo**: luồng kiểm tra dùng dữ liệu tất định từ database và
response chưa có trường confidence. Không được xem điểm khớp tên thuốc hay metric eval là confidence của LLM.
Nếu sau này dùng confidence làm điều kiện hiển thị, cần hiệu chuẩn trên tập được chuyên gia gán nhãn; nếu dưới 90%
hoặc chưa hiệu chuẩn, phải hiển thị cảnh báo và yêu cầu người có chuyên môn xem xét. Ngày cập nhật hiện có ở API
danh sách nguồn, chưa gắn trực tiếp vào từng citation trong popup.

Chi tiết: [ARCHITECTURE.md](ARCHITECTURE.md), [docs/USER_FLOW.md](docs/USER_FLOW.md), tài liệu Gate 1 trong
[docs/gate_01/](docs/gate_01/).

## Target User

- **Primary:** dược sĩ cấp phát tại quầy hoặc làm dược lâm sàng, rà nhiều đơn mỗi ngày.
- **Secondary:** bác sĩ kê đơn, đồng thời xác nhận lần cuối các ca dược sĩ chuyển lên.

Bệnh nhân không đăng nhập hệ thống; đơn thuốc do bác sĩ hoặc dược sĩ đưa vào.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Agent | LangGraph + LangChain (`src/agents/`) |
| LLM | DeepSeek `deepseek-chat` cho bước giải thích "vì sao" (`src/services/explainer.py`, chưa nối vào ứng dụng); agent hiện giải thích bằng mẫu tất định từ CSDL |
| Backend | FastAPI + Python 3.11 (`interface/backend/`) |
| Frontend | Next.js 16 + React 19 + Tailwind v4 + TypeScript (`interface/fontend/`) |
| Database | PostgreSQL 16 + pgvector, pg_trgm, unaccent (schema `mvp`) |
| Dữ liệu | DDInter 2.0, Patel 2020, PK-DDIP, nhãn openFDA, danh mục thuốc DAV |
| Đánh giá | Golden set 48 ca, metric tất định, Ragas, LLM-as-a-judge (`eval/`) |
| DevOps | Docker + GitHub Actions (ruff + pytest) |

## Quick Start

Cần Python 3.11, Node.js và Docker.

```bash
# 1. Clone repo
git clone https://github.com/AI20K-Build-Phase-Cohort-4/P-060.git
cd P-060

# 2. Môi trường Python
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Biến môi trường
cp .env.example .env
# Điền DEEPSEEK_API_KEY (bước giải thích)

# 4. Database (cần dữ liệu, xem ghi chú bên dưới)
docker compose up -d db
# Cách nhanh: khôi phục file dump nhận từ nhóm, theo mục 10 của docs/DATA_PIPELINE.md
# Hoặc tự nạp từ data/mvp/*.csv:
python scripts/seed_mvp.py --database-url <DATABASE_URL> --fresh   # bảng backend đọc
python db/load_mvp.py                                             # schema mvp

# 5. Chạy backend (cổng 8000) và frontend (cổng 3000) cùng lúc
cd interface/fontend
npm install
npm run dev
```

- Chỉ chạy backend: `make run`, Swagger UI ở <http://localhost:8000/docs>.
- Kiểm tra mã: `make test`, `make lint`, `make check`.
- Đánh giá agent: `python eval/predict.py` chạy agent thật trên golden set, rồi
  `python eval/run_eval.py --pred eval/results/predictions.jsonl` để chấm. Xem [eval/README.md](eval/README.md).

**Về dữ liệu ở bước 5:** thư mục `data/` không nằm trong git. Xin gói dữ liệu từ thành viên phụ trách (file dump
Postgres hoặc file zip CSV) rồi làm theo mục 10 của [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md). `DATABASE_URL`
trong `.env` phải khớp tài khoản của container Postgres đang chạy. Script seed hiện lỗi ở bảng `pk_ddi` trên
Postgres; cách nạp bỏ qua bảng này cũng nằm ở mục 10.

## Biến môi trường

Chép `.env.example` thành `.env` rồi điền. File `.env` không đưa vào git.

| Biến | Bắt buộc | Mặc định | Dùng để |
|---|---|---|---|
| `DATABASE_URL` | Có | `postgresql://ddi:ddi_dev_password@127.0.0.1:5432/ddi` | Kết nối Postgres. Dùng `127.0.0.1` thay cho `localhost` trên Windows |
| `DEEPSEEK_API_KEY` | Không | trống | Bước LLM giải thích (`src/services/explainer.py`). Để trống thì ứng dụng vẫn chạy, lời giải thích lấy từ CSDL |
| `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | Không | `https://api.deepseek.com`, `deepseek-chat` | Máy chủ và model của bước giải thích |
| `EXPLAIN_TEMPERATURE`, `EXPLAIN_TIMEOUT_S`, `EXPLAIN_VERIFY` | Không | `0.2`, `60`, `true` | Nhiệt độ, thời gian chờ và bật kiểm định từng câu của bước giải thích |
| `OPENAI_API_KEY` | Chỉ khi chạy `--ragas` hoặc `--judge` | trống | Model chấm của bộ đánh giá |
| `MODEL_JUDGE` | Không | `gpt-4o-mini` | Model chấm rubric |
| `TYPESAFE_API_KEY` | Chỉ khi chạy `--judge cascade` | trống | Dịch vụ JEV chấm trước |
| `APP_ENV`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL` | Không | `development`, `0.0.0.0`, `8000`, `INFO` | Cấu hình backend |
| `CORS_ORIGINS` | Không | `http://localhost:3000` | Nguồn frontend được phép gọi API |

## Sample Queries

Gọi sau khi backend đã chạy (`npm run dev` hoặc `make run`). Kết quả dưới đây là output thực tế ngày 2026-10-04;
bản đầy đủ từng ca ở [eval/results/manual_evidence.md](eval/results/manual_evidence.md).

```bash
curl -X POST http://localhost:8000/api/v1/interactions/check \
  -H "Content-Type: application/json" \
  -d '{"drugs": ["Panadol", "Warfarin"]}'
```

| Đầu vào (`drugs`) | Hệ thống trả về |
|---|---|
| `["Panadol", "Warfarin"]` | Nhận Panadol là Acetaminophen. Cặp Acetaminophen - Warfarin mức **Trung bình**, nguồn DDInter 2.0 kèm đường dẫn bản ghi |
| `["Dihydroergotamin", "Clarithromycin"]` | Mức **Chống chỉ định**, hai nguồn: DDInter 2.0 và nhãn FDA |
| `["Aspirin", "Ibuprofen", "Warfarin"]` | Ba cặp mức **Nghiêm trọng**, kèm cảnh báo Aspirin và Ibuprofen trùng nhóm NSAID |
| `["paracetamon", "Warfarin"]` | Tên gõ sai: gợi ý Acetaminophen (90,9%) kèm "Cần xác nhận, không tự áp dụng", chưa tra cặp này |
| `["Piracetam", "Paracetamol"]` | Cặp **chưa có bản ghi** trong CSDL. Hệ thống không kết luận an toàn |
| `["Augmentin", "Warfarin"]` | Biệt dược phối hợp: hệ thống hỏi lại hoạt chất (giới hạn hiện tại, xem bên dưới) |

Các lời gọi khác:

```bash
# Chuẩn hóa tên thuốc
curl -X POST http://localhost:8000/api/v1/drugs/normalize \
  -H "Content-Type: application/json" -d '{"drugs": ["Panadol", "paracetamon"]}'

# Danh sách nguồn dữ liệu, giấy phép và ngày cập nhật
curl http://localhost:8000/api/v1/sources
```

Trên giao diện (<http://localhost:3000>): tạo đơn, nhập các thuốc ở cột đầu vào, bấm kiểm tra, rồi bấm vào từng phát
hiện để xem chi tiết và nguồn.

## Project Structure

```
├── src/                     # Lõi AI thuần, không import FastAPI/SQLAlchemy
│   ├── agents/              # LangGraph: graph.py, state.py
│   │   └── nodes/           # normalize, clarify, lookup, rank, explain, guardrail
│   ├── tools/               # Thuật toán thuần: normalizer, lookup_core, ranker
│   ├── core/                # Guardrail theo luật
│   ├── services/            # ddi_repository, ddi_check, explainer, grounding, llm
│   └── main.py              # Shim re-export app (uvicorn src.main:app)
├── interface/
│   ├── backend/             # FastAPI: api/routers, services, repositories, schemas, db, agent_adapter
│   └── fontend/             # Next.js (tên thư mục giữ nguyên là "fontend")
├── db/                      # mvp_schema.sql, load_mvp.py, audit_mvp.py, backfill_mvp_columns.py
├── alembic/                 # Migration cho bảng nghiệp vụ
├── data/                    # Pipeline và dữ liệu (không nằm trong git)
├── eval/                    # Golden set, predict.py, metric, Ragas, judge, kết quả
├── tests/                   # Pytest
├── docs/                    # Kiến trúc, luồng người dùng, dữ liệu, Gate 1, guidebook
├── presentation/            # Slide và video Demo Day
├── scripts/                 # Hook ghi log AI
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/       # CI
```

## API Endpoints

Tất cả nằm dưới tiền tố `/api/v1`, trừ `/health`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Kiểm tra dịch vụ |
| POST | `/api/v1/drugs/normalize` | Chuẩn hóa tên thuốc về hoạt chất |
| GET | `/api/v1/drugs/search` | Gợi ý tên thuốc khi nhập |
| POST | `/api/v1/interactions/check` | Kiểm tra tương tác cho một danh sách thuốc |
| GET | `/api/v1/interactions/pair` | Tra một cặp hoạt chất |
| GET | `/api/v1/sources` | Nguồn dữ liệu, giấy phép, độ phủ |
| GET, POST | `/api/v1/prescriptions` | Danh sách đơn, tạo đơn |
| GET | `/api/v1/prescriptions/summary` | Số liệu tổng quan |
| GET | `/api/v1/prescriptions/{rx_id}` | Chi tiết một đơn |
| POST | `/api/v1/prescriptions/{rx_id}/medications` | Thêm thuốc vào đơn |
| GET, POST | `/api/v1/prescriptions/{rx_id}/checks` | Lịch sử kiểm tra, chạy kiểm tra mới |
| GET | `/api/v1/checks/{check_id}` | Kết quả một lần kiểm tra |
| GET, POST | `/api/v1/reviews` | Ca cần người có chuyên môn xem xét |
| PATCH | `/api/v1/reviews/{review_id}` | Ghi kết luận, đổi trạng thái ca |
| POST | `/api/v1/assistant/chat` | Hỏi đáp về kết quả kiểm tra |
| POST | `/api/v1/chat` | Gọi thẳng agent |
| GET | `/api/v1/status` | Trạng thái agent |

## Deliverables Checklist

- [x] Source Code (GitHub)
- [x] README.md
- [x] Architecture Diagram ([docs/architecture_diagram.md](docs/architecture_diagram.md); thiết kế chi tiết ở [ARCHITECTURE.md](ARCHITECTURE.md))
- [x] AI Logs (tự thu thập qua hook, gửi khi `git push`)
- [ ] Live URL / Deploy
- [ ] Video Demo
- [ ] Pitch Deck (`presentation/`)
- [x] Weekly Journal ([JOURNAL.md](JOURNAL.md))
- [x] Worklog ([WORKLOG.md](WORKLOG.md))
- [x] Evaluation Evidence ([eval/results/manual_evidence.md](eval/results/manual_evidence.md): 8 kịch bản manual; [eval/results/manual/2026-10-04/](eval/results/manual/2026-10-04/): 5 lượt API có request/response thô; [eval/results/report.md](eval/results/report.md): eval agent trên 48 ca, 10/18 metric tất định đạt)

## Giới hạn hiện tại

- Dữ liệu tương tác chỉ phủ các hoạt chất có trong DDInter. Khoảng 36% dòng hoạt chất của thuốc tại Việt Nam (chủ
  yếu dược liệu, vitamin và khoáng phối hợp) chưa có bản ghi. "Chưa có bản ghi" không có nghĩa là an toàn.
- Chưa có dược sĩ rà soát nội dung chuyên môn của dữ liệu.
- DDInter và Patel 2020 chỉ cho dùng phi thương mại; PK-DDIP không ghi giấy phép. Cần xử lý trước khi thương mại hóa.
- Bản MVP không kiểm tra số đăng ký thuốc.
- Agent chưa đạt mọi ngưỡng đánh giá: độ nhạy 0,778 (ngưỡng 0,96). Chưa xử lý đúng biệt dược phối hợp và chưa tra
  thuốc - thức ăn, thuốc - bệnh, trùng hoạt chất trong graph. Chi tiết ở [eval/results/report.md](eval/results/report.md).
- LLM confidence >90% chưa được triển khai/đo; ngày cập nhật nguồn chưa hiển thị theo từng finding. Chi tiết và bằng
  chứng manual ở [eval/results/manual_evidence.md](eval/results/manual_evidence.md).
- Giao diện đang được chỉnh theo luồng Bác sĩ và Dược sĩ của tài liệu Gate 1.

## Team

| Member | Role | Student ID |
|--------|------|-----------|
| Nguyễn Văn Chiến | Frontend, backend API | 2A202602926 |
| Nguyễn Ngọc Hân | Benchmark, metric, đánh giá | 2A202602511 |
| Nguyễn Cảnh Duy | Dữ liệu, LLM giải thích, tài liệu Gate 1 | 2A202602815 |

## License

[MIT](LICENSE) cho mã nguồn. Dữ liệu tương tác thuốc giữ giấy phép của từng nguồn, xem
[docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md).
