# Frontend kết nối backend

Frontend sử dụng API `/api/v1` của backend FastAPI để tải và lưu dữ liệu.

Chạy backend ở cổng 8000 và frontend với `npm run dev` (cổng 3000).
Next.js chuyển tiếp `/api/v1/*` đến `http://127.0.0.1:8000`.
Để dùng backend khác, đặt `BACKEND_URL` trong `interface/fontend/.env.local`, rồi khởi động lại Next.js.

Trước khi chạy trên CSDL đã tồn tại, đặt `DATABASE_URL` trỏ đúng CSDL backend và chạy `python -m alembic upgrade head` tại root repository. Migration thêm tên/ngày tạo đơn; hồ sơ cũ giữ ngày tạo chưa xác định.

Giao diện tải đơn thuốc, lịch sử và review từ backend. Thêm đơn (kèm thuốc), thêm nhiều thuốc và gửi review chỉ báo thành công sau khi API lưu. Khi backend không kết nối được, giao diện hiển thị lỗi và nút thử lại. CSDL trống hiển thị trạng thái trống.
