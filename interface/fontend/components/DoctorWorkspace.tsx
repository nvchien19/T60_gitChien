"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, Clock3, FileText, RefreshCw, Send, Stethoscope, Users, X } from "lucide-react";
import { api, loadReviews, type Prescription, type ReviewRequest } from "@/lib/api";

export function DoctorReviewPanel() {
  const [requests, setRequests] = useState<ReviewRequest[]>([]);
  const [filter, setFilter] = useState("Đang chờ");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [response, setResponse] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [prescription, setPrescription] = useState<Prescription | null>(null);
  const [rxLoading, setRxLoading] = useState(false);
  const [rxError, setRxError] = useState("");
  const [rxOpen, setRxOpen] = useState(false);
  const [rxId, setRxId] = useState("");
  const rxRequest = useRef(0);
  useEffect(() => () => { rxRequest.current++; }, []);
  const rxDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (rxOpen) rxDialog.current?.showModal(); }, [rxOpen]);
  const selected = requests.find(r => r.id === selectedId);
  const reload = useCallback(async () => { setError(""); setLoading(true); try { setRequests(await loadReviews()); } catch (e) { setError((e as Error).message); } finally { setLoading(false); } }, []);
  useEffect(() => { void reload(); const timer = setInterval(() => { loadReviews().then(setRequests).catch(e => setError(e.message)); }, 30000); return () => clearInterval(timer); }, [reload]);
  function select(request: ReviewRequest) { setSelectedId(request.id); setResponse(request.response || ""); setError(""); }
  async function reply() {
    if (!selected || !response.trim() || saving) return;
    setSaving(true); setError("");
    try { await api(`/reviews/${selected.id}`, { status: "Đã phản hồi", response: response.trim() }, "PATCH"); await reload(); }
    catch (e) { setError((e as Error).message); } finally { setSaving(false); }
  }
  async function openPrescription() {
    if (!selected) return;
    const id = selected.prescriptionId;
    const request = ++rxRequest.current;
    setRxId(id); setRxOpen(true); setPrescription(null); setRxError(""); setRxLoading(true);
    try {
      const result = await api<Prescription>(`/prescriptions/${id}`);
      if (request === rxRequest.current) setPrescription(result);
    } catch (e) {
      if (request === rxRequest.current) setRxError((e as Error).message);
    } finally {
      if (request === rxRequest.current) setRxLoading(false);
    }
  }
  const visible = requests.filter(r => filter === "Tất cả" || r.status === filter);
  const waiting = requests.filter(r => r.status === "Đang chờ").length;
  return <div className="space-y-6">
      <div className="flex items-end justify-between gap-4"><div><p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-sky-600"><Stethoscope size={16} /> Phối hợp chuyên môn</p><h1 className="text-2xl font-extrabold sm:text-3xl">Yêu cầu trao đổi</h1><p className="mt-2 text-sm text-slate-500">Tiếp nhận yêu cầu từ dược sĩ và gửi phản hồi chuyên môn.</p></div><button onClick={() => void reload()} disabled={loading} className="rounded-lg border border-slate-200 bg-white p-3" aria-label="Làm mới yêu cầu"><RefreshCw size={18} className={loading ? "animate-spin" : ""} /></button></div>
      <div className="grid grid-cols-3 gap-3">{[["Tổng yêu cầu", requests.length, Users], ["Đang chờ", waiting, Clock3], ["Đã phản hồi", requests.length - waiting, CheckCircle2]].map(([label, value, Icon]) => { const Symbol = Icon as typeof Users; return <div key={String(label)} className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5"><Symbol size={18} className="mb-3 text-sky-500" /><p className="text-xs text-slate-500">{String(label)}</p><p className="mt-1 text-2xl font-extrabold">{String(value)}</p></div>; })}</div>
      {error && <p role="alert" className="rounded-lg bg-rose-50 p-4 text-sm text-rose-700">{error}</p>}
      <div className="grid gap-5 lg:grid-cols-[minmax(300px,0.9fr)_minmax(0,1.3fr)]">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="flex gap-2 border-b border-slate-100 p-4" aria-label="Lọc yêu cầu">{["Đang chờ", "Đã phản hồi", "Tất cả"].map(status => <button key={status} onClick={() => setFilter(status)} aria-pressed={filter === status} className={`rounded-lg px-3 py-2 text-xs font-bold ${filter === status ? "bg-sky-50 text-sky-700" : "text-slate-500 hover:bg-slate-50"}`}>{status}</button>)}</div>
          {loading && !requests.length ? <p role="status" className="p-8 text-sm text-slate-500">Đang tải yêu cầu…</p> : !visible.length ? <div className="p-10 text-center"><Users className="mx-auto mb-3 text-sky-400" /><p className="font-bold">Chưa có yêu cầu {filter === "Đang chờ" ? "đang chờ" : ""}</p><p className="mt-2 text-xs text-slate-500">Yêu cầu mới của dược sĩ sẽ xuất hiện tại đây.</p></div> : <div className="divide-y divide-slate-100">{visible.map(req => <button key={req.id} onClick={() => select(req)} aria-pressed={selectedId === req.id} className={`w-full p-5 text-left transition ${selectedId === req.id ? "bg-sky-50 ring-1 ring-inset ring-sky-200" : "hover:bg-slate-50"}`}><div className="flex items-center justify-between gap-2"><span className="text-sm font-bold">{req.creatorName || "Yêu cầu cũ"}</span><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${req.status === "Đang chờ" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}>{req.status}</span></div><p className="mt-2 line-clamp-2 text-sm text-slate-600">{req.message}</p><p className="mt-3 text-[11px] text-slate-400">{req.prescriptionId} · {req.date}</p></button>)}</div>}
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
          {!selected ? <div className="flex min-h-80 flex-col items-center justify-center text-center"><FileText size={34} className="mb-4 text-sky-300" /><h2 className="font-bold">Chọn một yêu cầu để xem chi tiết</h2><p className="mt-2 max-w-xs text-sm text-slate-500">Thông tin đơn thuốc và nội dung trao đổi sẽ hiển thị tại đây.</p></div> : <><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold text-sky-600">YÊU CẦU #{selected.id}</p><h2 className="mt-2 text-xl font-extrabold">Trao đổi về đơn {selected.prescriptionId}</h2><p className="mt-2 text-xs text-slate-500">Người gửi: {selected.creatorName || "chưa xác định"} · {selected.medCount} thuốc</p></div><button onClick={() => setSelectedId(null)} aria-label="Đóng chi tiết" className="p-2 text-slate-400"><X size={18} /></button></div>
          <p className="mt-5 whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-sm leading-7 text-slate-700">{selected.message}</p>
          <button onClick={() => void openPrescription()} className="mt-4 flex items-center gap-2 text-sm font-bold text-sky-600"><FileText size={16} /> Xem đơn thuốc</button>
          {selected.response && <div className="mt-6 rounded-xl border border-emerald-100 bg-emerald-50 p-4"><p className="text-xs font-bold text-emerald-700">Phản hồi của {selected.responderName} · {selected.respondedAt}</p><p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">{selected.response}</p></div>}
          <label htmlFor="doctor-response" className="mt-7 block text-sm font-bold">{selected.response ? "Cập nhật phản hồi" : "Phản hồi cho dược sĩ"}</label>
          <textarea id="doctor-response" value={response} onChange={e => setResponse(e.target.value)} maxLength={4000} disabled={saving || !selected.createdBy} placeholder="Nhập nhận định và hướng xử trí của bạn…" className="mt-3 min-h-36 w-full rounded-xl border border-slate-200 p-4 text-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100" />
          {!selected.createdBy && <p className="mt-2 text-xs text-amber-700">Yêu cầu cũ chưa được gắn với tài khoản dược sĩ.</p>}
          <button onClick={() => void reply()} disabled={saving || !response.trim() || !selected.createdBy} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-sky-500 px-5 py-3 text-sm font-bold text-white hover:bg-sky-600 disabled:opacity-50 sm:w-auto"><Send size={16} /> {saving ? "Đang gửi…" : "Gửi phản hồi"}</button></>}
        </section>
      </div>
    {rxOpen && <dialog ref={rxDialog} onCancel={() => setRxOpen(false)} aria-labelledby="rx-title" className="doctor-dialog m-auto max-h-[85dvh] w-[calc(100%_-_32px)] max-w-2xl overflow-hidden bg-transparent p-0"><section className="flex max-h-[85dvh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white"><div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-100 p-6"><h2 id="rx-title" className="text-lg font-extrabold">Đơn {rxId}</h2><button onClick={() => setRxOpen(false)} className="shrink-0 p-2" aria-label="Đóng đơn thuốc"><X size={20} /></button></div><div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-6">{rxLoading ? <p role="status">Đang tải đơn thuốc…</p> : rxError ? <p role="alert" className="text-rose-600">{rxError}</p> : prescription && <div className="space-y-3">{prescription.medications.length ? prescription.medications.map(med => <div key={med.id} className="rounded-xl border border-slate-200 p-4"><p className="font-bold">{med.name}</p><p className="mt-1 text-sm text-slate-500">{med.ingredient} · {med.dose || "Chưa có liều"} · {med.frequency || "Chưa có tần suất"}</p></div>) : <p className="text-sm text-slate-500">Đơn chưa có thuốc.</p>}</div>}</div></section></dialog>}
  </div>;
}
