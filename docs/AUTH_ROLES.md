# Đăng nhập và phân quyền

| Vai trò | Chức năng |
| --- | --- |
| Dược sĩ (pharmacist) | Quản lý đơn thuốc, kiểm tra an toàn, gửi yêu cầu trao đổi và xem phản hồi của bác sĩ trên yêu cầu mình tạo. |
| Bác sĩ (doctor) | Quản lý đơn thuốc, kiểm tra an toàn, xem lịch sử như dược sĩ; đồng thời xem yêu cầu trao đổi và gửi/cập nhật phản hồi. |

Sidebar của hai vai trò có Tổng quan, Đơn thuốc, Kiểm tra an toàn và Lịch sử. Chỉ bác sĩ có mục Yêu cầu trao đổi trong sidebar và điều hướng di động. Dược sĩ gửi yêu cầu và xem phản hồi từ màn hình kiểm tra an toàn.

API yêu cầu đăng nhập; quyền được kiểm tra từ tài khoản trong database. Trình duyệt lưu cookie HttpOnly; server chỉ lưu hash phiên. Đăng xuất, vô hiệu hóa tài khoản hoặc đặt lại mật khẩu thu hồi phiên. Phiên thường có thời hạn 8 giờ, lựa chọn ghi nhớ có thời hạn 30 ngày. Mật khẩu dùng scrypt, không lưu bản rõ. Login có giới hạn 20 lần/10 phút/IP trong mỗi worker; khi triển khai nhiều worker cần cấu hình rate limit dùng chung tại gateway. CORS_ORIGINS phải chứa origin frontend hợp lệ; production dùng HTTPS để cookie Secure hoạt động.

## Cài đặt database

Từ thư mục gốc P-060, đặt DATABASE_URL trỏ đúng database ứng dụng rồi chạy:

```powershell
python -m alembic upgrade head
```

Không chỉ khởi động dev server để nâng schema database đã tồn tại: create_all không thêm cột vào bảng cũ. Migration mới giữ yêu cầu cũ; các yêu cầu đó chưa có người tạo nên chỉ bác sĩ nhìn thấy, không cho phản hồi đến tài khoản chưa xác định. Không tự gán chúng cho dược sĩ bất kỳ.

## Quản trị tài khoản

```powershell
python -m scripts.manage_users create --email bacsi@pharmacy.vn --role doctor --name "Bác sĩ Nguyễn An"
python -m scripts.manage_users create --email duocsi@pharmacy.vn --role pharmacist --name "Dược sĩ Minh Anh"
python -m scripts.manage_users reset-password --email bacsi@pharmacy.vn
python -m scripts.manage_users disable --email duocsi@pharmacy.vn
```

Lệnh hỏi mật khẩu hai lần, tối thiểu 12 ký tự; không truyền mật khẩu qua tham số lệnh. Không có tài khoản/mật khẩu mặc định và không mở đăng ký công khai. Quên mật khẩu trên giao diện hướng dẫn liên hệ quản trị viên.

Danh sách trao đổi làm mới mỗi 30 giây và có nút làm mới ở không gian bác sĩ. Phản hồi lưu tên bác sĩ và thời gian, hiển thị lại cho dược sĩ đã tạo yêu cầu.
