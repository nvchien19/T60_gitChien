# Brief — Nền tảng Quản lý Dự án Nghiên cứu (RPMP)

## 1. Bối cảnh & Vấn đề
Các đơn vị nghiên cứu (viện, trường, trung tâm R&D) hiện quản lý vòng đời dự án nghiên cứu (đề xuất → xét duyệt → triển khai → nghiệm thu) rời rạc qua email, Excel, Word, khiến việc tổng hợp tiến độ, kinh phí, dữ liệu và công bố khoa học tốn nhiều công sức thủ công và thiếu một nguồn dữ liệu thống nhất.

## 2. Mục tiêu sản phẩm
Xây dựng nền tảng quản lý **toàn bộ vòng đời dự án nghiên cứu**: đề xuất, xét duyệt, lập kế hoạch, phân công nhiệm vụ, theo dõi mốc tiến độ, ghi nhận kinh phí/dữ liệu, công bố và kết quả đầu ra — giúp đơn vị nghiên cứu có nguồn thông tin thống nhất và giảm thao tác tổng hợp báo cáo thủ công.

## 3. Đối tượng người dùng
| Vai trò | Nhu cầu chính |
|---|---|
| Chủ nhiệm đề tài | Lập kế hoạch, phân công, theo dõi tiến độ, nộp báo cáo |
| Thành viên nghiên cứu | Nhận việc, cập nhật tiến độ, upload tài liệu/dữ liệu |
| Quản trị/Phòng KHCN | Xét duyệt, quản lý danh mục dự án, tổng hợp báo cáo toàn đơn vị |
| Ban lãnh đạo | Xem dashboard tổng quan, ra quyết định |

## 4. Phạm vi (Scope)
**Giai đoạn 1 – Cơ bản**
- Quản lý dự án, thành viên, mốc công việc (milestone), tài liệu
- Báo cáo tiến độ
- Tối thiểu 2 vai trò (chủ nhiệm / quản trị) + luồng phê duyệt

**Giai đoạn 2 – Nâng cao  **
- Trợ lý tra cứu quy định có trích nguồn (RAG)
- Cảnh báo trễ hạn/rủi ro
- Tổng hợp báo cáo tự động
- Theo dõi công bố khoa học
- Dashboard danh mục dự án (portfolio)

**Ngoài phạm vi (giai đoạn đầu):** kế toán chi tiết, quản lý nhân sự/HRM, tích hợp thư viện khoa học bên ngoài (Scopus/WoS) — để lại cho các giai đoạn sau.

## 5. Định hướng công nghệ
- Frontend: React/Next.js
- Backend: FastAPI
- CSDL: PostgreSQL
- Lưu trữ tài liệu; Workflow engine cho luồng phê duyệt
- Dashboard: Power BI
- AI: RAG trên quy định & biểu mẫu nghiên cứu; LangGraph/agent workflow cho trợ lý & cảnh báo
- Hạ tầng: Docker, SSO/OIDC

## 6. Chỉ số thành công (KPI đề xuất)
- Giảm ≥ 50% thời gian tổng hợp báo cáo thủ công
- 100% dự án có luồng phê duyệt số hóa (thay email/giấy)
- ≥ 80% người dùng nội bộ active hàng tuần sau 3 tháng go-live
- Độ chính xác trích dẫn của trợ lý RAG ≥ 90% (giai đoạn nâng cao)

## 7. Rủi ro chính
- Dữ liệu quy định/biểu mẫu không chuẩn hóa → ảnh hưởng chất lượng RAG
- Kháng cự thay đổi từ người dùng quen quy trình cũ (email/Excel)
- Tích hợp SSO/OIDC với hệ thống định danh sẵn có của đơn vị

## 8. Mốc thời gian đề xuất
| Giai đoạn | Nội dung | Thời lượng |
|---|---|---|
| 1 | MVP Cơ bản | 8–10 tuần |
| 2 | Nâng cao (AI/RAG, dashboard) | 6–8 tuần tiếp theo |