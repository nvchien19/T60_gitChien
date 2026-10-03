# Backend — `interface/backend` (FastAPI · DDI Safety API)

> **Hệ thống:** Rả thuốc — AI Agent tra cứu tương tác thuốc & cảnh báo an toàn dùng thuốc.
> **Vai trò thư mục này:** Backend API (FastAPI) — validate I/O, phân quyền, orchestration
> nghiệp vụ, truy vấn CSDL, nạp dữ liệu rồi chuyển cho lõi AI. **Không** tự suy luận mức
> nghiêm trọng bằng LLM, **không** render UI.

---

## 1. Ranh giới với lõi AI

Repo chia làm hai lớp rõ ràng:

| | `src/` — **lõi AI** | `interface/backend/` — **backend web** |
|---|---|---|
| Chứa | LangGraph agent, tools thuần, guardrail rule-based | FastAPI app, routers, DB, repositories, schemas, services |
| Framework | không FastAPI, không SQLAlchemy | FastAPI + SQLAlchemy async |
| Truy vấn DB | **không bao giờ** | qua `repositories/` |
| Test | chạy được không cần app, không cần DB | cần app + DB test |

```mermaid
graph LR
    FE["Frontend"] --> MW["middleware"]
    MW --> R["api/routers"]
    R --> S["services/check_service"]
    S --> AD["agent_adapter<br/>(CẦU NỐI DUY NHẤT)"]
    AD --> G["src/agents/graph<br/>Lõi AI"]
    AD --> T["src/tools + src/core<br/>thuần túy"]
    S --> Q["repositories/ddi_repo"]
    Q --> PG[("PostgreSQL")]
```

**Chiều phụ thuộc chỉ một chiều: `interface.backend → src`.** `src/` không bao giờ import
ngược lại — nhờ vậy test agent chạy được không cần dựng FastAPI.

Backend chạm lõi AI ở đúng **hai dạng**:

| Dạng | Ai được phép | Ví dụ |
|---|---|---|
| **Thuật toán thuần** (`src.tools`, `src.core.guardrails`) | mọi file backend | `check_service.py` gọi `rank_findings`, `guardrail_assert` |
| **LangGraph agent** (`src.agents`) | **chỉ** `agent_adapter/` | `agent_adapter` gọi `split_drugs`, `get_agent()` |

```python
# interface/backend/services/check_service.py — dùng thuật toán thuần, OK
from src.tools.ranker import rank_findings
from src.core.guardrails import guardrail_assert

# interface/backend/agent_adapter/__init__.py — nơi DUY NHẤT import src.agents
from src.agents.nodes.normalize import split_drugs
```

`src.agents` bị cô lập trong `agent_adapter` vì đó là chỗ duy nhất cần nạp DB rồi mới
gọi được graph. Các nơi khác chỉ dùng hàm thuần, không cần DB.

> Kiểm tra ranh giới:
> ```bash
> grep -rn "from src.agents" interface/backend/   # chỉ được ra agent_adapter/
> grep -rn "import interface" src/                # phải RỖNG
> ```

---

## 2. Cấu trúc thư mục

```text
interface/backend/
├── main.py                  # Entry point: app, lifespan, CORS, include_router
├── config.py                # Settings (pydantic-settings, đọc .env)
├── agent_adapter/           # ★ CẦU NỐI backend → src (lõi AI)
│   └── __init__.py          #   nạp catalog + records từ DB, gọi get_agent()
├── api/
│   ├── routes.py            # Router agent: POST /chat, GET /status
│   └── routers/
│       ├── drugs.py         # /drugs/normalize, /drugs/search
│       ├── interactions.py  # /interactions/check, /interactions/pair
│       ├── prescriptions.py # /prescriptions/*, /checks/{id}, /reviews, /assistant/chat
│       └── sources.py       # /sources — nguồn dữ liệu + độ phủ (S8)
├── db/
│   ├── base.py              # Base declarative + naming convention
│   ├── session.py           # Async engine, SessionLocal, get_session
│   └── models/tables.py     # 19 bảng SQLAlchemy
├── repositories/
│   └── ddi_repo.py          # ★ ĐIỂM QUERY DB DUY NHẤT
├── schemas/
│   ├── ddi.py               # Contract I/O chính (CheckRequest/Response, FindingOut…)
│   └── chat.py              # ChatRequest / ChatResponse
└── services/
    └── check_service.py     # Orchestration: normalize → lookup → rank → guardrail
```

Lõi AI tương ứng ở `src/`:

```text
src/
├── agents/
│   ├── graph.py             # StateGraph + get_agent() lazy singleton
│   ├── state.py             # AgentState
│   └── nodes/               # normalize · clarify · lookup · rank · explain · guardrail
├── tools/                   # normalizer · lookup_core · ranker · _khoa (hàm thuần)
├── core/guardrails.py       # Guardrail rule-based, không LLM
└── services/llm.py          # get_llm() — config do backend inject
```

Chi tiết lõi AI: xem [`src/README.md`](../../src/README.md) khi có.

---

## 3. Chạy

```bash
# 1. Cài (từ gốc repo)
pip install -r requirements.txt

# 2. Cấu hình
cp .env.example .env      # điền DATABASE_URL; OPENAI_API_KEY tuỳ chọn

# 3. Chạy
uvicorn interface.backend.main:app --reload --port 8000
# hoặc
make run
```

Swagger UI: <http://localhost:8000/docs>

### Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db` | dev dùng SQLite. Prod: `postgresql+asyncpg://user:pass@127.0.0.1:5432/rathuoc` |
| `APP_ENV` | `development` | `development`/`test` → `lifespan` tự `create_all` |
| `CORS_ORIGINS` | `http://localhost:3000` | **phân tách bằng dấu phẩy**, không dùng `*` khi `allow_credentials` |
| `OPENAI_API_KEY` | *(rỗng)* | Rỗng → chạy exact-match, không gọi LLM |
| `MODEL_NAME` | `gpt-4o-mini` | Inject cho `get_llm()` |
| `LOG_LEVEL` | `INFO` | |

`db/session.py` tự đổi scheme: `postgresql://` → `postgresql+asyncpg://`, `sqlite://` → `sqlite+aiosqlite://`.
Nên cấu hình `127.0.0.1` thay vì `localhost` để tránh rơi vào `::1` khi rule `pg_hba.conf` không khớp.

### Seed dữ liệu

```bash
python scripts/seed_mvp.py --fresh        # nạp data/mvp/*.csv vào DB
python scripts/embed_mechanisms.py        # embedding (bỏ qua nếu thiếu OPENAI_API_KEY)
alembic upgrade head                      # migration (prod)
```

---

## 4. Luồng xử lý

### 4.1 Endpoint chính — `POST /api/v1/interactions/check`

Đi qua `services/check_service.run_check()`:

```text
normalize_list()        exact trên toàn bộ aliases → fallback fuzzy rapidfuzz
  ↓                     ok / suggest / unknown (suggest KHÔNG auto-accept)
fetch_interaction_records()
  ↓                     lớp 1: DDInter exact, query cả 2 chiều
                        lớp 2: dosage_form_rules + ara_interactions
                        cặp không có bản ghi → no_record
rank_findings()         giữ mức cao nhất, gộp citations, sort giảm dần
guardrail_assert()      loại finding thiếu citation + sanitize text
  ↓
CheckResponse { normalized, findings, max_severity, no_record_pairs,
                food_findings, duplicate_findings, disclaimer, data_coverage }
```

Mức nghiêm trọng lấy **từ bản ghi nguồn**, không để LLM suy luận → cùng input + cùng DB cho cùng output.

### 4.2 Qua agent — `POST /api/v1/chat`

Đi qua `agent_adapter.run_agent()`, rồi vào LangGraph:

```mermaid
graph LR
    START --> N["normalize"]
    N --> Q{"còn suggest?"}
    Q -->|có| CL["clarify → END"]
    Q -->|không| LK["lookup"]
    LK --> RK["rank"]
    RK --> EX["explain"]
    EX --> G["guardrail"]
    G -->|pass| END1([END])
    G -->|fail| EX
```

`agent_adapter` làm đúng 3 việc — nạp dữ liệu, rồi gọi graph:

| Bước | Hàm | Vì sao ở backend |
|---|---|---|
| Nạp catalog (63k alias) | `load_catalog(db)` | lõi AI không đọc DB |
| Chuẩn hóa để biết `drug_id` | `normalize_list(db, …)` | cần `drug_id` mới tra được cặp |
| Tra bản ghi tương tác | `fetch_interaction_records(db, …)` | cần SQL |
| Chạy graph | `get_agent().ainvoke(state)` | thuần túy |

Lõi AI nhận `AgentState` đã đầy đủ dữ liệu, chỉ suy luận và diễn giải.

> `langgraph` là dependency **mềm**. Thiếu nó: `agent_available()` → `False`, `POST /chat` trả
> **503**, mọi endpoint khác vẫn chạy bình thường. Cài đủ thì `/status` trả `ready`.

---

## 5. Bảng API

Base `/api/v1`.

| Method | Path | Mô tả |
|---|---|---|
| GET | `/health` | `{status, env}` |
| POST | `/api/v1/interactions/check` | **Kiểm tra tương tác chính** |
| GET | `/api/v1/interactions/pair?a&b` | Tra 1 cặp |
| POST | `/api/v1/drugs/normalize` | Chuẩn hóa danh sách thuốc |
| GET | `/api/v1/drugs/search?q&limit` | Tìm thuốc |
| GET | `/api/v1/sources` | Nguồn dữ liệu + độ phủ (S8) |
| GET | `/api/v1/prescriptions/summary` | Tổng quan đơn |
| GET/POST | `/api/v1/prescriptions` | List + tạo đơn |
| GET | `/api/v1/prescriptions/{rx_id}` | Chi tiết đơn |
| POST | `/api/v1/prescriptions/{rx_id}/medications` | Thêm thuốc (normalize ngay) |
| POST | `/api/v1/prescriptions/{rx_id}/checks` | Chạy check cho đơn |
| GET | `/api/v1/prescriptions/{rx_id}/checks` | Lịch sử check |
| GET | `/api/v1/checks/{check_id}` | Đọc check, tái tạo findings từ snapshot |
| POST | `/api/v1/reviews` | Gửi review HITL (tự đếm `med_count` nếu thiếu) |
| GET | `/api/v1/reviews?prescription_id=&status=` | List yêu cầu dược sĩ, mới nhất trước |
| PATCH | `/api/v1/reviews/{review_id}` | Dược sĩ chuyển `Đang chờ` → `Đã phản hồi` |
| POST | `/api/v1/assistant/chat` | Assistant **rule-based, không LLM** |
| POST | `/api/v1/chat` | Chat qua agent LangGraph (503 nếu thiếu langgraph) |
| GET | `/api/v1/status` | Trạng thái agent |

Lỗi trả `HTTPException`: 404 (không tồn tại), 400 (đơn rỗng), 500 (agent lỗi), 503 (agent chưa sẵn sàng).
Đích kiến trúc: chuẩn `RFC 9457 problem+json`.

---

## 6. Data layer

19 bảng — xem `db/models/tables.py`. Ba nhóm:

| Nhóm | Bảng |
|---|---|
| **Danh mục** | `sources`, `drugs`, `aliases`, `products`, `product_ingredients` |
| **Tương tác** | `interaction_mechanisms`, `drug_interactions`, `food_interactions`, `disease_interactions`, `duplication_classes`, `ara_interactions`, `dosage_form_rules`, `pk_ddi`, `fda_labels` |
| **App** | `prescriptions`, `medications`, `checks`, `reviews` |

Ghi chú thiết kế:

- PK là `TEXT` giữ nguyên ID từ CSV → `COPY` trực tiếp được.
- Portable SQLite/Postgres: `TEXT[]` → JSON, `vector(1536)` → JSON, cosine tính ở Python.
  `pgvector` là **tuỳ chọn** — thiếu vẫn chạy exact-match.
- `drug_interactions` **không** UNIQUE: DDInter gốc có 218 cặp trùng.

---

## 7. Test & lint

```bash
make test        # pytest tests/
make lint        # ruff check src/ tests/  +  ruff check interface/backend/
make check       # lint + format + test
```

Hiện tại: **23 passed, 1 skipped** (nhóm `test_agents` skip khi thiếu `langgraph`).

| Nhóm | Phạm vi |
|---|---|
| `tests/test_api/` | Luồng check, đơn thuốc, health, agent status |
| `tests/test_tools/` | normalizer, lookup, ranker, guardrail |
| `tests/test_agents/` | Graph agent (cần `langgraph`) |

---

## 8. Quy ước bắt buộc

1. **Chỉ `repositories/` query DB.** Router/service không viết SQL trực tiếp; chỉ dùng SQLAlchemy parameter binding.
2. **`agent_adapter/` là ranh giới.** Thêm logic gọi lõi AI → đặt trong đây, không import `src.*` chỗ khác.
3. **`src/` không import ngược lại.** Không `import interface.backend` trong bất kỳ file nào của `src/`.
4. **Severity lấy từ bản ghi nguồn.** Không để LLM xếp hạng; `guardrail` rule-based, không dùng LLM.
5. **Mọi kết luận phải có citation** (`source_id` tồn tại trong DB) — thiếu thì loại bỏ, không trả.
6. **Không bao giờ trả "an toàn"** khi không có bản ghi — trả `Chưa có bản ghi trong CSDL`.
7. **`suggest` không auto-accept.** Frontend modal xác nhận, user bắt buộc chọn.
8. **Disclaimer + handoff dược sĩ** gắn mọi response, không tắt được; chặn cụm khuyên ngưng/đổi/tăng-giảm liều/kê thuốc.
9. **PII/PHI**: mask trước khi log, không đưa PII vào prompt, audit mọi lần đọc hồ sơ. Validate input: ≤50 thuốc/lượt, tên ≤200 ký tự.
10. **Test không gọi OpenAI thật** — dùng fixture `mock_llm` (`tests/conftest.py`).

---

## 9. Cần sửa khi ra production

| # | Vấn đề | Hiện tại | Cần làm |
|---|---|---|---|
| 1 | Auth | Chưa có | JWT HS256 + RBAC (`patient`/`pharmacist`/`doctor`) — **bắt buộc trước khi có PHI thật** |
| 2 | Lỗi | `HTTPException` | Chuyển `application/problem+json` (RFC 9457) |
| 3 | Router `prescriptions` | Tự viết `select()` | Đưa vào `repositories/` |
| 4 | Guardrail tầng 2 | Chỉ tầng 1 trong pipeline | Thêm response middleware re-check |
| 5 | Rate limit | `Limiter` khai báo, chưa áp | `/interactions/check` 20 req/phút/user; OCR 5 req/phút |
| 6 | Cache catalog | `_ALIASES_CACHE` không TTL | TTL hoặc Redis khi > 1 worker |
| 7 | `CORS_ORIGINS` | `.split(",")` | Production: allowlist tường minh, không `*` |
| 8 | `.dockerignore` | Chưa loại `interface/fontend/` | Loại để image backend không mang mã FE |

---

## Tài liệu liên quan

| Tài liệu | Nội dung |
|---|---|
| [`ARCHITECTURE.md`](../../ARCHITECTURE.md) | Kiến trúc toàn hệ thống, guardrail, data flow |
| [`docs/BE_DEVELOPMENT.md`](../../docs/BE_DEVELOPMENT.md) | Kế hoạch phát triển backend theo tuần |
| [`docs/architecture/frontend.md`](../../docs/architecture/frontend.md) | Thiết kế frontend 8 màn hình |
| [`Topic.md`](../../Topic.md) | Đặc tả gốc |
