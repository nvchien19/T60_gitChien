# Architecture Diagram

Sơ đồ kiến trúc của Rà Thuốc (P-060), vẽ theo mã nguồn hiện có. Thiết kế chi tiết và các quyết định kiến trúc nằm ở
[ARCHITECTURE.md](../ARCHITECTURE.md); ranh giới giữa backend và lõi AI nằm ở
[interface/backend/README.md](../interface/backend/README.md).

## System Overview

```mermaid
graph TB
    User(["Bác sĩ / Dược sĩ"]) --> UI["Frontend<br/>Next.js 16 · interface/fontend"]
    UI -->|"REST /api/v1 (proxy qua Next rewrites)"| API["FastAPI<br/>interface/backend"]

    subgraph Backend["interface/backend"]
        API --> R["api/routers<br/>drugs · interactions · prescriptions · sources"]
        R --> S["services/check_service"]
        R --> AD["agent_adapter<br/>cầu nối duy nhất sang lõi AI"]
        S --> REPO["repositories/ddi_repo"]
        AD --> REPO
    end

    subgraph Core["src/ (lõi AI, không truy vấn DB)"]
        G["agents/graph<br/>LangGraph"]
        T["tools<br/>normalizer · lookup_core · ranker"]
        GR["core/guardrails"]
        EX["services/explainer + grounding"]
    end

    AD --> G
    S --> T
    S --> GR
    G --> T
    G --> GR
    EX -.->|"chỉ diễn giải bản ghi đã tra (chưa nối vào ứng dụng)"| LLM["DeepSeek<br/>deepseek-chat"]

    REPO --> PG[("PostgreSQL 16 + pgvector")]
    PIPE["data/ pipeline<br/>crawl → clean → build"] -->|"scripts/seed_mvp.py · db/load_mvp.py"| PG
    SRC["DDInter 2.0 · Patel 2020 · PK-DDIP<br/>openFDA · DAV"] --> PIPE
```

Chiều phụ thuộc chỉ đi một hướng: `interface/backend → src`. Lõi AI nhận dữ liệu đã tra sẵn (danh mục tên thuốc và
bản ghi tương tác) qua `agent_adapter`, nên chạy và test được mà không cần Database.

## Agent Flow

```mermaid
graph LR
    START((Start)) --> N["normalize<br/>chuẩn hóa tên thuốc"]
    N -->|"còn tên suggest / unknown"| C["clarify<br/>hỏi lại người dùng"]
    N -->|"lỗi đầu vào"| E["error"]
    N -->|"mọi tên đều ok"| L["lookup<br/>ghép bản ghi theo cặp"]
    L --> RK["rank<br/>xếp mức theo bản ghi"]
    RK --> X["explain<br/>giải thích kèm trích dẫn"]
    X --> GD{"guardrail"}
    GD -->|"thiếu trích dẫn, tối đa 2 lần"| X
    GD -->|"đạt"| END((End))
    C --> END
    E --> END
```

| Node | Việc làm | Có gọi LLM |
|---|---|---|
| `normalize` | Tách danh sách thuốc, tra bảng tên (`aliases`). Tên gần đúng không tự nhận | Không |
| `clarify` | Dừng lại, hỏi người dùng xác nhận tên `suggest` hoặc `unknown` | Không |
| `lookup` | Ghép bản ghi tương tác vào từng cặp; cặp không có bản ghi ghi rõ `no_record` | Không |
| `rank` | Xếp mức độ lấy thẳng từ bản ghi nguồn, hiển thị mức cao nhất | Không |
| `explain` | Viết lời giải thích tiếng Việt, gắn trích dẫn `[n]` và disclaimer | Không trong graph; `src/services/explainer.py` dùng DeepSeek cho phần "vì sao" |
| `guardrail` | Chặn kết luận không nguồn, lời khuyên đổi thuốc, câu khẳng định "an toàn" | Không |

## Data Flow

```mermaid
graph LR
    DAV["Cổng công bố thuốc DAV"] --> A["crawl_dav.py"]
    A --> B["clean_dav.py<br/>54.883 số đăng ký"]
    EXT["DDInter · openFDA<br/>Patel 2020 · PK-DDIP"] --> Cw["crawl_ddi.py"]
    B --> D["build_ddi.py<br/>nối tên, lớp 1, lớp 2"]
    Cw --> D
    D --> M["data/mvp/*.csv<br/>15 bảng"]
    M --> AU["db/audit_mvp.py<br/>kiểm tra độ sạch"]
    M --> LD["scripts/seed_mvp.py (bảng backend đọc)<br/>db/load_mvp.py (schema mvp)"]
    LD --> PG[("Postgres")]
    M --> GS["eval/golden/build_golden.py<br/>golden set 48 ca"]
    PG --> PR["eval/predict.py → run_eval.py<br/>chấm agent thật"]
```

Chi tiết từng bước và số liệu: [DATA_PIPELINE.md](DATA_PIPELINE.md).

## Component Details

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Next.js 16, React 19, Tailwind v4 | Nhập đơn, xem cảnh báo, hàng đợi xem xét |
| Backend | FastAPI, SQLAlchemy async | Kiểm tra đầu vào, điều phối nghiệp vụ, truy vấn CSDL |
| Agent | LangGraph | Điều phối normalize → lookup → rank → explain → guardrail |
| Tools | Python thuần (`src/tools`) | Chuẩn hóa tên, tra cặp, xếp mức; tái lập được, không dùng LLM |
| Guardrail | Luật (`src/core/guardrails.py`) | Bắt buộc trích dẫn, chặn lời khuyên đổi thuốc |
| LLM | DeepSeek `deepseek-chat` | Diễn giải "vì sao" từ bản ghi đã tra được (`src/services/explainer.py`); hiện chưa nối vào ứng dụng, agent giải thích bằng mẫu tất định |
| Database | PostgreSQL 16, pgvector, pg_trgm, unaccent | Dữ liệu tham chiếu và bảng nghiệp vụ (đơn, lần kiểm tra, ca xem xét) |
| Data pipeline | pandas, rapidfuzz (`data/`) | Thu thập, làm sạch, dựng 15 bảng dữ liệu |
| Evaluation | Metric tất định, Ragas, LLM-as-a-judge (`eval/`) | Chấm agent trên golden set |
