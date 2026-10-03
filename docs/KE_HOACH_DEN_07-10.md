# Kế hoạch công việc đến 12:00 thứ Tư 07/10/2026

> **Mục tiêu đợt này:** có bản chạy được từ đầu đến cuối: người dùng nhập thuốc → hệ thống tra tương tác trong CSDL → **LLM giải thích vì sao có tương tác** → giao diện hiển thị kết quả có nguồn → có số liệu đánh giá để đưa vào báo cáo và slide.
>
> **Hạn chót:** 12:00 thứ Tư 07/10/2026. Sau 12:00 không thêm tính năng, chỉ nộp.
>
> **Phân công:** Duy (dữ liệu, backend, LLM giải thích) · Chiến (frontend) · Hân (benchmark, metric, đánh giá).

---

## 1. Hiện trạng (01/10)

| Phần | Đã có | Còn thiếu |
|---|---|---|
| Dữ liệu `data/mvp/` | 15 bảng, liên kết giữa các bảng đúng 100%, khóa chính không trùng | Quá nhiều dữ liệu không dùng tới; còn hoạt chất rác, bản ghi trùng, ký tự bẩn (chi tiết ở mục 4) |
| CSDL | `db/mvp_schema.sql`, `db/load_mvp.py` (trên `main`) | Chưa nạp bản dữ liệu đã làm sạch |
| Backend `src/` | Khung template FastAPI + LangGraph | **Chưa có logic thật**: normalize, lookup, rank, explain, guardrail đều chưa có |
| LLM giải thích | Chưa có | Khảo sát cho thấy người dùng cần biết **vì sao** có tương tác, không chỉ biết là có |
| Frontend (nhánh `Chien`) | UI đầu tiên, chế độ sáng/tối, toàn bộ dùng dữ liệu giả | Chưa nối API; một số nút chưa có chức năng; luồng nghiêng về quản lý đơn thuốc thay vì kiểm tra nhanh |
| Đánh giá `eval/` | 48 ca golden, metric 3 tầng, Ragas, judge; `--oracle` đạt 18/18 | Chưa chấm agent thật; chưa có metric cho phần giải thích; cột Actual trong `report.md` còn trống |
| Tài liệu nộp | README, ARCHITECTURE | `JOURNAL.md`, `WORKLOG.md` còn trống; sơ đồ kiến trúc chưa có bước LLM giải thích; chưa có slide, video, link chạy thật |

---

## 2. Mốc chung của cả nhóm

| Mốc | Thời điểm | Điều kiện xong | Ai chịu trách nhiệm |
|---|---|---|---|
| **M0: Chốt API contract** | Thứ Sáu 02/10, 21:00 | Cả 3 người đồng ý định dạng request/response ở mục 3. Chiến dựng mock theo contract; Hân dùng cùng định dạng cho `predictions.jsonl` | Duy chủ trì, cả nhóm |
| **M1: Dữ liệu v2 + bản FE với mock** | Chủ nhật 04/10, 22:00 | Dữ liệu đã thu gọn và làm sạch, nạp được vào Postgres. FE chạy luồng mới trên mock. Hân có bộ metric cho phần giải thích | Duy, Chiến, Hân |
| **M2: Chạy được từ đầu đến cuối** | Thứ Ba 06/10, 18:00 | FE gọi API thật và ra kết quả có giải thích. Eval chấm được agent thật. **Sau mốc này ngừng thêm tính năng** | Cả nhóm |
| **M3: Nộp** | Thứ Tư 07/10, 12:00 | Code đã merge vào `main`, báo cáo eval có số thật, slide và video xong, WORKLOG/JOURNAL đã điền | Cả nhóm |

**Họp nhanh 15 phút mỗi tối lúc 21:00:** mỗi người báo đã xong gì, đang vướng gì, ngày mai làm gì. Ghi kết quả vào `WORKLOG.md`.

---

## 3. API contract (bản nháp, chốt ở M0)

Một định dạng dùng chung cho cả ba việc: backend trả về, frontend hiển thị, eval chấm điểm. Các trường bám theo `predictions.jsonl` trong `eval/README.md` mục 6, để bỏ bớt bước chuyển đổi.

**`GET /api/v1/drugs/search?q=panad`**: gợi ý tên thuốc khi người dùng gõ.

```json
[{"name": "Panadol", "drug_ids": ["DDInter14"], "ingredient": "Paracetamol", "status": "ok"}]
```

**`POST /api/v1/checks`**: kiểm tra một danh sách thuốc.

```json
// request
{"drugs": ["Panadol", "Warfarin"], "confirmed": {"augmetin": "DDInter83"}}

// response
{
  "flow": "lookup",                       // lookup | clarify (còn tên cần xác nhận) | unknown
  "normalized": [{"input": "Panadol", "status": "ok", "drug_ids": ["DDInter14"], "name_vi": "Paracetamol"}],
  "findings": [{
    "type": "interaction",                // interaction | food | disease | duplicate_active | duplicate_class
    "drug_ids": ["DDInter14", "DDInter1951"],
    "severity": "moderate",               // contraindicated | major | moderate | minor (luôn lấy từ CSDL)
    "source_id": "ddinter", "record_id": "4554", "source_url": "https://...",
    "explanation": {                      // do LLM sinh, CHỈ diễn giải, không đổi mức độ
      "why": "Vì sao xảy ra tương tác (cơ chế, viết dễ hiểu) [1]",
      "effect": "Điều có thể gặp [1]",
      "ask": "Nên hỏi bác sĩ/dược sĩ điều gì",
      "citations": [1]
    }
  }],
  "no_record": ["Thuốc X"],                // chưa có bản ghi, KHÔNG có nghĩa là an toàn
  "max_severity": "moderate",
  "disclaimer": "Kết quả chỉ là cảnh báo tham khảo ...",
  "latency_ms": 2140
}
```

> Nếu LLM chậm thì để `explanation = null` và FE gọi riêng `GET /api/v1/explanations/{record_id}`. Phần tra tương tác không được phải chờ LLM.

---

## 4. Bảng việc của Duy: dữ liệu, backend, LLM giải thích

Hướng thu gọn dữ liệu (đề xuất, Duy chốt):
- Chỉ giữ thuốc `status = valid`.
- Giữ các cặp tương tác có `both_in_vn = True`: 51.121 / 260.100 dòng, giảm khoảng 80%.
- Giữ hoạt chất đang lưu hành ở Việt Nam, hoặc có tương tác với hoạt chất đang lưu hành.
- Trong `fda_labels`, bỏ các cột văn bản dài không hiển thị. Bỏ cột gần như rỗng `phong_benh`.

| # | Đầu việc | Chi tiết / điều kiện xong | Thời hạn | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|---|
| D1 | Chốt phạm vi thu gọn dữ liệu | Viết quy tắc lọc vào `data/build_ddi.py`, ghi số dòng trước/sau vào `data/mvp/README.md` | T6 02/10, 12:00 | P0 | — |
| D2 | Sửa lỗi tách hoạt chất DAV | Loại token rác (`và`, `cứ`, `d`, `mg`, `200`, `19,0`). Sửa hàm tạo khóa đang cắt mất chữ (Tía tô → `tia`, Tô mộc → `moc`, Cao khô → `kho`, L-Lysin → `l`). Tách hàm lượng khỏi tên (`Spiramycin 1,5 M.IU`). Rà 507 khóa ngắn hoặc chứa số | T6 02/10 | P0 | D1 |
| D3 | Gộp hoạt chất bị tách nhiều bản ghi | Riboflavin (7 bản ghi), thiamin/Vitamin B1 (3), `typhoid vaccine live` (2): thêm vào bảng MANUAL trong `build_ddi.py` | T7 03/10 | P0 | D2 |
| D4 | Khử trùng tương tác | Xóa 1 cặp tự tương tác (Botulinum toxin A, id 237256). Xóa 218 dòng trùng chỉ khác `interaction_id`. 230 cặp có 2 mức độ: giữ mức cao nhất, ghi lý do. 118 dòng lệch mức với cơ chế: chọn một nguồn mức độ duy nhất. Ngoài ra: `disease_interactions` 78 dòng trùng, `pk_ddi` 12 dòng trùng, `food` 1 dòng trùng. Đánh `position` riêng cho từng thành phần của thuốc phối hợp | T7 03/10 | P0 | D1 |
| D5 | Làm sạch văn bản | Lọc ký tự điều khiển (`\x02`, `\x08`), thẻ `<NP>`, đoạn `" O 0` trong references (3.284 dòng), dấu cách đôi, dấu cách cuối tên. Chuyển 2 mã OMIM ra khỏi cột `mesh_id` | T7 03/10 | P1 | — |
| D6 | Biến kiểm tra chất lượng thành test | Chuyển các kiểm tra ở bước audit (khóa trùng, ký tự bẩn, toàn vẹn tham chiếu) thành `tests/test_data/`. Chạy được trước mỗi lần build | CN 04/10 | P1 | D2–D5 |
| D7 | Đưa script dữ liệu vào git | Cần **cả nhóm đồng ý** sửa `.gitignore` (thêm `!data/*.py`, `!data/mvp/README.md`). Không đưa CSV lớn lên git | CN 04/10 | P1 | Nhóm đồng ý |
| D8 | Nạp dữ liệu v2 vào Postgres | Cập nhật `db/mvp_schema.sql` (thêm lại các ràng buộc UNIQUE giờ đã thỏa), chạy `db/load_mvp.py`. Báo Hân chạy lại `build_golden.py` | CN 04/10, 22:00 (**M1**) | P0 | D1–D5 |
| D9 | API contract + khung API | Viết schema Pydantic theo mục 3. Có endpoint trả mock trước để Chiến dùng ngay | T6 02/10, 21:00 (**M0**) | P0 | — |
| D10 | Tool `normalize` + `lookup` + `rank` | Thay code mẫu trong `src/`: chuẩn hóa tên (`khoa()` + `aliases` + `pg_trgm`), tra lớp 1 + lớp 2, xếp theo mức cao nhất. Tên `suggest` trả `flow = clarify`, không tra trước khi người dùng xác nhận. `GET /drugs/search` cho autocomplete | T2 05/10 | P0 | D8, D9 |
| D11 | **Node LLM giải thích (`explain`)** | Đầu vào là bản ghi CSDL (mô tả cơ chế, cách xử trí, tài liệu tham khảo); đầu ra là `why` / `effect` / `ask` bằng tiếng Việt dễ hiểu, có [n]. **LLM không quyết định mức độ, không khuyên ngưng/đổi/kê thuốc, chỉ được dùng nội dung có trong bản ghi.** Prompt để ở `src/agents/prompts/`. Đề xuất: sinh sẵn giải thích theo `mechanism_id` cho các cặp `both_in_vn` rồi cache lại, giúp giảm độ trễ và chi phí, và cho phép dược sĩ duyệt trước | T3 06/10, 12:00 | P0 | D10; tiêu chí từ H2 |
| D12 | Node guardrail | Kiểm tra sau khi LLM sinh: không có câu khuyên dùng thuốc (G1), không nói "an toàn" khi không có bản ghi (G4), không lộ PII (G5), mỗi kết luận có trích dẫn. Nếu fail thì sinh lại, quá 2 lần thì trả nguyên văn bản ghi | T3 06/10 | P0 | D11 |
| D13 | Sinh `predictions.jsonl` cho 48 ca golden | Chạy agent trên `eval/golden/golden_set.jsonl`, giao cho Hân chấm. Sửa lỗi theo kết quả | T3 06/10, 15:00 | P0 | D10–D12 |
| D14 | Cập nhật sơ đồ kiến trúc | Thêm bước `explain` (LLM) và `guardrail` vào `docs/architecture_diagram.md` và ARCHITECTURE.md | T3 06/10 | P1 | — |
| D15 | Deploy / link chạy thật | Docker Compose (BE + Postgres) hoặc dịch vụ miễn phí; đủ để quay demo | T4 07/10, 10:00 | P1 | M2 |

---

## 5. Bảng việc của Chiến: frontend

**Vấn đề đang có trong `interface/fontend/app/page.tsx` (nhánh `Chien`):**
- **Nút gắn sai hoặc chưa có chức năng:**
  - Nút "Thêm đơn thuốc" ở thư viện mở modal "Thêm thuốc vào RX-…", tức là thêm thuốc chứ không phải tạo đơn.
  - Mỗi đơn trong danh sách "Đơn thuốc gần đây" ở trang Tổng quan đều dẫn về trang thư viện, không mở đúng đơn được bấm.
  - Nút "Yêu cầu dược sĩ xem" trong kết quả không có `onClick`.
  - Các nút Cài đặt, chuông thông báo, menu mobile, đính kèm tệp chưa có chức năng.
  - Số "3" trên menu "Kiểm tra an toàn" là số cố định.
- **Kết quả là dữ liệu giả cố định:** cùng 3 tương tác cho mọi đơn. Màn "Đang kiểm tra" đứng yên ở bước 4. Modal chi tiết luôn ghi nguồn "FDA Drug Labels". Trợ lý chat luôn trả cùng một câu.
- **Luồng:** nhập thuốc tự do, không gợi ý tên, không có bước xác nhận tên. Golden set đòi hỏi tên `suggest` phải hỏi lại trước khi tra.
- **Thiếu mức độ:** chỉ có 3 mức. Còn thiếu "Chống chỉ định" và trạng thái "Chưa có bản ghi" (màu xám, không được hiển thị như an toàn). Chưa có nhóm thuốc–thực phẩm, thuốc–bệnh, trùng hoạt chất.
- **Trên mobile:** thanh điều hướng dưới chỉ có 4 mục, nên không vào được "Trao đổi dược sĩ".
- **Ngôn ngữ:** còn lẫn nhãn tiếng Anh ("Prescription detail", "Saved records", "Medication Safety").
- **Mã nguồn:** toàn bộ dồn trong một file, mỗi component viết trên một dòng dài; chưa có lớp gọi API.

**Luồng đề xuất (luồng chính, ưu tiên mobile):**

```
Trang chủ: nút lớn "Kiểm tra thuốc"
  → Nhập thuốc (gợi ý tên khi gõ, thêm thành từng thẻ)
  → Xác nhận tên (ok: tick xanh | suggest: "Ý bạn là…?" | unknown: "Chưa có trong dữ liệu")
  → Kết quả: tóm tắt mức cao nhất + danh sách theo mức + nhóm "Chưa có bản ghi"
  → Chi tiết một tương tác: Vì sao? / Có thể gặp gì? / Nên hỏi bác sĩ/dược sĩ điều gì? / Nguồn
  → (tùy chọn) Lưu vào đơn thuốc | Gửi dược sĩ
```

Thư viện đơn thuốc và lịch sử chuyển thành chức năng phụ, dùng để lưu kết quả.

| # | Đầu việc | Chi tiết / điều kiện xong | Thời hạn | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|---|
| C1 | Chốt API contract cùng Duy | Đọc mục 3, góp ý những trường FE cần thêm | T6 02/10, 21:00 (**M0**) | P0 | — |
| C2 | Sửa các nút sai hoặc thiếu chức năng | Xử lý các nút trong danh sách vấn đề ở trên. Nút nào chưa làm kịp thì **ẩn đi**, không để nút bấm không phản hồi | T6 02/10 | P0 | — |
| C3 | Tách file + lớp gọi API + mock | Tách `page.tsx` thành từng component/view. Tạo `lib/api.ts` và dữ liệu mock theo contract để làm FE song song với BE. Bật/tắt mock bằng biến môi trường | T7 03/10 | P0 | C1 |
| C4 | Luồng "Kiểm tra thuốc" mới | Ô nhập có gợi ý tên (`/drugs/search`); thuốc thêm thành thẻ, xóa được; bước xác nhận tên cho `suggest`/`unknown` | T7 03/10 – CN 04/10 | P0 | C3 |
| C5 | Màn kết quả mới | Dùng 4 mức (Chống chỉ định / Nghiêm trọng / Trung bình / Nhẹ) cộng "Chưa có bản ghi" màu xám. Nhóm theo loại: thuốc–thuốc, thực phẩm, bệnh nền, trùng hoạt chất. Có thẻ tóm tắt mức cao nhất. Disclaimer luôn hiển thị, không ẩn được. Trích dẫn [n] bấm được để mở nguồn | CN 04/10 (**M1**) | P0 | C3 |
| C6 | Chi tiết tương tác có phần giải thích | 4 mục: **Vì sao xảy ra** (từ LLM) / Có thể gặp gì / Nên hỏi bác sĩ/dược sĩ điều gì / Bằng chứng (nguồn, bản gốc tiếng Anh thu gọn). Có skeleton khi giải thích đang tải, và vẫn hiển thị bản ghi gốc nếu LLM lỗi | CN 04/10 – T2 05/10 | P0 | C5, contract |
| C7 | Nối API thật | Thay mock bằng API; xử lý trạng thái đang tải / lỗi / không có kết quả / mất mạng; timeout 10 giây | T2 05/10 – T3 06/10 | P0 | D10 |
| C8 | Trợ lý chat | Nếu kịp: nối với giải thích của finding đang xem. Nếu không kịp: **ẩn trợ lý**, không để câu trả lời giả trong bản demo. Bỏ nút đính kèm | T3 06/10 | P1 | D11 |
| C9 | Mobile + khả năng tiếp cận | Kiểm tra ở chiều rộng 375px; chữ ≥ 16px; đủ tương phản; vào được mọi mục trên mobile; Việt hóa toàn bộ nhãn | T3 06/10 | P1 | — |
| C10 | Merge + demo | Mở PR từ `Chien` vào `main`. Quay video demo theo kịch bản (2–3 ca trong golden set: Panadol + Warfarin, dihydroergotamin + clarithromycin, thuốc chưa có bản ghi). Chụp màn hình cho slide | T4 07/10, 11:00 | P0 | M2 |

---

## 6. Bảng việc của Hân: benchmark, metric, đánh giá

Nền tảng đã có trong `eval/README.md`: benchmark các công cụ tra tương tác (Marcath 2018, Patel 2016, Suriyapakorn 2019, Xu 2025), benchmark LLM trả lời tương tác (Al-Ashwal 2023), HealthBench, LLM-as-a-judge, Ragas. Việc của Hân là **mở rộng sang phần giải thích (LLM mới)** và **chấm hệ thống thật**.

| # | Đầu việc | Chi tiết / điều kiện xong | Thời hạn | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|---|
| H1 | Nắm bộ đánh giá hiện có | Đọc `eval/README.md`; cài `eval/requirements-eval.txt`; chạy `python eval/run_eval.py --oracle` (phải đạt 18/18); ghi lại những chỗ chưa rõ | T6 02/10 | P0 | — |
| H2 | **Nghiên cứu metric cho phần giải thích** | Tìm benchmark/metric đánh giá giải thích y khoa cho người bệnh, gồm: bám nguồn (faithfulness), đủ ý "vì sao" (có nêu cơ chế không), dễ hiểu bằng tiếng Việt (độ dài câu, thuật ngữ không giải thích), không khuyên dùng thuốc, có trích dẫn. Mỗi metric có định nghĩa, ngưỡng, nguồn tham khảo (ghi link, chỉ dùng nguồn đã đọc). Viết thành mục mới trong `eval/README.md`. **Gửi Duy tiêu chí trước để viết prompt (D11)** | CN 04/10 (**M1**) | P0 | H1 |
| H3 | Bổ sung golden set cho phần giải thích | Thêm trường `expected_explanation_points` (các ý bắt buộc phải có trong phần "vì sao") cho khoảng 20 ca có tương tác; thêm tiêu chí rubric tương ứng. Cập nhật `eval/golden/build_golden.py` và `eval/metrics.py` | T2 05/10 | P0 | H2 |
| H4 | Baseline so sánh: LLM không có CSDL | Cho một LLM (ví dụ gpt-4o-mini) trả lời trực tiếp 48 ca, không có CSDL; chấm bằng cùng bộ metric. Mục đích là chứng minh hệ thống bám CSDL tốt hơn (Al-Ashwal 2023: ChatGPT-4 chỉ đạt độ đặc hiệu 0,39). Kết quả này dùng cho slide | T2 05/10 | P1 | H1 |
| H5 | Dựng lại golden set trên dữ liệu v2 | Sau M1, chạy lại `build_golden.py`; review các ca bị lệch mức độ do dữ liệu thay đổi; báo Duy nếu lỗi nằm ở dữ liệu | T2 05/10 | P0 | D8 |
| H6 | Khảo sát người dùng về phần giải thích | Mẫu đánh giá ngắn (thang 1–5: dễ hiểu, hữu ích, tin tưởng) cho 5–10 người dùng thử bản demo. Dùng làm số liệu "User satisfaction > 4/5" trong `report.md` | Soạn mẫu: T2 05/10; thu kết quả: T3 06/10 – T4 07/10 sáng | P1 | M2 (cần bản chạy được) |
| H7 | Chấm agent thật | Chạy trên `predictions.jsonl` của Duy: tầng A + `--ragas --judge llm` + metric giải thích mới. Phân tích lỗi theo nhóm ca; báo bug cho Duy (dữ liệu, BE) và Chiến (hiển thị) | T3 06/10, 15:00 – 20:00 | P0 | D13 |
| H8 | Báo cáo đánh giá | Điền cột Actual trong `eval/results/report.md`, gồm latency p95 và so sánh với baseline (H4). Làm 2–3 biểu đồ cho slide. Đây là deliverable 10 "Evaluation Evidence" | T4 07/10, 10:00 | P0 | H7 |
| H9 | WORKLOG / JOURNAL | Tổng hợp từ các buổi họp tối vào `WORKLOG.md` (theo ngày) và `JOURNAL.md` (theo tuần). Mỗi người tự điền dòng của mình, Hân rà lại trước khi nộp | Mỗi tối; chốt T4 07/10, 11:00 | P1 | — |

---

## 7. Lịch theo ngày (tóm tắt)

| Ngày | Duy | Chiến | Hân |
|---|---|---|---|
| **T6 02/10** | D1, D2, D9 (**M0** 21:00) | C1, C2 | H1, bắt đầu H2 |
| **T7 03/10** | D3, D4, D5 | C3, bắt đầu C4 | H2 |
| **CN 04/10** | D6, D7, D8 (**M1** 22:00) | C4, C5 (**M1**) | Xong H2 (**M1**), gửi tiêu chí cho Duy |
| **T2 05/10** | D10 | C6, bắt đầu C7 | H3, H4, H5, soạn mẫu H6 |
| **T3 06/10** | D11, D12, D13 (15:00), D14 | C7, C8, C9 (**M2** 18:00) | H7 (từ 15:00), bắt đầu thu H6 |
| **T4 07/10 (đến 12:00)** | D15, sửa lỗi | C10 (video, PR) | H8, H9, thu nốt H6 |

**Slide (deliverable 7):** mỗi người viết phần của mình trước 10:00 thứ Tư: Duy viết dữ liệu + kiến trúc + LLM, Chiến viết luồng UI + demo, Hân viết số liệu đánh giá. Hân ghép bản cuối.

---

## 8. Rủi ro và cách xử lý

| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| LLM giải thích chậm (> 10 giây) | Latency p95 cao | Sinh sẵn giải thích theo `mechanism_id` và cache (D11). FE hiển thị kết quả tra trước, giải thích tải sau |
| LLM bịa hoặc khuyên dùng thuốc | Faithfulness thấp, guardrail fail | Prompt chỉ cho dùng nội dung trong bản ghi; có guardrail (D12); quá 2 lần sinh lại thì trả nguyên văn bản ghi |
| Làm sạch dữ liệu kéo dài, chặn backend | Quá CN 04/10 vẫn chưa nạp được DB | Mục P1 (D5–D7) để sau. Backend tạm dùng dữ liệu hiện tại, chỉ áp phần lọc của D1 |
| FE chờ BE | Đến T2 vẫn chưa có API thật | FE chạy trên mock đúng contract (C3). Contract đã chốt ở M0 nên khi nối API chỉ cần đổi biến môi trường |
| Golden set lệch sau khi đổi dữ liệu | `build_golden.py` dừng vì lệch mức | H5: review từng ca; lỗi do dữ liệu thì báo Duy, lỗi do golden thì sửa golden |
| Merge nhánh bị xung đột vào phút cuối | — | Mỗi người mở PR sớm (trước M2). Không push thẳng vào `main` sau 18:00 thứ Ba |

---

## 9. Việc chưa có người nhận (nhóm quyết định ở buổi họp T6)

- Giấy phép dữ liệu: DDInter và Patel 2020 chỉ được dùng phi thương mại, còn PK-DDIP không ghi giấy phép. Cần ghi rõ giới hạn này trong README và slide.
- Dược sĩ duyệt `eval/golden/golden_set.csv` và các giải thích sinh sẵn: cần tìm người duyệt.
- Quy tắc trùng nhóm "antiarrhythmics" của DDInter (digoxin + amiodaron) đang để ở `optional_findings` trong golden set: cần dược sĩ quyết định giữ hay bỏ.
