# CLAUDE.md

Tài liệu lưu vết dự án, tổng hợp từ lịch sử git (17 commit, 2026-09-10 → 2026-09-29) và các thay đổi chưa commit tính đến 2026-09-30.
Ngôn ngữ làm việc và viết tài liệu của team: **tiếng Việt**.

## 1. Dự án

**P-060: AI Agent kiểm tra an toàn thuốc (tương tác thuốc–thuốc / thuốc–thực phẩm).** Xem đề bài trong [Topic.md](Topic.md).

- Người dùng nhập danh sách thuốc đang dùng (gồm OTC và thực phẩm chức năng). Agent chạy chuỗi `normalize → lookup → rank → explain → guardrail`.
- Kết quả là **cảnh báo tham khảo có nguồn**. AI **không** tự khuyên ngưng, đổi hoặc kê thuốc, và **không** chẩn đoán.
- Mọi kết luận phải bám CSDL tương tác có trích dẫn. "Không có bản ghi" không có nghĩa là "an toàn".
- Stack: LangGraph, FastAPI, Next.js, Postgres, vector DB. Kiến trúc đích nằm ở [ARCHITECTURE.md](ARCHITECTURE.md) và [docs/architecture/frontend.md](docs/architecture/frontend.md).
- Dự án được khởi tạo từ template AI20K Agent (VinUni AI20K Build Phase, cohort 4).

### Phạm vi hiện tại: MVP

- Làm bản thử nghiệm trước. **Chưa cần kiểm tra số đăng ký (SĐK)** của thuốc.
- Nguồn dữ liệu: DDInter 2.0 (CC BY-NC-SA), bảng ARA của Patel 2020 (CC BY-NC), PK-DDIP (không nêu giấy phép), nhãn openFDA. Giấy phép phi thương mại cần xử lý trước khi ra mắt thương mại.
- Thư mục `data/` bị `.gitignore` loại hoàn toàn, nên các script pipeline chưa được version. Muốn đưa vào git thì phải thêm ngoại lệ như `!data/*.py` (hỏi team trước khi sửa `.gitignore`).

## 2. Lệnh thường dùng

```bash
make run        # uvicorn src.main:app --reload (cổng 8000)
make test       # pytest tests/ -v
make lint       # ruff check src/ tests/
make check      # lint + format + test

python eval/run_eval.py --oracle                               # tự kiểm tra harness đánh giá
python eval/run_eval.py --pred eval/results/predictions.jsonl  # chấm agent, không cần API key
pip install -r eval/requirements-eval.txt
python eval/run_eval.py --pred ... --ragas --judge llm         # thêm Ragas và rubric judge
```

Frontend: `interface/fontend/` (Next.js, tên thư mục viết sai chính tả là `fontend`, giữ nguyên). Dùng `pnpm` hoặc `npm`.

## 3. Cấu trúc thư mục

| Đường dẫn | Nội dung | Trạng thái |
|---|---|---|
| `src/` | Backend FastAPI và LangGraph (`agents/`, `api/`, `services/`, `models/`) | Còn là code mẫu của template, chưa có logic DDI |
| `interface/fontend/` | Giao diện Next.js, có chế độ sáng/tối | Bản UI đầu tiên |
| `data/` | Pipeline crawl, làm sạch và dựng CSDL, đầu ra `data/mvp/*.csv` | Có trên máy, **không** nằm trong git |
| `eval/` | Bộ đánh giá agent (metric, golden set, Ragas, judge) | Chưa commit |
| `tests/` | `test_agents/`, `test_api/`, `test_eval/` | `test_eval/` chưa commit |
| `docs/` | Guidebook 10 chương, kiến trúc, tài liệu Gate 1 (docx) | Đã commit |
| `scripts/`, `.claude/`, `.cursor/`, `.codex/`, `.gemini/`, `.agents/`, `.github/hooks/`, `.opencode/` | Hook ghi log sử dụng AI, gửi lên grading server mỗi lần `git push` | Đã commit |
| `JOURNAL.md`, `WORKLOG.md` | Nhật ký tuần và nhật ký ngày | **Vẫn là mẫu trống**, chưa điền |

## 4. Lịch sử thay đổi theo commit

Commit đã có trên `main` (mới nhất ở trên).

### 2026-09-29 (nvchien190)

| Commit | Nội dung |
|---|---|
| `e10459e` update fontend, light mode | Sửa theme sáng/tối: rút gọn `theme/dark.css` (−38 dòng), sửa `layout.tsx`, `globals.css`, `ThemeToggle.tsx` |
| `eb1be56` first UI | Tạo frontend Next.js: `app/page.tsx`, `layout.tsx`, theme `light.css` và `dark.css`, `MedicationAssistantWidget`, `ThemeToggle`, component `ui/button` (shadcn), cấu hình Tailwind/PostCSS/TS. Sửa `docs/guide/chapter-06.md`. Có lockfile của cả npm và pnpm |
| `b8248f8` test | Viết lại hook `.opencode/plugin/ai-log.ts` và xoá `.opencode/plugins/ai-log.js` |
| `ef13395` del | Xoá thư mục `GATE 1 Submission/` (README và PDF brief/PRD/wireframe) |
| `124dedb` Merge `main` vào `Chien` | Gộp nhánh |
| `ca40a56` architecture | Viết lại [ARCHITECTURE.md](ARCHITECTURE.md) (815 dòng: kiến trúc, agent, guardrail, ERD, API, auth, bảo mật, testing, deploy, design decisions, lộ trình). Thêm `docs/architecture/frontend.md`, `docs/gate_01/{Brief,PRD,Wireframe_UIFlow}.docx`, `.dockerignore`, cập nhật `.gitignore` |

### 2026-09-25 (Nguyễn Cảnh Duy)

| Commit | Nội dung |
|---|---|
| `fb84d21` Organize Gate 1 submission folder | Gom brief, PDF vào `GATE 1 Submission/` kèm README |
| `de8b8d0` Brief, prd, wireframe | Thêm `Topic.md` và PDF brief/PRD/wireframe |

### 2026-09-16 → 2026-09-19

| Commit | Nội dung |
|---|---|
| `1cd89b9` Merge (hawey2) | Gộp nhánh remote |
| `25f8edc` Create ai-log.js | Thêm plugin ghi log AI cho opencode |
| `2268841` Initial commit (nnhicey3AM) | Sửa `.env.example`, thêm `GATE 1 Submission/brief.md` |
| `ae4b996`, `adc99c5` | Thêm hook `ai-log` cho opencode và rule `.agents/rules/ai-log-hook.md`, sửa `README.md`, `JOURNAL.md` |
| `889d308` Stop AI log hooks depending on a bash that Windows may not have | Bỏ phụ thuộc bash trên Windows: thêm `scripts/_ailog_paths.py`, sửa `_pyrun.cmd/.sh` và cấu hình hook của Claude, Codex, Cursor, Gemini, GitHub |
| `5fe823f` Fix pre-push hook invoking WSL bash instead of Git Bash | Sửa hook pre-push gọi nhầm bash của WSL |
| `91d9098` Fix Python detection in `_pyrun.sh` | Bỏ qua stub Python của Windows Store |

### 2026-09-10

| Commit | Nội dung |
|---|---|
| `4c0c977` Initial commit (phoenix-mentor[bot]) | Template AI20K Agent: `src/` mẫu, Docker, CI, Makefile, `requirements.txt`, `ruff.toml`, guidebook 10 chương, checklist deliverable, hook ghi log AI cho 6 công cụ |

## 5. Thay đổi chưa commit (working tree, 2026-09-30)

### Bộ đánh giá `eval/`: mới, chưa commit

- `eval/README.md`: định nghĩa metric, ngưỡng đạt và nguồn benchmark (Marcath 2018, Patel & Beckett 2016, Suriyapakorn 2019...). Ngưỡng neo theo Lexicomp: độ nhạy ≥ 0,96, độ đặc hiệu ≥ 0,84, PPV ≥ 0,97, NPV ≥ 0,83.
- `eval/golden/build_golden.py` dựng golden set 48 ca từ `data/mvp/`. Đầu ra: `golden_set.jsonl` (đầu vào của eval) và `golden_set.csv` (để dược sĩ review bằng Excel).
- `eval/metrics.py`: metric tất định (độ nhạy/đặc hiệu, mức độ, trùng hoạt chất, guardrail, trích dẫn, PII, disclaimer).
- `eval/ragas_eval.py`: Faithfulness, FactualCorrectness, ContextRecall, ContextPrecision, ToolCallF1 (Ragas 0.4.3).
- `eval/judge.py`: chấm rubric theo schema Pydantic, có cascade JEV → LLM.
- `eval/run_eval.py`: chạy toàn bộ, so ngưỡng, ghi `eval/results/latest.md` và `run_<thời điểm>.json`.
- `eval/requirements-eval.txt`.
- `tests/test_eval/test_metrics.py`: 13 test cho metric, không gọi API (LLM và JEV được giả lập).

### File đã sửa

- `.env.example`: thêm mục Evaluation, gồm `MODEL_JUDGE` và `TYPESAFE_API_KEY` (chỉ cần cho `--judge cascade`).
- `eval/results/report.md`: thay bảng 4 metric mẫu bằng bảng theo nhóm (phát hiện tương tác, chuẩn hóa tên, an toàn, trích dẫn, Ragas, LLM-as-a-judge, vận hành). Cột Actual còn trống (⏳).

### Kết quả chạy `--oracle` mới nhất (`eval/results/latest.md`)

- 17 trên 18 metric tất định đạt. Riêng `latency_p95_ms` chưa đo vì chưa có agent thật.
- **Còn 1 metric fail:** `advice_free_rate` = 0,979 (ngưỡng 1,0). Ca `GS-020` (dosage_form) có câu chứa cụm "đổi sang" bị regex bắt là lời khuyên đổi thuốc. Cần xem đây là lỗi của regex hay của dữ liệu golden.

## 6. Việc còn dang dở

1. Commit bộ `eval/` và `tests/test_eval/`. Nhớ tách `latest.md` và `run_*.json` (kết quả sinh ra) khỏi mã nguồn nếu không muốn version chúng.
2. Xử lý ca `GS-020` để `advice_free_rate` đạt 100%.
3. Cài logic thật cho `src/` (normalizer, lookup, ranker, explainer, guardrail). Hiện vẫn là code mẫu của template.
4. Nối frontend `interface/fontend/` với API backend.
5. Điền `JOURNAL.md` và `WORKLOG.md`.
6. Quyết định có đưa `data/*.py` vào git không, và rà giấy phép dữ liệu phi thương mại.
7. Sau khi agent chạy được: sinh `predictions.jsonl`, chạy `--ragas --judge llm`, điền cột Actual trong `eval/results/report.md`.
