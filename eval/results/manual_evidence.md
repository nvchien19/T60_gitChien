# Eval evidences: test case thủ công

> Bằng chứng đánh giá cho Gate 2 (MVP). Mỗi ca dưới đây được gọi tay vào hệ thống đang chạy và chép lại **output thực
> tế**. Kết quả chấm tự động trên golden set 48 ca nằm ở [report.md](report.md).

## 1. Cách chạy

- Ngày chạy: 2026-10-04. Backend `interface.backend.main:app` chạy trên máy phát triển, Postgres đã nạp dữ liệu sạch
  (5.619 hoạt chất, 259.860 bản ghi tương tác).
- Điểm gọi: `POST /api/v1/interactions/check`. Màn "Kết quả kiểm tra an toàn" của giao diện dùng cùng dịch vụ này.
  Ca TC8 dùng thêm các điểm gọi đơn thuốc và xem xét.
- Lệnh mẫu:

```bash
curl -X POST http://localhost:8000/api/v1/interactions/check \
  -H "Content-Type: application/json" \
  -d '{"drugs": ["Panadol", "Warfarin"]}'
```

- Trong các khối JSON, chuỗi dài được cắt bớt (dấu `…`) và bỏ các trường không dùng để đánh giá. Phần còn lại giữ
  nguyên như hệ thống trả về.

## 2. Tiêu chí đối chiếu

| Tiêu chí | Hệ thống hiện đáp ứng thế nào | Trường trong output |
|---|---|---|
| Độ tin cậy trên 90%, nếu không phải có cảnh báo | Ứng dụng đang chạy **không gọi LLM**: lời cảnh báo lấy nguyên từ bản ghi CSDL, nên không có điểm tin cậy của LLM. Điểm tin cậy hệ thống có là **điểm khớp tên thuốc** (0 đến 1). Luật đang áp dụng chặt hơn mức 90%: chỉ khớp chính xác (100%) mới tự áp dụng; tên khớp dưới 100% chỉ là gợi ý, kèm cảnh báo "Cần xác nhận, không tự áp dụng" và không được dùng để tra | `normalized[].status`, `suggestions[].score`, `note` |
| Cảnh báo dựa trên nguồn nào | Mỗi phát hiện mang danh sách trích dẫn có tên nguồn | `citations[].source_name` |
| Đọc từ cơ sở dữ liệu tương tác nào, mở được bản ghi | Trích dẫn thuốc - thuốc có đường dẫn tới đúng bản ghi DDInter (`/interact/<mã>/`) hoặc nhãn FDA trên DailyMed | `citations[].source_url` |
| Gợi ý xử trí | Lấy từ trường xử trí của bản ghi nguồn. Hệ thống không tự khuyên ngưng hay đổi thuốc | `management` |
| Ngày cập nhật | Ngày cập nhật theo từng nguồn, lấy ở `GET /api/v1/sources` | `items[].last_updated` |
| Bấm vào xem kết luận | Trên giao diện, bấm một phát hiện sẽ mở hộp "Chi tiết phát hiện" (phát hiện gì, nên làm gì, bằng chứng, nút "Xem nguồn"). Mỗi lần kiểm tra có mã `CHECK-…`, xem lại được ở mục Lịch sử | `GET /api/v1/checks/{check_id}` |

Ngày cập nhật các nguồn (output thực tế của `GET /api/v1/sources`):

| Nguồn | Giấy phép | Cập nhật |
|---|---|---|
| Cục Quản lý Dược - danh mục thuốc được cấp số đăng ký | Dữ liệu công khai của cơ quan nhà nước | 2026-09-30 |
| DDInter 2.0 | CC BY-NC-SA 4.0 - chỉ dùng phi thương mại | 2026-09-30 |
| Patel 2020 - tương tác với thuốc giảm acid | CC BY-NC 4.0 - chỉ dùng phi thương mại | 2020-01-01 |
| PK-DDIP (PK-DDI DB) | Không ghi giấy phép - chỉ dùng tham khảo nội bộ | 2026-09-30 |
| Nhãn thuốc FDA (openFDA drug label, DailyMed) | Dữ liệu công (https://open.fda.gov/terms/) | 2026-09-29 |
| Từ điển tên hoạt chất Việt - quốc tế của dự án | Nội bộ dự án | 2026-10-04 |

## 3. Tổng hợp

| Ca | Tình huống | Đầu vào | Kết quả |
|---|---|---|---|
| TC1 | Biệt dược + hoạt chất, tương tác mức Trung bình | Panadol, Warfarin | ✅ Đạt |
| TC2 | Cặp chống chỉ định, hai nguồn độc lập | Dihydroergotamin, Clarithromycin | ✅ Đạt |
| TC3 | Tên gõ sai chính tả (độ tin cậy 90,9%) | paracetamon, Warfarin | ✅ Đạt |
| TC4 | Cặp không có bản ghi tương tác | Piracetam, Paracetamol | ✅ Đạt |
| TC5 | Biệt dược phối hợp (ca chưa đạt) | Augmentin, Warfarin | ❌ Chưa đạt |
| TC6 | Đơn 3 thuốc, có trùng nhóm điều trị | Aspirin, Ibuprofen, Warfarin | ✅ Đạt |
| TC7 | Tên thuốc không tồn tại | Thuocxyz123, Warfarin | ✅ Đạt |
| TC8 | Luồng đơn thuốc → kiểm tra → gửi xem xét → xem lại kết luận | Aspirin, Warfarin | 🟡 Đạt một phần |

**8 ca: 6 đạt, 1 đạt một phần, 1 chưa đạt.**

## 4. Chi tiết từng ca

### TC1. Biệt dược + hoạt chất, tương tác mức Trung bình

- **Đầu vào:** `["Panadol", "Warfarin"]`
- **Mong đợi:** Nhận `Panadol` là Acetaminophen; báo cặp Acetaminophen - Warfarin mức Trung bình, có nguồn DDInter.
- **Thời gian phản hồi:** 60 ms

| Tiêu chí | Output thực tế |
|---|---|
| Độ tin cậy nhận diện tên | `Panadol` → Acetaminophen: khớp chính xác (100%), tự áp dụng<br>`Warfarin` → Warfarin: khớp chính xác (100%), tự áp dụng |
| Mức cao nhất (thuốc - thuốc) | Trung bình |
| Gợi ý xử trí | Acetaminophen + Warfarin: Due to the lack of safer alternatives, acetaminophen is considered the analgesic and antipyretic drug of choice for patients receiving warfarin and similar anticoagulants. However, caution is recommended during concomitant therapy, particularly if high dosages… |
| Disclaimer | Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay. |

| Cặp | Mức độ | Nguồn | Mở bản ghi gốc | Nguồn cập nhật |
|---|---|---|---|---|
| Acetaminophen + Warfarin | Trung bình | DDInter 2.0 | [DDInter 2.0](https://ddinter2.scbdd.com/server/interact/4554/) | 2026-09-30 |
| Acetaminophen + rượu, bia (đồ uống có cồn) (thức ăn) | Nghiêm trọng | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Warfarin + rượu, bia (đồ uống có cồn) (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Warfarin + thực phẩm giàu vitamin K (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |

<details><summary>Output JSON thực tế (rút gọn)</summary>

```json
{
 "normalized": [
  {
   "input": "Panadol",
   "status": "ok",
   "canonical_name": "Acetaminophen",
   "drug_id": "DDInter14",
   "suggestions": [],
   "note": ""
  },
  {
   "input": "Warfarin",
   "status": "ok",
   "canonical_name": "Warfarin",
   "drug_id": "DDInter1951",
   "suggestions": [],
   "note": ""
  }
 ],
 "max_severity_vi": "Trung bình",
 "findings": [
  {
   "pair": [
    "Acetaminophen",
    "Warfarin"
   ],
   "severity_vi": "Trung bình",
   "summary": "Acetaminophen (APAP) may potentiate the hypoprothrombinemic effect of warfarin and other vitamin K antagonists, although data are somewhat conflicting and the precise mec…",
   "management": "Due to the lack of safer alternatives, acetaminophen is considered the analgesic and antipyretic drug of choice for patients receiving warfarin and similar anticoagulants…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "DDInter 2.0",
     "source_url": "https://ddinter2.scbdd.com/server/interact/4554/"
    }
   ]
  }
 ],
 "food_findings": [
  {
   "pair": [
    "Acetaminophen",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Nghiêm trọng",
   "summary": "Chronic, excessive consumption of alcohol may increase the risk of acetaminophen-induced hepatotoxicity, which has included rare cases of fatal hepatitis and frank hepati…",
   "management": "In general, chronic alcoholics should avoid regular or excessive use of acetaminophen. Alternative analgesic/antipyretic therapy may be appropriate in patients who consum…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Warfarin",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Trung bình",
   "summary": "Enhanced hypoprothrombinemic response to warfarin has been reported in patients with acute alcohol intoxication and/or liver disease. The proposed mechanisms are inhibiti…",
   "management": "Patients taking oral anticoagulants should be counseled to avoid large amounts of ethanol, but moderate consumption (one to two drinks per day) are not likely to affect t…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Warfarin",
    "thực phẩm giàu vitamin K"
   ],
   "severity_vi": "Trung bình",
   "summary": "Vitamin K may antagonize the hypoprothrombinemic effect of oral anticoagulants. Vitamin K is a cofactor in the synthesis of blood clotting factors that are inhibited by o…",
   "management": "Intake of vitamin K through supplements or diet should not vary significantly during oral anticoagulant therapy. The diet in general should remain consistent, as other fo…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  }
 ],
 "duplicate_findings": [],
 "no_record_pairs": [],
 "disclaimer": "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay."
}
```

</details>

**Kết quả: ✅ Đạt.** Đúng hoạt chất, đúng mức độ theo bản ghi DDInter số 4554, có đường dẫn mở bản ghi gốc và disclaimer.

### TC2. Cặp chống chỉ định, hai nguồn độc lập

- **Đầu vào:** `["Dihydroergotamin", "Clarithromycin"]`
- **Mong đợi:** Báo mức Chống chỉ định, trích cả DDInter và nhãn FDA.
- **Thời gian phản hồi:** 52 ms

| Tiêu chí | Output thực tế |
|---|---|
| Độ tin cậy nhận diện tên | `Dihydroergotamin` → Dihydroergotamine: khớp chính xác (100%), tự áp dụng<br>`Clarithromycin` → Clarithromycin: khớp chính xác (100%), tự áp dụng |
| Mức cao nhất (thuốc - thuốc) | Chống chỉ định |
| Gợi ý xử trí | Clarithromycin + Dihydroergotamine: Chống chỉ định với MỌI dạng dihydroergotamin (tiêm, xịt mũi, bột xịt mũi). Đổi đường dùng không làm phối hợp này an toàn hơn. |
| Disclaimer | Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay. |

| Cặp | Mức độ | Nguồn | Mở bản ghi gốc | Nguồn cập nhật |
|---|---|---|---|---|
| Clarithromycin + Dihydroergotamine | Chống chỉ định | DDInter 2.0, FDA Labels | [DDInter 2.0](https://ddinter2.scbdd.com/server/interact/67745/), [FDA Labels](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=b464a64d-b150-4f6b-b3df-e486a41294d7) | 2026-09-30, 2026-09-29 |
| Clarithromycin + nước bưởi chùm (grapefruit) (thức ăn) | Nhẹ | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Dihydroergotamine + nước bưởi chùm (grapefruit) (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |

<details><summary>Output JSON thực tế (rút gọn)</summary>

```json
{
 "normalized": [
  {
   "input": "Dihydroergotamin",
   "status": "ok",
   "canonical_name": "Dihydroergotamine",
   "drug_id": "DDInter557",
   "suggestions": [],
   "note": ""
  },
  {
   "input": "Clarithromycin",
   "status": "ok",
   "canonical_name": "Clarithromycin",
   "drug_id": "DDInter393",
   "suggestions": [],
   "note": ""
  }
 ],
 "max_severity_vi": "Chống chỉ định",
 "findings": [
  {
   "pair": [
    "Clarithromycin",
    "Dihydroergotamine"
   ],
   "severity_vi": "Chống chỉ định",
   "summary": "Chất ức chế mạnh CYP3A4 làm tăng nồng độ dihydroergotamin, gây co mạch dẫn tới thiếu máu cục bộ ngoại biên/não nghiêm trọng, đe dọa tính mạng (cảnh báo đóng khung).",
   "management": "Chống chỉ định với MỌI dạng dihydroergotamin (tiêm, xịt mũi, bột xịt mũi). Đổi đường dùng không làm phối hợp này an toàn hơn.",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "DDInter 2.0",
     "source_url": "https://ddinter2.scbdd.com/server/interact/67745/"
    },
    {
     "source_name": "FDA Labels",
     "label": "Nhãn FDA dihydroergotamin tiêm và xịt mũi (Trudhesa): cảnh báo đóng khung; Kiem_…",
     "source_url": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=b464a64d-b150-4f6b-b3df-e486a41294d7"
    }
   ]
  }
 ],
 "food_findings": [
  {
   "pair": [
    "Clarithromycin",
    "nước bưởi chùm (grapefruit)"
   ],
   "severity_vi": "Nhẹ",
   "summary": "Grapefruit juice may delay the gastrointestinal absorption of clarithromycin but does not appear to affect the overall extent of absorption or inhibit the metabolism of c…",
   "management": "Concomitant use of Clarithromycin with grapefruit or grapefruit juice should generally be avoided.",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Dihydroergotamine",
    "nước bưởi chùm (grapefruit)"
   ],
   "severity_vi": "Trung bình",
   "summary": "Grapefruit juice may increase the plasma concentrations of orally administered drugs that are substrates of the CYP450 3A4 isoenzyme. The proposed mechanism is inhibition…",
   "management": "Patients who regularly consume grapefruit or grapefruit juice should be monitored for adverse effects and altered plasma concentrations of drugs that undergo significant…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  }
 ],
 "duplicate_findings": [],
 "no_record_pairs": [],
 "disclaimer": "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay."
}
```

</details>

**Kết quả: ✅ Đạt.** Mức cao nhất được hiển thị; hai trích dẫn đều có đường dẫn. Lời xử trí lấy từ quy tắc dạng bào chế của dự án, viết bằng tiếng Việt.

### TC3. Tên gõ sai chính tả (độ tin cậy 90,9%)

- **Đầu vào:** `["paracetamon", "Warfarin"]`
- **Mong đợi:** Không tự nhận `paracetamon` là paracetamol; hỏi lại người dùng; không báo "an toàn".
- **Thời gian phản hồi:** 76 ms

| Tiêu chí | Output thực tế |
|---|---|
| Độ tin cậy nhận diện tên | `paracetamon`: chưa chắc chắn (Acetaminophen 90.9%, Paaracetamol 87%) → **không tự áp dụng**, kèm cảnh báo "Cần xác nhận, không tự áp dụng"<br>`Warfarin` → Warfarin: khớp chính xác (100%), tự áp dụng |
| Mức cao nhất (thuốc - thuốc) | Chưa có bản ghi |
| Gợi ý xử trí | — (không có phát hiện thuốc - thuốc) |
| Disclaimer | Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay. |

| Cặp | Mức độ | Nguồn | Mở bản ghi gốc | Nguồn cập nhật |
|---|---|---|---|---|
| Warfarin + rượu, bia (đồ uống có cồn) (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Warfarin + thực phẩm giàu vitamin K (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |

<details><summary>Output JSON thực tế (rút gọn)</summary>

```json
{
 "normalized": [
  {
   "input": "paracetamon",
   "status": "suggest",
   "canonical_name": "",
   "drug_id": "",
   "suggestions": [
    {
     "drug_id": "DDInter14",
     "canonical_name": "Acetaminophen",
     "score": 0.909
    },
    {
     "drug_id": "DAV:paaracetamol",
     "canonical_name": "Paaracetamol",
     "score": 0.87
    }
   ],
   "note": "Cần xác nhận, không tự áp dụng"
  },
  {
   "input": "Warfarin",
   "status": "ok",
   "canonical_name": "Warfarin",
   "drug_id": "DDInter1951",
   "suggestions": [],
   "note": ""
  }
 ],
 "max_severity_vi": "Chưa có bản ghi",
 "findings": [],
 "food_findings": [
  {
   "pair": [
    "Warfarin",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Trung bình",
   "summary": "Enhanced hypoprothrombinemic response to warfarin has been reported in patients with acute alcohol intoxication and/or liver disease. The proposed mechanisms are inhibiti…",
   "management": "Patients taking oral anticoagulants should be counseled to avoid large amounts of ethanol, but moderate consumption (one to two drinks per day) are not likely to affect t…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Warfarin",
    "thực phẩm giàu vitamin K"
   ],
   "severity_vi": "Trung bình",
   "summary": "Vitamin K may antagonize the hypoprothrombinemic effect of oral anticoagulants. Vitamin K is a cofactor in the synthesis of blood clotting factors that are inhibited by o…",
   "management": "Intake of vitamin K through supplements or diet should not vary significantly during oral anticoagulant therapy. The diet in general should remain consistent, as other fo…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  }
 ],
 "duplicate_findings": [],
 "no_record_pairs": [],
 "disclaimer": "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay."
}
```

</details>

**Kết quả: ✅ Đạt.** Điểm khớp 90,9% vẫn chỉ là gợi ý: hệ thống chỉ tự áp dụng khi khớp chính xác 100%. Cặp với Warfarin chưa được tra cho tới khi người dùng xác nhận tên.

### TC4. Cặp không có bản ghi tương tác

- **Đầu vào:** `["Piracetam", "Paracetamol"]`
- **Mong đợi:** Ghi rõ "chưa có bản ghi", không kết luận an toàn.
- **Thời gian phản hồi:** 77 ms

| Tiêu chí | Output thực tế |
|---|---|
| Độ tin cậy nhận diện tên | `Piracetam` → Piracetam: khớp chính xác (100%), tự áp dụng<br>`Paracetamol` → Acetaminophen: khớp chính xác (100%), tự áp dụng |
| Mức cao nhất (thuốc - thuốc) | Chưa có bản ghi |
| Gợi ý xử trí | — (không có phát hiện thuốc - thuốc) |
| Disclaimer | Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay. |

| Cặp | Mức độ | Nguồn | Mở bản ghi gốc | Nguồn cập nhật |
|---|---|---|---|---|
| Acetaminophen + rượu, bia (đồ uống có cồn) (thức ăn) | Nghiêm trọng | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Acetaminophen + Piracetam | Chưa có bản ghi | — | — | — |

<details><summary>Output JSON thực tế (rút gọn)</summary>

```json
{
 "normalized": [
  {
   "input": "Piracetam",
   "status": "ok",
   "canonical_name": "Piracetam",
   "drug_id": "DAV:piracetam",
   "suggestions": [],
   "note": ""
  },
  {
   "input": "Paracetamol",
   "status": "ok",
   "canonical_name": "Acetaminophen",
   "drug_id": "DDInter14",
   "suggestions": [],
   "note": ""
  }
 ],
 "max_severity_vi": "Chưa có bản ghi",
 "findings": [],
 "food_findings": [
  {
   "pair": [
    "Acetaminophen",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Nghiêm trọng",
   "summary": "Chronic, excessive consumption of alcohol may increase the risk of acetaminophen-induced hepatotoxicity, which has included rare cases of fatal hepatitis and frank hepati…",
   "management": "In general, chronic alcoholics should avoid regular or excessive use of acetaminophen. Alternative analgesic/antipyretic therapy may be appropriate in patients who consum…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  }
 ],
 "duplicate_findings": [],
 "no_record_pairs": [
  [
   "Acetaminophen",
   "Piracetam"
  ]
 ],
 "disclaimer": "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay."
}
```

</details>

**Kết quả: ✅ Đạt.** Cặp nằm trong `no_record_pairs`, mức hiển thị là "Chưa có bản ghi"; không có câu nào kết luận an toàn. Giao diện ghi thêm "không đảm bảo an toàn tuyệt đối".

### TC5. Biệt dược phối hợp (ca chưa đạt)

- **Đầu vào:** `["Augmentin", "Warfarin"]`
- **Mong đợi:** Nhận `Augmentin` là Amoxicillin + Clavulanic acid và tra cả hai với Warfarin.
- **Thời gian phản hồi:** 46 ms

| Tiêu chí | Output thực tế |
|---|---|
| Độ tin cậy nhận diện tên | `Augmentin`: chưa chắc chắn (Clavulanic acid 100%, Amoxicillin 100%) → **không tự áp dụng**, kèm cảnh báo "Thuốc phối hợp nhiều hoạt chất — chọn hoạt chất đúng"<br>`Warfarin` → Warfarin: khớp chính xác (100%), tự áp dụng |
| Mức cao nhất (thuốc - thuốc) | Chưa có bản ghi |
| Gợi ý xử trí | — (không có phát hiện thuốc - thuốc) |
| Disclaimer | Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay. |

| Cặp | Mức độ | Nguồn | Mở bản ghi gốc | Nguồn cập nhật |
|---|---|---|---|---|
| Warfarin + rượu, bia (đồ uống có cồn) (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Warfarin + thực phẩm giàu vitamin K (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |

<details><summary>Output JSON thực tế (rút gọn)</summary>

```json
{
 "normalized": [
  {
   "input": "Augmentin",
   "status": "suggest",
   "canonical_name": "",
   "drug_id": "",
   "suggestions": [
    {
     "drug_id": "DDInter394",
     "canonical_name": "Clavulanic acid",
     "score": 1.0
    },
    {
     "drug_id": "DDInter83",
     "canonical_name": "Amoxicillin",
     "score": 1.0
    }
   ],
   "note": "Thuốc phối hợp nhiều hoạt chất — chọn hoạt chất đúng"
  },
  {
   "input": "Warfarin",
   "status": "ok",
   "canonical_name": "Warfarin",
   "drug_id": "DDInter1951",
   "suggestions": [],
   "note": ""
  }
 ],
 "max_severity_vi": "Chưa có bản ghi",
 "findings": [],
 "food_findings": [
  {
   "pair": [
    "Warfarin",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Trung bình",
   "summary": "Enhanced hypoprothrombinemic response to warfarin has been reported in patients with acute alcohol intoxication and/or liver disease. The proposed mechanisms are inhibiti…",
   "management": "Patients taking oral anticoagulants should be counseled to avoid large amounts of ethanol, but moderate consumption (one to two drinks per day) are not likely to affect t…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Warfarin",
    "thực phẩm giàu vitamin K"
   ],
   "severity_vi": "Trung bình",
   "summary": "Vitamin K may antagonize the hypoprothrombinemic effect of oral anticoagulants. Vitamin K is a cofactor in the synthesis of blood clotting factors that are inhibited by o…",
   "management": "Intake of vitamin K through supplements or diet should not vary significantly during oral anticoagulant therapy. The diet in general should remain consistent, as other fo…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  }
 ],
 "duplicate_findings": [],
 "no_record_pairs": [],
 "disclaimer": "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay."
}
```

</details>

**Kết quả: ❌ Chưa đạt.** Hệ thống trả `suggest` và dừng ở bước hỏi lại, nên cặp Amoxicillin - Warfarin (mức Trung bình khi nhập riêng hoạt chất) không được tra cho tới khi người dùng chọn hoạt chất. Hệ thống không báo "an toàn", nhưng độ nhạy giảm. Đã ghi vào Action Items của report.md.

### TC6. Đơn 3 thuốc, có trùng nhóm điều trị

- **Đầu vào:** `["Aspirin", "Ibuprofen", "Warfarin"]`
- **Mong đợi:** Báo đủ 3 cặp thuốc - thuốc, xếp mức nặng trước; báo Aspirin và Ibuprofen cùng nhóm NSAID.
- **Thời gian phản hồi:** 64 ms

| Tiêu chí | Output thực tế |
|---|---|
| Độ tin cậy nhận diện tên | `Aspirin` → Acetylsalicylic acid: khớp chính xác (100%), tự áp dụng<br>`Ibuprofen` → Ibuprofen: khớp chính xác (100%), tự áp dụng<br>`Warfarin` → Warfarin: khớp chính xác (100%), tự áp dụng |
| Mức cao nhất (thuốc - thuốc) | Nghiêm trọng |
| Gợi ý xử trí | Acetylsalicylic acid + Warfarin: This combination, especially with analgesic/antipyretic aspirin doses, should generally be avoided unless the potential benefit outweighs the risk of bleeding. If concomitant therapy is used for additive anticoagulant effects, monitoring for excessive anticoag…<br>Ibuprofen + Warfarin: NSAIDs should be administered with oral anticoagulants only if benefit outweighs risk. The INR should be checked frequently and oral anticoagulant dosage adjusted accordingly, particularly following initiation or discontinuation of NSAIDs in patients who are s…<br>Acetylsalicylic acid + Ibuprofen: Patients receiving low-dose aspirin for cardioprotection should avoid the regular use of ibuprofen and possibly other NSAIDs. Occasional use of ibuprofen is acceptable, as the risk from any attenuation of the antiplatelet effect of low-dose aspirin is likely t… |
| Disclaimer | Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay. |

| Cặp | Mức độ | Nguồn | Mở bản ghi gốc | Nguồn cập nhật |
|---|---|---|---|---|
| Acetylsalicylic acid + Warfarin | Nghiêm trọng | DDInter 2.0 | [DDInter 2.0](https://ddinter2.scbdd.com/server/interact/34056/) | 2026-09-30 |
| Ibuprofen + Warfarin | Nghiêm trọng | DDInter 2.0 | [DDInter 2.0](https://ddinter2.scbdd.com/server/interact/10470/) | 2026-09-30 |
| Acetylsalicylic acid + Ibuprofen | Nghiêm trọng | DDInter 2.0 | [DDInter 2.0](https://ddinter2.scbdd.com/server/interact/10165/) | 2026-09-30 |
| Acetylsalicylic acid + Ibuprofen (trùng nhóm) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Acetylsalicylic acid + rượu, bia (đồ uống có cồn) (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Warfarin + rượu, bia (đồ uống có cồn) (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Ibuprofen + rượu, bia (đồ uống có cồn) (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Warfarin + thực phẩm giàu vitamin K (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |

<details><summary>Output JSON thực tế (rút gọn)</summary>

```json
{
 "normalized": [
  {
   "input": "Aspirin",
   "status": "ok",
   "canonical_name": "Acetylsalicylic acid",
   "drug_id": "DDInter20",
   "suggestions": [],
   "note": ""
  },
  {
   "input": "Ibuprofen",
   "status": "ok",
   "canonical_name": "Ibuprofen",
   "drug_id": "DDInter900",
   "suggestions": [],
   "note": ""
  },
  {
   "input": "Warfarin",
   "status": "ok",
   "canonical_name": "Warfarin",
   "drug_id": "DDInter1951",
   "suggestions": [],
   "note": ""
  }
 ],
 "max_severity_vi": "Nghiêm trọng",
 "findings": [
  {
   "pair": [
    "Acetylsalicylic acid",
    "Warfarin"
   ],
   "severity_vi": "Nghiêm trọng",
   "summary": "Aspirin, even in small doses, may increase the risk of bleeding in patients on oral anticoagulants by inhibiting platelet aggregation, prolonging bleeding time, and induc…",
   "management": "This combination, especially with analgesic/antipyretic aspirin doses, should generally be avoided unless the potential benefit outweighs the risk of bleeding. If concomi…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "DDInter 2.0",
     "source_url": "https://ddinter2.scbdd.com/server/interact/34056/"
    }
   ]
  },
  {
   "pair": [
    "Ibuprofen",
    "Warfarin"
   ],
   "severity_vi": "Nghiêm trọng",
   "summary": "Nonsteroidal anti-inflammatory drugs (NSAIDs) may potentiate the hypoprothrombinemic effect and bleeding risk associated with oral anticoagulants.",
   "management": "NSAIDs should be administered with oral anticoagulants only if benefit outweighs risk. The INR should be checked frequently and oral anticoagulant dosage adjusted accordi…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "DDInter 2.0",
     "source_url": "https://ddinter2.scbdd.com/server/interact/10470/"
    }
   ]
  },
  {
   "pair": [
    "Acetylsalicylic acid",
    "Ibuprofen"
   ],
   "severity_vi": "Nghiêm trọng",
   "summary": "The antiplatelet and cardioprotective effect of low-dose aspirin may be antagonized by coadministration of some nonsteroidal anti-inflammatory drugs (NSAIDs). Ibuprofen h…",
   "management": "Patients receiving low-dose aspirin for cardioprotection should avoid the regular use of ibuprofen and possibly other NSAIDs. Occasional use of ibuprofen is acceptable, a…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "DDInter 2.0",
     "source_url": "https://ddinter2.scbdd.com/server/interact/10165/"
    }
   ]
  }
 ],
 "food_findings": [
  {
   "pair": [
    "Acetylsalicylic acid",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Trung bình",
   "summary": "The concurrent use of aspirin or nonsteroidal anti-inflammatory drugs (NSAIDs) and ethanol may lead to gastrointestinal (GI) blood loss. The mechanism may be due to a com…",
   "management": "Patients should be counseled on this potential interaction and advised to refrain from alcohol consumption while taking aspirin or NSAIDs.",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Warfarin",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Trung bình",
   "summary": "Enhanced hypoprothrombinemic response to warfarin has been reported in patients with acute alcohol intoxication and/or liver disease. The proposed mechanisms are inhibiti…",
   "management": "Patients taking oral anticoagulants should be counseled to avoid large amounts of ethanol, but moderate consumption (one to two drinks per day) are not likely to affect t…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Ibuprofen",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Trung bình",
   "summary": "The concurrent use of aspirin or nonsteroidal anti-inflammatory drugs (NSAIDs) and ethanol may lead to gastrointestinal (GI) blood loss. The mechanism may be due to a com…",
   "management": "Patients should be counseled on this potential interaction and advised to refrain from alcohol consumption while taking aspirin or NSAIDs.",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Warfarin",
    "thực phẩm giàu vitamin K"
   ],
   "severity_vi": "Trung bình",
   "summary": "Vitamin K may antagonize the hypoprothrombinemic effect of oral anticoagulants. Vitamin K is a cofactor in the synthesis of blood clotting factors that are inhibited by o…",
   "management": "Intake of vitamin K through supplements or diet should not vary significantly during oral anticoagulant therapy. The diet in general should remain consistent, as other fo…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  }
 ],
 "duplicate_findings": [
  {
   "pair": [
    "Acetylsalicylic acid",
    "Ibuprofen"
   ],
   "severity_vi": "Trung bình",
   "summary": "Trùng nhóm điều trị: nonsteroidal anti-inflammatories (2 thuốc)",
   "management": "",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "nonsteroidal anti-inflammatories",
     "source_url": ""
    }
   ]
  }
 ],
 "no_record_pairs": [],
 "disclaimer": "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay."
}
```

</details>

**Kết quả: ✅ Đạt.** Đủ 3 cặp mức Nghiêm trọng, mỗi cặp có đường dẫn bản ghi DDInter riêng; có cảnh báo trùng nhóm.

### TC7. Tên thuốc không tồn tại

- **Đầu vào:** `["Thuocxyz123", "Warfarin"]`
- **Mong đợi:** Trả `unknown`, có cảnh báo, không suy đoán.
- **Thời gian phản hồi:** 83 ms

| Tiêu chí | Output thực tế |
|---|---|
| Độ tin cậy nhận diện tên | `Thuocxyz123`: không nhận diện được → kèm cảnh báo "Chưa có bản ghi trong CSDL"<br>`Warfarin` → Warfarin: khớp chính xác (100%), tự áp dụng |
| Mức cao nhất (thuốc - thuốc) | Chưa có bản ghi |
| Gợi ý xử trí | — (không có phát hiện thuốc - thuốc) |
| Disclaimer | Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay. |

| Cặp | Mức độ | Nguồn | Mở bản ghi gốc | Nguồn cập nhật |
|---|---|---|---|---|
| Warfarin + rượu, bia (đồ uống có cồn) (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |
| Warfarin + thực phẩm giàu vitamin K (thức ăn) | Trung bình | DDInter 2.0 | chưa có đường dẫn | 2026-09-30 |

<details><summary>Output JSON thực tế (rút gọn)</summary>

```json
{
 "normalized": [
  {
   "input": "Thuocxyz123",
   "status": "unknown",
   "canonical_name": "",
   "drug_id": "",
   "suggestions": [],
   "note": "Chưa có bản ghi trong CSDL"
  },
  {
   "input": "Warfarin",
   "status": "ok",
   "canonical_name": "Warfarin",
   "drug_id": "DDInter1951",
   "suggestions": [],
   "note": ""
  }
 ],
 "max_severity_vi": "Chưa có bản ghi",
 "findings": [],
 "food_findings": [
  {
   "pair": [
    "Warfarin",
    "rượu, bia (đồ uống có cồn)"
   ],
   "severity_vi": "Trung bình",
   "summary": "Enhanced hypoprothrombinemic response to warfarin has been reported in patients with acute alcohol intoxication and/or liver disease. The proposed mechanisms are inhibiti…",
   "management": "Patients taking oral anticoagulants should be counseled to avoid large amounts of ethanol, but moderate consumption (one to two drinks per day) are not likely to affect t…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  },
  {
   "pair": [
    "Warfarin",
    "thực phẩm giàu vitamin K"
   ],
   "severity_vi": "Trung bình",
   "summary": "Vitamin K may antagonize the hypoprothrombinemic effect of oral anticoagulants. Vitamin K is a cofactor in the synthesis of blood clotting factors that are inhibited by o…",
   "management": "Intake of vitamin K through supplements or diet should not vary significantly during oral anticoagulant therapy. The diet in general should remain consistent, as other fo…",
   "citations": [
    {
     "source_name": "DDInter 2.0",
     "label": "",
     "source_url": ""
    }
   ]
  }
 ],
 "duplicate_findings": [],
 "no_record_pairs": [],
 "disclaimer": "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay."
}
```

</details>

**Kết quả: ✅ Đạt.** Tên lạ không được gán vào hoạt chất nào; không có kết luận cho cặp chứa tên này.

### TC8. Luồng đơn thuốc → kiểm tra → gửi xem xét → xem lại kết luận

- **Đầu vào:** đơn "Eval manual TC9" gồm `Aspirin`, `Warfarin`
- **Mong đợi:** lưu được đơn, chạy kiểm tra có mã để xem lại, gửi được ca cho người có chuyên môn, người xem xét ghi
  được kết luận và người gửi đọc lại được.

| Bước | Lời gọi | Output thực tế |
|---|---|---|
| 1. Tạo đơn | `POST /prescriptions` | `{"id": "RX-80C3F8", "status": "Chưa kiểm tra", "medications": [{"name": "Aspirin", "ingredient": "Acetylsalicylic acid", "verified": true, "norm_status": "ok"}, {"name": "Warfarin", "ingredient": "Warfarin", "verified": true, "norm_status": "ok"}]}` |
| 2. Chạy kiểm tra | `POST /prescriptions/RX-80C3F8/checks` | `{"check_id": "CHECK-B808F4", "status": "done", "max_severity": "major", "findings_count": 1}` |
| 3. Mở lại kết quả | `GET /checks/CHECK-B808F4` | Trả đủ chi tiết: cặp `Acetylsalicylic acid` + `Warfarin`, mức Nghiêm trọng, cơ chế, xử trí, trích dẫn DDInter, disclaimer, `steps_done` 8 bước |
| 4. Gửi xem xét | `POST /reviews` | `{"review_id": 1, "status": "Đang chờ dược sĩ xem xét"}` |
| 5. Người xem xét phản hồi | `PATCH /reviews/1` | `{"id": 1, "prescription_id": "RX-80C3F8", "check_id": "CHECK-B808F4", "patient": "Ca thử TC9", "med_count": 2, "message": "Nhờ xem xét cặp Aspirin - Warfarin", "status": "Đã phản hồi"}` |

**Kết quả: 🟡 Đạt một phần.** Đơn, lần kiểm tra và ca xem xét đều lưu được và mở lại được bằng mã. Phần chưa đạt:
ca xem xét chỉ đổi được trạng thái "Đang chờ" sang "Đã phản hồi", **chưa có trường lưu nội dung kết luận** của người
xem xét, nên người gửi chưa đọc được kết luận bằng chữ.

## 5. Điểm còn thiếu so với tiêu chí

| Điểm thiếu | Thấy ở ca | Việc cần làm |
|---|---|---|
| Chưa có điểm tin cậy của LLM vì bước LLM giải thích (`src/services/explainer.py`) chưa nối vào ứng dụng | Mọi ca | Khi nối LLM: trả kèm điểm tin cậy và kết quả kiểm tra grounding; dưới 90% thì hiện cảnh báo hoặc dùng lại bản mẫu từ CSDL |
| Biệt dược phối hợp dừng ở bước hỏi lại, bỏ sót cặp có bản ghi | TC5 | Coi tên phối hợp là `ok` với đủ các hoạt chất |
| Phát hiện thuốc - thức ăn và trùng nhóm chưa có đường dẫn mở bản ghi gốc | TC1, TC2, TC6 | Bổ sung `source_url` và mã bản ghi cho hai loại này |
| Ngày cập nhật chỉ có theo nguồn, chưa gắn vào từng phát hiện | Mọi ca | Thêm `last_updated` vào `citations[]` để giao diện hiện ngay cạnh cảnh báo |
| Lời cơ chế và xử trí của DDInter còn là tiếng Anh | TC1, TC6 | Dịch qua bước LLM giải thích có kiểm tra grounding |
| `max_severity_vi` chỉ tính cặp thuốc - thuốc, không tính thuốc - thức ăn | TC4 (thức ăn mức Nghiêm trọng nhưng tổng là "Chưa có bản ghi") | Thống nhất cách tính hoặc tách hai chỉ số trên giao diện |
| Ca xem xét chưa lưu nội dung kết luận | TC8 | Thêm trường kết luận vào bảng `reviews` và `PATCH /reviews/{id}` |
| Giờ tạo đơn lệch múi giờ so với giờ tạo lần kiểm tra (`09:13` so với `02:13`, cùng ghi `+00:00`) | TC8 | Dùng thống nhất giờ UTC khi ghi `prescriptions.created_at` |

Dữ liệu thử của TC8 (đơn `RX-80C3F8`, lần kiểm tra `CHECK-B808F4`, ca xem xét số 1) còn trong Database của máy chạy
thử; xóa trước khi quay video demo.

## 6. Bổ sung request/response API thô — 2026-10-04

Để lưu bằng chứng có thể đối chiếu từng request với response, chạy thêm năm ca trực tiếp trên backend local. File
JSON UTF-8 nguyên bản và metadata nằm trong [manual/2026-10-04/](manual/2026-10-04/); tổng hợp ở
[case-results.json](manual/2026-10-04/case-results.json).

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| TC-01 — Aspirin + Warfarin | PASS — HTTP 200, `major`, có citation | [request](manual/2026-10-04/TC-01/request.json), [response](manual/2026-10-04/TC-01/response.json) |
| TC-02 — Panadol + Warfarin | PASS — HTTP 200, Panadol → Acetaminophen, `moderate` | [request](manual/2026-10-04/TC-02/request.json), [response](manual/2026-10-04/TC-02/response.json) |
| TC-03 — tên không tồn tại | PASS — trạng thái `unknown`, không có finding kết luận là an toàn | [request](manual/2026-10-04/TC-03/request.json), [response](manual/2026-10-04/TC-03/response.json) |
| TC-04 — `asca` | PASS — `suggest`, kèm gợi ý cần xác nhận | [request](manual/2026-10-04/TC-04/request.json), [response](manual/2026-10-04/TC-04/response.json) |
| TC-05 — đơn → check → chi tiết | PASS — HTTP 201/201/200, detail có finding và citation | [tạo đơn](manual/2026-10-04/TC-05/response-create.json), [check](manual/2026-10-04/TC-05/response-check.json), [chi tiết](manual/2026-10-04/TC-05/response-detail.json) |

Metadata sáu nguồn và ngày cập nhật được lưu riêng tại [sources-response.json](manual/2026-10-04/sources-response.json).
TC-05 tạo đơn test tổng hợp `RX-D81A6D` và check `CHECK-7BAF8B` trên database của máy chạy thử.
