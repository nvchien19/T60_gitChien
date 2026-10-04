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
- **Giải thích có nguồn:** LLM chỉ diễn giải bản ghi đã tra được; mỗi kết luận kèm nguồn và ngày cập nhật.
- **Guardrail:** chặn lời khuyên đổi thuốc, chặn kết luận không có trích dẫn. Không có bản ghi thì ghi "chưa có bản
  ghi trong CSDL", không dùng từ "an toàn".
- **Con người xác nhận (HITL):** dược sĩ duyệt đơn có hỏi lại lần cuối; ca không chắc chắn chuyển bác sĩ kèm phiếu
  bằng chứng; bác sĩ ghi kết luận.

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
# Điền DEEPSEEK_API_KEY (bước giải thích) và AI_LOG_API_KEY (key riêng của từng thành viên)

# 4. Cài hook ghi log AI (một lần sau khi clone)
bash scripts/setup_hooks.sh        # Windows PowerShell: scripts\setup_hooks.ps1

# 5. Database (cần dữ liệu, xem ghi chú bên dưới)
docker compose up -d db
# Cách nhanh: khôi phục file dump nhận từ nhóm, theo mục 10 của docs/DATA_PIPELINE.md
# Hoặc tự nạp từ data/mvp/*.csv:
python scripts/seed_mvp.py --database-url <DATABASE_URL> --fresh   # bảng backend đọc
python db/load_mvp.py                                             # schema mvp

# 6. Chạy backend (cổng 8000) và frontend (cổng 3000) cùng lúc
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
- [x] Evaluation Evidence ([eval/results/report.md](eval/results/report.md): đã chấm agent thật, 10/18 metric tất định đạt; chưa chạy Ragas và LLM judge)

## Giới hạn hiện tại

- Dữ liệu tương tác chỉ phủ các hoạt chất có trong DDInter. Khoảng 36% dòng hoạt chất của thuốc tại Việt Nam (chủ
  yếu dược liệu, vitamin và khoáng phối hợp) chưa có bản ghi. "Chưa có bản ghi" không có nghĩa là an toàn.
- Chưa có dược sĩ rà soát nội dung chuyên môn của dữ liệu.
- DDInter và Patel 2020 chỉ cho dùng phi thương mại; PK-DDIP không ghi giấy phép. Cần xử lý trước khi thương mại hóa.
- Bản MVP không kiểm tra số đăng ký thuốc.
- Agent chưa đạt mọi ngưỡng đánh giá: độ nhạy 0,778 (ngưỡng 0,96). Chưa xử lý đúng biệt dược phối hợp và chưa tra
  thuốc - thức ăn, thuốc - bệnh, trùng hoạt chất trong graph. Chi tiết ở [eval/results/report.md](eval/results/report.md).
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
