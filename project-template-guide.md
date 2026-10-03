# Khởi tạo dự án từ Template

## Nhận repo của đội — Bắt đầu từ nền tảng đúng

Một trong những sai lầm phổ biến nhất của sinh viên khi bắt đầu dự án mới là tạo mọi thứ từ con số không — tự setup cấu trúc thư mục, tự cấu hình linting, tự viết CI/CD file, tự tạo Dockerfile. Kết quả là mỗi đội có một cấu trúc khác nhau, thiếu những file quan trọng, và mất hàng ngày chỉ để setup thay vì viết logic chính. Template dự án giải quyết vấn đề này bằng cách cung cấp một nền tảng đã được chuẩn hóa, bao gồm tất cả best practices mà bạn cần.

Trong AI20K bạn không phải tự clone template rồi tự tạo repository. Khi đội của bạn được chốt, hệ thống sinh sẵn một repo riêng cho đội từ chính template này — nằm trong org GitHub của khoá bạn đang học, đặt tên theo mã đội. Việc của bạn là clone nó về và bắt đầu code.

### Trước khi clone, kiểm tra hai điều

- Bạn đã vào org GitHub của khoá.
- BTC gửi lời mời tới tài khoản GitHub bạn đã đăng ký; lời mời chưa được chấp nhận thì lệnh clone sẽ báo lỗi 404 (GitHub trả 404 chứ không phải 403 cho repo private mà bạn chưa có quyền). Kiểm tra tại github.com/settings/organizations.
- Repo của đội đã được tạo. Link repo hiện ở trang đội trên Phoenix, đồng thời có một tin nhắn báo trong kênh feed GitHub trên Discord ngay khi repo được sinh ra.

Nếu chưa thấy repo của đội, đừng tự tạo repo mới — hãy báo BTC. Repo do đội tự tạo nằm ngoài org nên không bắn webhook về hệ thống chấm, và không được tính là bài nộp.

## Clone repo của đội

Mở terminal và chạy các lệnh sau:

```bash
# Thay <ORG-CỦA-KHOÁ>/<MÃ-ĐỘI> bằng URL thật — copy ở trang đội trên Phoenix
$ git clone https://github.com/<ORG-CỦA-KHOÁ>/<MÃ-ĐỘI>.git

# Di chuyển vào thư mục dự án
$ cd <MÃ-ĐỘI>

# Xác nhận remote trỏ đúng repo của đội, không phải template
$ git remote -v
```

Bạn không cần `rm -rf .git`, không cần `git init`, cũng không cần `git remote add`. Repo của đội được sinh bằng cơ chế generate của GitHub chứ không phải fork hay clone thủ công: nó bắt đầu bằng đúng một commit khởi tạo, lịch sử commit của template không đi theo. Thứ mà bước `rm -rf .git` ngày trước dùng để dọn dẹp thì nay không tồn tại.

Ngược lại, xoá `.git` lúc này là tự phá dự án của mình: mất remote trỏ về GitHub, mất luôn branch `main` đang được bảo vệ, và lần push sau đó không còn chỗ để đẩy lên.

## Cấu trúc thư mục và ý nghĩa

Sau khi clone, hãy mở thư mục dự án trong editor (khuyến nghị VS Code). Bạn sẽ thấy cấu trúc như sau:

```text
<MÃ-ĐỘI>/
├── src/
│   ├── agent/           # LangGraph Agent logic
│   │   ├── __init__.py
│   │   ├── graph.py     # State graph definition
│   │   ├── state.py     # State schema
│   │   ├── nodes.py     # Node functions
│   │   └── tools.py     # Agent tools
│   ├── api/             # FastAPI endpoints
│   │   ├── __init__.py
│   │   ├── main.py      # FastAPI app entry point
│   │   ├── routes/      # API route modules
│   │   └── deps.py      # Dependencies injection
│   ├── core/            # Shared config & utilities
│   │   ├── __init__.py
│   │   ├── config.py    # Pydantic settings
│   │   └── logging.py   # Logging setup
│   └── models/          # Data models (Pydantic)
│       ├── __init__.py
│       └── schemas.py   # Request/Response schemas
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── eval/            # Agent evaluation tests
├── docs/
│   ├── architecture/    # Architecture diagrams
│   ├── api/             # API documentation
│   └── adr/             # Architecture Decision Records
├── eval/                # Evaluation datasets & scripts
│   ├── datasets/        # Test questions & expected outputs
│   └── scripts/         # Evaluation runner scripts
├── presentation/        # Demo Day slides & materials
├── .env.example         # Mẫu biến môi trường
├── .gitignore           # Git ignore rules
├── Dockerfile           # Container definition
├── docker-compose.yml   # Multi-container orchestration
├── requirements.txt     # Danh sách dependencies
├── ruff.toml            # Cấu hình linter/formatter
├── Makefile             # Common commands shortcut
└── README.md            # Project documentation
```

Mỗi thư mục phục vụ một mục đích cụ thể. Hãy hiểu rõ trước khi bắt đầu code:

- `src/agent/` — Nơi chứa toàn bộ logic AI Agent của bạn. File `graph.py` định nghĩa state graph (sơ đồ trạng thái) cho Agent, `state.py` chứa schema dữ liệu truyền giữa các node, `nodes.py` chứa các hàm xử lý logic tại mỗi bước, và `tools.py` chứa các công cụ mà Agent có thể sử dụng.
- `src/api/` — FastAPI backend.
- `src/core/` — Cấu hình và tiện ích dùng chung.
- `src/models/` — Pydantic models cho request và response.
- `tests/` — Bài kiểm thử.
- `docs/` — Tài liệu dự án.
- `eval/` — Dữ liệu và script để đánh giá Agent.
- `presentation/` — Slide và tài liệu cho Demo Day.

### ĐIỂM CHÍNH

Cấu trúc thư mục không phải ngẫu nhiên — nó phản ánh nguyên tắc separation of concerns (tách biệt trách nhiệm). Agent logic tách biệt khỏi API logic, tách biệt khỏi config, tách biệt khỏi tests. Khi dự án lớn lên, bạn sẽ thấy cấu trúc này giúp bạn tìm và sửa code nhanh hơn rất nhiều so với “bỏ tất cả vào một file.”

## Chọn tầng khởi đầu: Prototype nhanh hay build nghiêm túc?

### Tầng 1 — Prototype ngày 1 (validate idea)

### Tầng 2 — Repo của đội (chapter này)

| Khi nào | Mục tiêu | Bỏ gì | Không bỏ gì | Quy tắc |
|---|---|---|---|---|
| Tuần 1-2, chưa chắc user cần gì | Trả lời “user có dùng không?” trong 48 giờ | DevOps, tests, guardrails | Không bỏ gì được nữa | Chuẩn bị “hoàn thành hơn hoàn hảo” |
| Đã có USP + ≥5 feedback khẳng định | Trả lời “sản phẩm chịu được Demo Day không?” trong 6 tuần | - | - | - |

Tầng 1 có thể vứt đi 100% — và đó là thắng, không phải lỗ. Khi chuyển lên tầng 2, mang theo đúng 2 thứ từ tầng 1: câu hỏi user thật (→ golden dataset Chương 10) + USP đã validate (Chương 5).

## 100% Nhận repo trên Phoenix

- Clone repo đội
- Tạo venv Python 3.12
- Cập nhật requirements.txt
- Cấu hình `.env`: API key + cascade model
- Setup AI logging hooks
- `make run`: server + Swagger UI
- Branch `develop` + commit đầu

## Thiết lập môi trường — Đừng để “trên máy tôi chạy được”

### Yêu cầu hệ thống

- Python 3.12 hoặc mới hơn
- `pip` phiên bản mới nhất
- Git 2.30+
- Docker Desktop (tùy chọn)

### Kiểm tra phiên bản Python

```bash
$ python3 --version
# Output mong đợi: Python 3.12.x hoặc cao hơn

# Nếu bạn có nhiều phiên bản Python, kiểm tra chính xác:
$ python3.12 --version
```

## Tạo virtual environment

```bash
# Từ thư mục gốc của dự án
$ python3.12 -m venv .venv

# Kích hoạt venv trên macOS/Linux
$ source .venv/bin/activate

# Kích hoạt venv trên Windows
$ .venv\Scripts\activate

# Xác nhận đang dùng Python trong venv
$ which python
# Output nên là: /path/to/your/project/.venv/bin/python
```

Sau khi kích hoạt, bạn sẽ thấy tên venv hiển thị ở đầu command prompt, ví dụ: `(.venv) $`.

### Cài đặt dependencies

```bash
$ pip install -r requirements.txt
```

Template khai báo dependencies trong `requirements.txt` — cả thư viện chạy thật lẫn thư viện dùng để test và lint đều nằm trong một file, cài bằng một lệnh.

### Xác nhận cài đặt thành công

```bash
# Kiểm tra FastAPI đã cài
$ python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
# Output: FastAPI 0.x.x

# Kiểm tra LangGraph đã cài
$ python -c "import langgraph; print('LangGraph OK')"

# Chạy tests để xác nhận template hoạt động
$ make test
# Hoặc:
$ pytest tests/ -v
```

Nếu tất cả các lệnh trên chạy mà không có error, chúc mừng — môi trường của bạn đã sẵn sàng.

> Mẹo: Nếu bạn gặp lỗi “Module not found” dù đã cài, nguyên nhân phổ biến nhất là bạn quên kích hoạt venv hoặc cài nhầm vào system Python.

## Biến môi trường — Không bao giờ hardcode secrets

Một lỗi phổ biến và nguy hiểm mà nhiều sinh viên mắc phải là “hardcode” (nhúng trực tiếp) các giá trị nhạy cảm như API keys, database passwords vào trong source code.

### File `.env.example`

Template cung cấp sẵn file `.env.example` — đây là “mẫu” liệt kê tất cả biến môi trường cần thiết mà không chứa giá trị thực. Bước đầu tiên của bạn là copy nó thành `.env` và điền giá trị:

```bash
$ cp .env.example .env
```

Nội dung file `.env.example` mẫu:

```env
# Application
APP_NAME=ai-agent
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# API
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
MODEL_CLASSIFY=gpt-4o-mini
MODEL_GENERATE=gpt-4o
MODEL_JUDGE=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2048
AGENT_MAX_ITERATIONS=8

# Database
DATABASE_URL=sqlite:///./data/app.db

# Vector Store
VECTOR_STORE_TYPE=chroma
CHROMA_PERSIST_DIR=./data/chroma
```

Sau khi copy, mở file `.env` và thay thế các giá trị placeholder bằng giá trị thực của bạn.

### Config module với `pydantic-settings`

```python
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "ai-agent"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1024, le=65535)
    api_prefix: str = "/api/v1"

    llm_provider: Literal["openai", "anthropic", "google"] = "openai"
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    openai_max_tokens: int = Field(default=2048, ge=1, le=128000)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
```

### Phân tích từng phần quan trọng

- `Literal` types giúp giới hạn giá trị cho phép.
- `Field` validators áp dụng validation trên port, temperature, tokens.
- `model_config` đọc từ file `.env` với mapping case-insensitive.
- `settings = Settings()` tạo instance duy nhất để dùng toàn ứng dụng.

## Git workflow — Làm việc nhóm không hỗn loạn

### Chiến lược branching

```bash
# Bắt đầu tính năng mới
$ git checkout develop
$ git pull origin develop
$ git checkout -b feature/agent-search-tool

# Làm việc, commit thường xuyên
$ git add src/agent/tools/search.py
$ git commit -m "feat(agent): thêm tool tìm kiếm web"

# Push và tạo Pull Request
$ git push origin feature/agent-search-tool
```

### Định dạng commit message

```text
type(scope): mô tả ngắn gọn
```

Các type phổ biến:

- `feat` — Thêm tính năng mới
- `fix` — Sửa bug
- `docs` — Cập nhật tài liệu
- `test` — Thêm/sửa tests
- `refactor` — Tái cấu trúc code
- `chore` — Bảo trì

### Pull Request process

Mỗi PR nên:

- Có tiêu đề rõ ràng theo format commit message
- Có mô tả giải thích thay đổi, tại sao, và cách test
- Nhỏ và tập trung
- Được review bởi ít nhất 1 thành viên khác
- Pass tất cả automated checks

## Chạy server lần đầu — Hello World moment

### Khởi động server

```bash
# Đảm bảo venv đã kích hoạt
$ source .venv/bin/activate

# Chạy FastAPI server
$ uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Swagger UI

Mở trình duyệt và truy cập:

```text
http://localhost:8000/docs
```

### Health check endpoint

```bash
$ curl http://localhost:8000/api/v1/health
```

Response mong đợi:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```

## Dùng Makefile cho lệnh thường dùng

```bash
$ make run          # Chạy server
$ make test         # Chạy tất cả tests
$ make lint         # Chạy linter (ruff)
$ make format       # Format code (ruff format)
$ make typecheck    # Chạy type checker (mypy)
$ make check        # Chạy tất cả checks (lint + format + typecheck + test)
```

## Bắt đầu project của bạn — Từ template thành sản phẩm

### Những gì cần thay đổi ngay

1. Rà lại `requirements.txt`
2. Cập nhật `README.md`
3. Cập nhật `.env` với API key thực

### Những gì cần giữ nguyên

- Cấu trúc thư mục
- Git workflow
- CI/CD configuration
- Testing setup
- Linting configuration

### Kế hoạch hành động cho tuần đầu tiên

Sau khi hoàn thành tất cả các bước trong chương này, bạn nên có:

- Repo của đội đã clone về máy, `git remote -v` trỏ đúng org của khoá.
- Môi trường ảo đã setup, tất cả dependencies đã cài.
- File `.env` đã cấu hình với API key.
- Server chạy được trên localhost, Swagger UI accessible.
- `README` đã cập nhật với thông tin đội.
- Branch `develop` đã tạo, ít nhất 1 commit trên `develop`.
- AI Logging Hooks đã cài đặt.

## Cài đặt AI Usage Logging Hooks

Template tích hợp sẵn hệ thống auto-logging — ghi lại mọi prompt và tool call khi bạn dùng AI coding tools.

### Chạy setup (bắt buộc — 1 lần duy nhất)

```bash
# Linux / macOS / Git Bash
bash scripts/setup_hooks.sh

# Windows PowerShell
# powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

Lệnh này cài git pre-push hook và tạo thư mục `.ai-log/`.

### 6 AI tools được hỗ trợ tự động

- Claude Code
- Cursor
- OpenAI Codex CLI
- Gemini CLI
- GitHub Copilot
- Antigravity IDE

### Cách hoạt động

Bạn dùng AI tool → Hook tự động capture prompt + metadata → Append vào `.ai-log/session.jsonl` → `git push` → pre-push hook submit lên grading server

### Log thủ công cho web tools

```bash
bash scripts/_pyrun.sh scripts/log_manual.py

# One-line
bash scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "Brainstorm UI layout"
bash scripts/_pyrun.sh scripts/log_manual.py --tool gemini-web --prompt "Research scoring algorithms"
```

### Cấu hình `.env`

```env
AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
AI_LOG_API_KEY=<giáo viên sẽ cung cấp>
AI_LOG_DIR=.ai-log
```

> ⚠️ Quan trọng: Đừng sửa hoặc xoá file trong `.ai-log/`. Đừng chạy `git push --no-verify` để bypass hook.

## Tóm tắt

Chương này hướng dẫn bạn khởi tạo dự án từ template — bước đầu tiên và quan trọng nhất. Chúng ta đã đi qua việc clone repository, hiểu cấu trúc thư mục, thiết lập môi trường ảo, cài đặt dependencies, và chạy server lần đầu tiên.

Bạn cũng đã học cách quản lý biến môi trường với `pydantic-settings`, thiết lập Git workflow với branching strategy và commit message convention, và hiểu được những gì cần tùy chỉnh so với những gì cần giữ nguyên từ template.

## Câu hỏi ôn tập

### Câu 1

Tại sao chúng ta phải xóa `.git` của template và chạy `git init` lại? Điều gì sẽ xảy ra nếu không làm bước này?

### Câu 2

Giải thích sự khác biệt giữa file `.env.example` và file `.env`. Tại sao file `.env.example` được commit lên Git nhưng file `.env` thì không? Điều gì xảy ra nếu bạn lỡ commit file `.env`?

### Câu 3

Trong cấu hình `pydantic-settings`, tại sao chúng ta dùng `Literal["development", "staging", "production"]` thay vì `str` cho field `app_env`? Lợi ích của việc này là gì trong thực tế? Hãy cho một ví dụ cụ thể về tình huống mà `Literal` type giúp phát hiện lỗi sớm.
