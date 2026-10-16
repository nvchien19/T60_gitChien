"use client";

import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";

// Tầng 1 của disclaimer (docs/phap_ly/PHAP_LY_Y_TE.md): xác nhận phạm vi sử dụng một lần cho mỗi tài khoản trên
// mỗi trình duyệt. Lưu ở localStorage nên không phải bằng chứng đồng ý có thể kiểm chứng; đổi nội dung thì tăng VERSION.
const VERSION = "2026-10-17";

const POINTS = [
  "Đây là bản thử nghiệm phục vụ học tập và nghiên cứu, chưa được cấp phép như trang thiết bị y tế.",
  "Kết quả là cảnh báo tham khảo có nguồn, không phải chẩn đoán hay chỉ định điều trị. Quyết định kê, đổi hoặc ngừng thuốc thuộc về bác sĩ và dược sĩ.",
  "Mức độ tương tác hiển thị đúng như nguồn dữ liệu ghi. \"Chưa có bản ghi\" không có nghĩa là an toàn.",
  "Một số nội dung là bản dịch máy chưa được dược sĩ duyệt; chatbot, phần giải thích và nhận dạng ảnh đơn dùng dịch vụ AI đặt ở nước ngoài.",
  "Không nhập họ tên, số điện thoại, số định danh hay địa chỉ của bệnh nhân. Che các thông tin này trước khi tải ảnh đơn thuốc.",
];

export function TermsNotice({ userId }: { userId: number }) {
  const key = `p060-terms-${VERSION}-${userId}`;
  const [open, setOpen] = useState(false);
  const [agreed, setAgreed] = useState(false);

  useEffect(() => {
    try { setOpen(localStorage.getItem(key) !== "1"); } catch { setOpen(true); }
  }, [key]);

  if (!open) return null;

  function accept() {
    try { localStorage.setItem(key, "1"); } catch { /* không có localStorage: hỏi lại lần sau */ }
    setOpen(false);
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="terms-title" className="max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        <h2 id="terms-title" className="flex items-center gap-2 text-lg font-extrabold text-slate-900">
          <ShieldAlert className="size-5 text-amber-600" /> Trước khi sử dụng
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-700">
          {POINTS.map(point => <li key={point}>{point}</li>)}
        </ul>
        <label className="mt-5 flex items-start gap-2 text-sm font-semibold text-slate-800">
          <input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)} className="mt-1 size-4" />
          Tôi đã đọc và hiểu các giới hạn trên.
        </label>
        <button type="button" disabled={!agreed} onClick={accept} className="mt-5 min-h-[44px] w-full rounded-lg bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50">
          Tiếp tục
        </button>
      </div>
    </div>
  );
}
