# Bản dịch tiếng Việt của kết quả kiểm tra

Bản gốc giữ nguyên trong `interaction_mechanisms`, `food_interactions`, `ara_interactions`.
Bảng `content_translations` lưu bản tiếng Việt theo bảng, ID, trường và mã ngôn ngữ.
Bảng này không phụ thuộc khóa ngoại vào nguồn, nên nạp lại MVP không xóa bản dịch.
SHA-256 của nguyên văn xác định bản dịch còn hợp lệ; API bỏ qua bản dịch cũ khi nguồn đổi.
API chỉ đọc DB, không gọi dịch vụ dịch trong lúc kiểm tra đơn.

## Chuẩn bị

Chạy từ thư mục gốc dự án:

```powershell
$env:DATABASE_URL = (Get-Content .env | Where-Object { $_ -match '^DATABASE_URL=' }) -replace '^DATABASE_URL=', ''
python -m alembic upgrade head
python scripts/translate_evidence.py --dry-run --limit 0
```

Google Basic: đặt `GOOGLE_TRANSLATION_API_KEY` trong `.env`; bật Cloud Translation API và billing trên dự án Google.
Google Advanced với glossary: đặt `GOOGLE_TRANSLATION_PROJECT`, `GOOGLE_TRANSLATION_LOCATION`, `GOOGLE_TRANSLATION_GLOSSARY`.
Đặt `GOOGLE_APPLICATION_CREDENTIALS` thành đường dẫn JSON service account hoặc dùng Application Default Credentials.
Glossary phải thuộc cùng khu vực với request. Không commit API key hoặc JSON credentials.

```powershell
python scripts/translate_evidence.py --provider google --limit 100
python scripts/translate_evidence.py --provider google --limit 0
```

Nếu chọn DeepSeek đã cấu hình:

```powershell
python scripts/translate_evidence.py --provider deepseek --limit 100
python scripts/translate_evidence.py --provider deepseek --limit 0
```

Mặc định mỗi lượt tối đa 100 trường để dễ kiểm tra; `--limit 0` dịch tất cả.
Có thể giới hạn `--tables interaction_mechanisms`. Ưu tiên cơ chế major rồi moderate và số cặp sử dụng nhiều.
Lưu sau từng batch, chạy lại tự bỏ qua bản dịch còn hợp lệ. Không dịch tên thuốc, mức độ hay citation riêng.
Không gửi đơn thuốc hoặc thông tin bệnh nhân; chỉ gửi văn bản bằng chứng từ nguồn dữ liệu.

## Rà soát

Bản dịch máy có `reviewed=false`, giao diện ghi "Bản dịch tự động, chưa được rà soát chuyên môn".
Người rà soát có thể sửa `translated_text` và đặt `reviewed=true` trong DB.
Không đổi `source_hash` khi chỉ sửa bản dịch; hash luôn thuộc nguyên văn hiện tại.
API chỉ dùng bản dịch không rỗng và khớp hash. Nếu thiếu/cũ, trả nguyên văn và `untranslated_fields`.
`original_mechanism` và `original_management` luôn chứa nguyên văn; mức độ và nguồn bằng chứng giữ nguyên.

Tài liệu Google: https://docs.cloud.google.com/translate/docs/reference/rest/v2/translate
Glossary: https://docs.cloud.google.com/translate/docs/advanced/glossary


## Gemini (mặc định)

Thêm `GEMINI_API_KEY` vào `.env`; `GOOGLE_API_KEY` cũng được hỗ trợ.
Model mặc định là `gemini-3.5-flash`, có thể đổi bằng `GEMINI_MODEL`.

```powershell
python scripts/translate_evidence.py --provider gemini --limit 4
python scripts/translate_evidence.py --provider gemini --limit 0
```

Gemini nhận JSON văn bản bằng chứng, trả bản dịch theo đúng thứ tự.
Output bị chặn, bị cắt hoặc thiếu trường sẽ không được lưu.
Khóa nằm trong header, không đưa vào URL hay log.
Tài liệu: https://ai.google.dev/api/generate-content

Dịch toàn bộ với tối đa 4 request đồng thời: `python scripts/translate_evidence.py --provider gemini --limit 0 --concurrency 4`. Giảm concurrency khi quota thấp. Log `Completed` xác nhận lượt chạy kết thúc; chạy lại bỏ qua bản dịch đã lưu.
