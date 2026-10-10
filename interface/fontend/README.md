# Frontend kết nối backend

Frontend sử dụng API `/api/v1` của backend FastAPI để tải và lưu dữ liệu.

Có thể chạy `npm run dev` từ root repository (`D:\Work\P-060`); lệnh ở root chuyển tiếp đến frontend.

Trên Windows, thiết lập backend tại root trước lần chạy đầu:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Lệnh `python --version` phải trả về phiên bản Python đã cài. Nếu Windows chỉ có alias trong `WindowsApps`, cài Python thật rồi mở lại terminal. Đặt `.env` tại root để backend đọc cấu hình database.

Chạy `npm run dev` ngay trong thư mục `interface/fontend`: lệnh này tự khởi động backend (cổng 8000), chờ backend sẵn sàng rồi khởi động frontend (cổng 3000). Nhấn `Ctrl+C` để dừng cả hai. Backend sử dụng Python ở `.venv` của root repository; có thể đặt `PYTHON` để dùng Python khác. Cài dependencies backend từ `requirements.txt` trước khi chạy. PostgreSQL cần chạy sẵn theo cấu hình `.env` ở root.

Nếu chỉ cần frontend với backend chạy riêng, dùng `npm run dev:frontend`. Có thể đặt `BACKEND_PORT` và `PORT` để đổi cổng khi chạy chung; lệnh tự cấu hình proxy tới backend tương ứng. Dừng các dịch vụ cũ trước khi chạy, tránh trùng cổng.
Next.js chuyển tiếp `/api/v1/*` đến `http://127.0.0.1:8000`.
Để dùng backend khác, đặt `BACKEND_URL` trong `interface/fontend/.env.local`, rồi khởi động lại Next.js.

Trước khi chạy trên CSDL đã tồn tại, đặt `DATABASE_URL` trỏ đúng CSDL backend và chạy `python -m alembic upgrade head` tại root repository. Migration thêm tên/ngày tạo đơn; hồ sơ cũ giữ ngày tạo chưa xác định.

Giao diện tải đơn thuốc, lịch sử và review từ backend. Thêm đơn (kèm thuốc), thêm nhiều thuốc và gửi review chỉ báo thành công sau khi API lưu. Khi backend không kết nối được, giao diện hiển thị lỗi và nút thử lại. CSDL trống hiển thị trạng thái trống.
