# Gate 1 — Rà Thuốc: AI Agent tra cứu tương tác thuốc và cảnh báo an toàn dùng thuốc

**Đội:** P-060 · AI20K Build Phase – Cohort 4

Bệnh nhân dùng nhiều thuốc (đa bệnh, đơn từ nhiều nơi, thực phẩm chức năng) dễ gặp tương tác nguy hiểm.
Rà Thuốc là AI Agent chuẩn hóa tên thuốc → tra tương tác → xếp mức độ → giải thích có nguồn,
luôn có dược sĩ/bác sĩ xác nhận (HITL) và không bao giờ tự khuyên ngừng/đổi/kê thuốc.

## Deliverables

| # | Deliverable | Vị trí |
|---|---|---|
| 1 | **Brief** | [rathuoc-brief-prd-wireframe.pdf](rathuoc-brief-prd-wireframe.pdf) — Phần A (trang 1–2) |
| 2 | **PRD** | [rathuoc-brief-prd-wireframe.pdf](rathuoc-brief-prd-wireframe.pdf) — Phần B (trang 3–5) |
| 3 | **Wireframe / UI Flow** | [rathuoc-brief-prd-wireframe.pdf](rathuoc-brief-prd-wireframe.pdf) — Phần C (trang 6–8) · Prototype clickable: <https://claude.ai/artifact/Uf8NrEQUEeMLLffbpSU921> |
| 4 | **GitHub Repo Setup + AI Log** | Repo này. Hook ghi log AI được cài sẵn (xem mục bên dưới) |

## Tóm tắt nội dung

- **Brief:** thực trạng, vấn đề, ràng buộc an toàn (HITL, grounded, chống bịa, bảo mật PII/PHI), người dùng, phạm vi, stack, nguồn dữ liệu, tiêu chí thành công, rủi ro.
- **PRD:** 3 persona, 16 user stories (P0 = MVP, P1 = nâng cao), luật nghiệp vụ & acceptance criteria, thiết kế agent LangGraph + 4 tools, kiến trúc & dữ liệu, yêu cầu phi chức năng, chỉ số đánh giá, lộ trình, câu hỏi mở.
- **Wireframe / UI Flow:** sơ đồ luồng người dùng, bản đồ 8 màn hình (S1–S8) cho 2 vai trò bệnh nhân và dược sĩ, wireframe từng màn hình, quy ước giao diện theo mức độ cảnh báo.

## Repo setup & AI Log

- Cấu trúc dự án theo template AI20K: `src/` (agents, api, services, models), `tests/`, `docs/`, Docker, CI GitHub Actions (`.github/workflows/ci.yml`).
- **AI usage logging:** hook cho Claude Code, Cursor, Codex, Gemini, Copilot, Antigravity, opencode ghi mọi prompt vào `.ai-log/session.jsonl`;
  hook `pre-push` tự động gửi log lên grading server mỗi lần `git push`. Cấu hình: [`.claude/settings.json`](../.claude/settings.json),
  [`.cursor/hooks.json`](../.cursor/hooks.json), [`scripts/`](../scripts/). Hướng dẫn cài đặt: [README gốc](../README.md#ai-usage-logging).
