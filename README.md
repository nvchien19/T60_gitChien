# AI20K Agent Template

Template chính thức cho học viên VinUni AI20K Build Phase: cấu trúc dự án, code
mẫu và hướng dẫn kỹ thuật để xây dựng một AI Agent hoàn chỉnh — từ kiến trúc,
code, test cho đến deploy và nộp bài Demo Day.

Technical Guidebook: <https://phoenix.note.transformerlabs.ai/technical-book>

## Template có sẵn những gì

- **Cấu trúc thư mục tách lớp** — `agents/`, `api/`, `services/`, `models/` đã
  chia sẵn, không phải bàn lại từ đầu.
- **Code mẫu chạy được** — LangGraph agent (state, node, tool), FastAPI routes,
  Pydantic settings, schema.
- **Docker và CI** — Dockerfile multi-stage, `docker-compose.yml`, workflow
  GitHub Actions chạy `ruff` + `pytest` khi push lên `main`/`develop` và khi mở
  pull request vào `main`.
- **Technical Guidebook 10 chương** trong `docs/guide/`, đồng thời đọc được
  online.
- **Checklist 10 deliverables** của Demo Day.
- **AI usage logging** — hook cài sẵn cho 6 công cụ AI, log tự động gửi lên
  grading server mỗi lần `git push`.

## Yêu cầu

- Python 3.11 (phiên bản CI đang dùng)
- Git
- Docker — tuỳ chọn, chỉ cần nếu chạy `docker compose`

## Bắt đầu

### 1. Clone repo của đội

Khi đội được chốt, hệ thống tự sinh repo cho đội từ template này, nằm trong org
GitHub của khoá bạn đang học và đặt tên theo mã đội. Copy URL ở trang đội trên
Phoenix rồi clone về:

```bash
git clone https://github.com/<ORG-CỦA-KHOÁ>/<MÃ-ĐỘI>.git
cd <MÃ-ĐỘI>
```

Không cần `rm -rf .git`, `git init` hay `git remote add`: repo sinh từ template
đã bắt đầu bằng lịch sử riêng của đội và remote trỏ sẵn đúng chỗ. Chưa thấy repo
của đội thì báo BTC — repo tự tạo nằm ngoài org sẽ không được chấm.

### 2. Cài môi trường

```bash
python3.11 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường

```bash
cp .env.example .env
```

Mở `.env` và điền `OPENAI_API_KEY`. Riêng `AI_LOG_API_KEY`, mỗi thành viên tự
tạo key riêng tại [dashboard Phoenix](https://phoenix.note.transformerlabs.ai/api-keys)
rồi thay vào chỗ `<get-your-api-key-from-dashboard-phoenix>` — giá trị trong
`.env.example` chỉ là placeholder, để nguyên thì log không vào được hệ thống chấm.

### 4. Cài hook ghi log AI

```bash
bash scripts/setup_hooks.sh                                      # Linux / macOS / Git Bash
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1 # Windows PowerShell
```

Chạy một lần sau khi clone. Hook ghi lại prompt khi bạn dùng Claude Code, Cursor,
Codex CLI, Gemini CLI, Antigravity hoặc GitHub Copilot, và cài pre-push hook để
đẩy log lên server.

### 5. Chạy backend

App FastAPI nằm ở `interface/backend/main.py`. `src/main.py` là shim mỏng chỉ
re-export nên cả hai lệnh dưới đây đều chạy:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000          # như template
uvicorn interface.backend.main:app --reload --host 0.0.0.0 --port 8000  # canonical
# hoặc
make run                                                       # dùng canonical
```

Swagger UI ở <http://localhost:8000/docs>. Hoặc dùng `make test`, `make lint` —
xem `Makefile`.

### 6. Chạy giao diện

Giao diện Next.js nằm ở `interface/fontend`, chạy riêng ở cổng 3000:

```bash
cd interface/fontend
npm install
npm run dev
```

Backend đã bật CORS cho `http://localhost:3000` (`.env` → `CORS_ORIGINS`).

> Giao diện hiện vẫn chạy dữ liệu mock, chưa gọi API. Bảng ánh xạ từng màn hình
> sang endpoint tương ứng nằm ở `docs/BE_DEVELOPMENT.md`.

## Cấu trúc thư mục

```
interface/
  backend/            FastAPI app — entry point interface.backend.main:app
    api/              routers: drugs, interactions, prescriptions, sources, agent
    db/               SQLAlchemy models + async session
    repositories/     tầng SQL duy nhất được phép truy vấn DB
    schemas/          Pydantic I/O contracts
    services/         business logic (check_service)
    agent_adapter/    cầu nối duy nhất sang src/ (LangGraph)
    config.py         Pydantic Settings
    main.py           app entry point + CORS
  fontend/            Next.js 16 App Router, React 19, Tailwind v4 — cổng 3000
src/                  AI core thuần — không import FastAPI/SQLAlchemy
  agents/             LangGraph agent (graph, state, nodes)
  core/               guardrail rule-based
  services/llm.py     LLM client
  tools/              thuật toán thuần (normalize, lookup, rank)
  main.py             shim re-export app (tương thích `uvicorn src.main:app`)
tests/                pytest suite
alembic/              migration script
data/                 DDI dataset + SQLite cho dev
scripts/              Hook ghi log AI + installer
docs/
  architecture/       thiết kế kiến trúc
  guide/              Technical Guidebook (nguồn của bản online)
eval/                 Kết quả evaluation
presentation/         Slide và video Demo Day
.claude/ .codex/ .cursor/ .gemini/ .agents/ .github/hooks/
                     Config hook cho từng công cụ
.github/workflows/    CI
Dockerfile            Multi-stage build
docker-compose.yml    Chạy backend bằng Docker
README_boilerplate.md  Khung README cho dự án của đội
```

## Technical Guidebook

| Chương | Nội dung | Thời gian |
|---|---|---|
| 1 | Lời mở đầu — mục tiêu, cách sử dụng | 15 phút |
| 2 | Khởi tạo dự án — clone, setup, git workflow | 4 giờ |
| 3 | Thiết kế kiến trúc — 3-tier, diagram, ADR | 6 giờ |
| 4 | LangGraph Agent — state, node, edge, tool, RAG | 8 giờ |
| 5 | FastAPI — routes, validation, error handling, streaming | 6 giờ |
| 6 | Giao diện — Next.js và Streamlit | 6 giờ |
| 7 | DevOps — Docker, CI/CD, deploy, logging | 6 giờ |
| 8 | Kiểm thử — unit test, integration test, RAGAS | 4 giờ |
| 9 | Demo Day — 10 deliverables, checklist | 2 giờ |
| 10 | Tài nguyên — khoá học, tài liệu, BMAD method | tham khảo |

Đọc online tại <https://phoenix.note.transformerlabs.ai/technical-book>: đăng
nhập bằng GitHub (đúng account đã được BTC mời vào org của khoá), chọn tab
**Technical Book** ở sidebar trái. Bản offline nằm trong `docs/guide/`, mở được
bằng bất kỳ markdown viewer nào.

## 10 deliverables cho Demo Day

| # | Deliverable | Vị trí | Template lo tới đâu |
|---|---|---|---|
| 1 | Source code | `src/` | Khung sẵn |
| 2 | README | copy `README_boilerplate.md` thành `README.md` | Khung sẵn |
| 3 | Architecture diagram | `docs/architecture_diagram.md` | Khung sẵn |
| 4 | AI logs | LangSmith (3 biến môi trường) + auto AI usage logging | Cấu hình sẵn |
| 5 | Live URL | deploy lên Render/Vercel | CI/CD sẵn |
| 6 | Video demo | `presentation/` | Đội tự làm |
| 7 | Pitch deck | `presentation/` | Đội tự làm |
| 8 | Development journal | `JOURNAL.md` | Khung sẵn |
| 9 | Worklog | `WORKLOG.md` | Khung sẵn |
| 10 | Evaluation evidence | `eval/` | Đội tự làm |

## Tech stack

| Lớp | Công nghệ |
|---|---|
| Agent | LangGraph + LangChain 0.3 (`src/agents/`) |
| Backend | FastAPI 0.115 + Uvicorn (`interface/backend/`) |
| LLM | OpenAI, mặc định `gpt-4o-mini` (đổi trong `interface/backend/config.py`) |
| Giao diện | Next.js 16 + React 19 + Tailwind v4 (`interface/fontend/`) |
| Database | PostgreSQL 16 + pgvector, hoặc SQLite cho dev |
| Lint / test | ruff + pytest 8 |
| DevOps | Docker + GitHub Actions |

## AI usage logging

Mọi prompt được ghi vào `.ai-log/session.jsonl` và tự động gửi lên grading server
ở bước pre-push.

| Công cụ | Cấu hình | Thời điểm ghi |
|---|---|---|
| Claude Code | `.claude/settings.json` | mỗi prompt (`UserPromptSubmit`) |
| Cursor | `.cursor/hooks.json` | mỗi prompt và khi dừng |
| OpenAI Codex CLI | `.codex/hooks.json` | mỗi prompt và khi dừng |
| Gemini CLI | `.gemini/settings.json` | mỗi lượt agent chạy |
| GitHub Copilot | `.github/hooks/hooks.json` | mỗi prompt và cuối session |
| Antigravity IDE | `.agents/hooks.json` | mỗi prompt, kèm lần quét lại lúc `git push` |
| opencode | `.opencode/plugin/ai-log.ts` | mỗi prompt |

Dùng ChatGPT hay công cụ web khác thì log thủ công:

```bash
scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "What you asked"
```

## Đóng góp

Repo này là open source. Đọc [CONTRIBUTING.md](CONTRIBUTING.md) trước khi mở PR.

Nội dung trong `docs/guide/` là nguồn của Technical Book và được đồng bộ lên bản
online, nên mọi thay đổi ở đó cần review của
[@AI20K-Build-Phase/book-maintainers](https://github.com/orgs/AI20K-Build-Phase/teams/book-maintainers)
— xem [.github/CODEOWNERS](.github/CODEOWNERS).

Báo lỗ hổng bảo mật theo [SECURITY.md](SECURITY.md), đừng mở public issue.

## License

[MIT](LICENSE) — dùng tự do cho mục đích giáo dục.
