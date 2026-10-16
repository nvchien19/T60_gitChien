"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { createHistoryLoader } from "@/lib/check-history";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  Bell,
  Bot,
  Check,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  FileText,
  History,
  Home,
  Info,
  Menu,
  MoreHorizontal,
  Pill,
  Plus,
  Search,
  Send,
  Settings,
  ShieldCheck,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
const MedicationAssistantWidget = dynamic(() => import("@/components/MedicationAssistantWidget").then(module => module.MedicationAssistantWidget), { loading: () => <p role="status" className="fixed bottom-5 right-5 rounded-xl bg-white p-4 text-sm shadow-lg">Đang tải trợ lý…</p> });
const PrescriptionEditor = dynamic(() => import("@/components/PrescriptionEditor").then(module => module.PrescriptionEditor), { loading: () => <p role="status" className="p-4 text-sm text-slate-500">Đang tải…</p> });
import type { EditableMedicationDraft } from "@/components/PrescriptionEditor";
import { FoodInteractions } from "@/components/FoodInteractions";
import { ContextFindings } from "@/components/ContextFindings";
import { DuplicateFindings } from "@/components/DuplicateFindings";
import { PatientContextPanel } from "@/components/PatientContextPanel";
const QualityView = dynamic(() => import("@/components/QualityView").then(module => module.QualityView), { loading: () => <p role="status" className="p-4 text-sm text-slate-500">Đang tải…</p> });
import { InteractionExplanation } from "@/components/InteractionExplanation";
import { BrandLogo } from "@/components/BrandLogo";
import { LogoutButton } from "@/components/LogoutButton";
const DoctorReviewPanel = dynamic(() => import("@/components/DoctorWorkspace").then(module => module.DoctorReviewPanel), { loading: () => <p role="status" className="p-4 text-sm text-slate-500">Đang tải…</p> });
import { AuthGate } from "@/components/AuthGate";
import { TermsNotice } from "@/components/TermsNotice";
import type { AuthUser } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

import {
  api,
  loadPrescriptions,
  loadReviews,
  findingsOf,
  dateLabel,
  type CheckRecord,
  type Finding,
  type Prescription,
  type ReviewRequest,
  type Severity,
  type Status,
} from "@/lib/api";

type View =
  | "Tổng quan"
  | "Đơn thuốc"
  | "Kiểm tra an toàn"
  | "Lịch sử"
  | "Yêu cầu trao đổi"
  | "Chất lượng AI";

const allNavItems: { label: View; icon: typeof Home }[] = [
  { label: "Tổng quan", icon: Home },
  { label: "Đơn thuốc", icon: Pill },
  { label: "Kiểm tra an toàn", icon: ClipboardCheck },
  { label: "Lịch sử", icon: History },
  { label: "Yêu cầu trao đổi", icon: Users },
  { label: "Chất lượng AI", icon: BarChart3 },
];

function SeverityBadge({ severity }: { severity: Severity | null }) {
  if (!severity)
    return (
      <span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-500">
        Chưa có
      </span>
    );
  // Không dùng màu xanh lá cho mức nào: dễ bị đọc thành "an toàn".
  const tone = {
    "Chống chỉ định": ["bg-red-700 text-white ring-red-800", "bg-red-100"],
    "Nghiêm trọng": ["bg-rose-50 text-rose-700 ring-rose-200", "bg-rose-500"],
    "Trung bình": ["bg-amber-50 text-amber-700 ring-amber-200", "bg-amber-500"],
    "Nhẹ": ["bg-sky-50 text-sky-800 ring-sky-200", "bg-sky-500"],
  }[severity];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-bold ring-1 ${tone[0]}`}
    >
      <span className={`size-1.5 rounded-full ${tone[1]}`} />
      {severity}
    </span>
  );
}

function StatusBadge({ status }: { status: Status }) {
  const tone =
    status === "Có tương tác"
      ? "bg-rose-50 text-rose-700"
      : status === "Đã kiểm tra"
        ? "bg-emerald-50 text-emerald-700"
        : status === "Cần xem lại"
          ? "bg-amber-50 text-amber-700"
          : "bg-slate-100 text-slate-600";
  return (
    <span className={`rounded-md px-2 py-1 text-[11px] font-bold ${tone}`}>
      {status}
    </span>
  );
}

export default function Page() {
  return <AuthGate>{(user, logout) => <><TermsNotice userId={user.id} /><ClinicalDashboard user={user} onLogout={logout} /></>}</AuthGate>;
}

function ClinicalDashboard({ user, onLogout }: { user: AuthUser; onLogout: () => Promise<void> }) {
  const isDoctor = user.role === "doctor";
  const roleLabel = isDoctor ? "Bác sĩ" : "Dược sĩ";
  const navItems = allNavItems;
  const [active, setActive] = useState<View>("Tổng quan");
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("Tất cả");
  const [showAssistant, setShowAssistant] = useState(false);
  const [assistantLoaded, setAssistantLoaded] = useState(false);
  useEffect(() => { if (showAssistant) setAssistantLoaded(true); }, [showAssistant]);
  const [addMode, setAddMode] = useState<"new" | "append" | null>(null);
  const [checking, setChecking] = useState(false);
  const [checkedId, setCheckedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<number | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [reviewRequests, setReviewRequests] = useState<ReviewRequest[]>([]);
  // Phản hồi của bác sĩ mà dược sĩ đã mở xem, nhớ theo từng tài khoản trên trình duyệt này.
  const seenKey = `seen-review-responses:${user.id}`;
  const [seenResponses, setSeenResponses] = useState<string[]>([]);
  useEffect(() => {
    try { setSeenResponses(JSON.parse(localStorage.getItem(seenKey) || "[]")); } catch { /* không có localStorage */ }
  }, [seenKey]);
  const newResponses = isDoctor ? [] : reviewRequests.filter((r) => r.response && !seenResponses.includes(r.id));
  // Chuông ở góc phải: dược sĩ thấy phản hồi chưa đọc, bác sĩ thấy yêu cầu đang chờ.
  const bellItems = isDoctor
    ? reviewRequests.filter((r) => r.status === "Đang chờ" && r.createdBy !== null)
    : newResponses;
  const reviewBadge = bellItems.length;
  const [bellOpen, setBellOpen] = useState(false);
  const markResponsesSeen = () => {
    const ids = reviewRequests.filter((r) => r.response).map((r) => r.id);
    setSeenResponses(ids);
    try { localStorage.setItem(seenKey, JSON.stringify(ids)); } catch { /* không có localStorage */ }
  };

  const selected =
    prescriptions.find((item) => item.id === selectedId) ?? prescriptions[0];
  const visiblePrescriptions = useMemo(
    () =>
      prescriptions.filter(
        (item) =>
          `${item.id} ${item.name ?? ""} ${item.patient} ${item.medications.map((m) => m.name).join(" ")}`
            .toLowerCase()
            .includes(query.toLowerCase()) &&
          (filter === "Tất cả" ||
            (filter === "Chưa kiểm tra" && item.status === filter) ||
            (filter === "Có tương tác" && item.status === filter) ||
            (filter === "Cần xem lại" && item.status === filter)),
      ),
    [prescriptions, query, filter],
  );

  const [selectedCheckId, setSelectedCheckId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checkRecord, setCheckRecord] = useState<CheckRecord | null>(null);
  const [checkRecords, setCheckRecords] = useState<
    Record<string, CheckRecord[]>
  >({});
  const [historyLoading, setHistoryLoading] = useState(false);
  const [checkLoading, setCheckLoading] = useState(false);
  const historyLoader = useMemo(() => createHistoryLoader<CheckRecord>(async id =>
    (await api<{ items: CheckRecord[] }>(`/prescriptions/${id}/checks`)).items), []);
  const busy = useRef(false);
  const reloadVersion = useRef(0);
  const findings = checkRecord ? findingsOf(checkRecord) : [];

  async function reload() {
    const version = ++reloadVersion.current;
    const rows = await loadPrescriptions();
    if (version !== reloadVersion.current) return;
    historyLoader.clear();
    setCheckRecords({});
    setPrescriptions(rows);
    setSelectedId(id => rows.some(row => row.id === id) ? id : rows[0]?.id || "");
  }
  useEffect(() => {
    let cancelled = false;
    reload().catch(e => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; reloadVersion.current++; };
  }, []);

  // Reviews update independently; they never hold up the prescription overview.
  useEffect(() => {
    let cancelled = false;
    loadReviews().then(rows => { if (!cancelled) setReviewRequests(rows); })
      .catch(e => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (active !== "Kiểm tra an toàn" || !selectedId) return;
    let cancelled = false;
    const version = reloadVersion.current;
    const current = () => !cancelled && version === reloadVersion.current;
    setCheckRecord(null);
    setCheckedId(null);
    setDetail(null);
    setCheckLoading(true);
    (async () => {
      const prescription = prescriptions.find(p => p.id === selectedId);
      if (!prescription) return;
      const records = prescription.checks ? await historyLoader.get(selectedId) : [];
      if (!current()) return;
      setCheckRecords(items => ({ ...items, [selectedId]: records }));
      const latest = selectedCheckId ? records.find(r => r.check_id === selectedCheckId) : records[0];
      if (!latest || (!selectedCheckId && prescription.lastChecked === "Chưa kiểm tra")) return;
      const record = await api<CheckRecord>(`/checks/${latest.check_id}`);
      if (current()) { setCheckRecord(record); setCheckedId(selectedId); }
    })().catch(e => { if (current()) setError(e.message); })
      .finally(() => { if (current()) setCheckLoading(false); });
    return () => { cancelled = true; };
  }, [active, selectedId, selectedCheckId, prescriptions, historyLoader]);

  useEffect(() => {
    if (active !== "Lịch sử") return;
    let cancelled = false;
    const version = reloadVersion.current;
    setHistoryLoading(true);
    historyLoader.all(prescriptions.filter(p => p.checks > 0).map(p => p.id))
      .then(records => { if (!cancelled && version === reloadVersion.current) setCheckRecords(records); })
      .catch(e => { if (!cancelled && version === reloadVersion.current) setError(e.message); })
      .finally(() => { if (!cancelled && version === reloadVersion.current) setHistoryLoading(false); });
    return () => { cancelled = true; };
  }, [active, prescriptions, historyLoader]);

  useEffect(() => {
    const timer = setInterval(() => { loadReviews().then(setReviewRequests).catch(e => setError(e.message)); }, 30000);
    return () => clearInterval(timer);
  }, []);

  const openPrescription = (id: string, checkId = "") => {
    setSelectedCheckId(checkId);
    setSelectedId(id);
    setActive("Kiểm tra an toàn");
  };
  const runCheck = async (id: string) => {
    if (!id || busy.current) return;
    busy.current = true;
    setSelectedCheckId("");
    setError("");
    setSelectedId(id);
    setChecking(true);
    setActive("Kiểm tra an toàn");
    try {
      await api(`/prescriptions/${id}/checks`, {});
      await reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setChecking(false);
      busy.current = false;
    }
  };
  const sendReviewRequest = async (message: string) => {
    if (!selected) throw new Error("Chọn đơn thuốc trước khi gửi yêu cầu.");
    await api("/reviews", {
      prescription_id: selected.id,
      check_id: checkRecord?.check_id || "",
      patient: "",
      message: message.trim() || "Yêu cầu xem xét kết quả kiểm tra an toàn.",
    });
    try {
      setReviewRequests(await loadReviews());
    } catch (e) {
      setError(
        "Đã gửi yêu cầu, nhưng chưa tải lại được danh sách. " +
          (e as Error).message,
      );
    }
  };
  const savePrescription = async (
    name: string,
    drafts: EditableMedicationDraft[],
  ) => {
    const medications = drafts.map((row) => ({
      ...row,
      type: row.type ?? "Kê đơn",
    }));
    let id = selected?.id;
    if (addMode === "new") {
      const created = await api<{ id: string }>("/prescriptions", {
        name,
        medications,
      });
      id = created.id;
    } else {
      if (!id) throw new Error("Chọn đơn thuốc trước khi thêm thuốc.");
      await api(`/prescriptions/${id}/medications`, medications, "PUT");
    }
    setSelectedCheckId("");
    setSelectedId(id || "");
    setCheckRecord(null);
    setCheckedId(null);
    setActive("Kiểm tra an toàn");
    setAddMode(null);
    try {
      await reload();
    } catch (e) {
      setError(
        "Đã lưu, nhưng chưa tải lại được dữ liệu. " + (e as Error).message,
      );
    }
  };

  return (
    <div className="clinical-app min-h-screen overflow-x-clip bg-[#f3f8f7] text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] flex-col border-r border-slate-200 bg-white lg:flex">
        <div className="flex h-[76px] items-center border-b border-slate-100 px-7">
          <BrandLogo size={112} alt="VINMEC" className="h-auto w-28" />
        </div>
        <nav
          className="flex-1 space-y-1 px-3 py-6"
          aria-label="Điều hướng chính"
        >
          {navItems.map(({ label, icon: Icon }) => (
            <button
              key={label}
              onClick={() => setActive(label)}
              className={`flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-[13px] font-semibold transition ${active === label ? "bg-teal-50 text-teal-700" : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"}`}
            >
              <Icon className="size-[17px]" />
              {label}
              {label === "Yêu cầu trao đổi" && reviewBadge > 0 && (
                <span className="ml-auto rounded-full bg-rose-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                  {reviewBadge}
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="space-y-4 border-t border-slate-100 p-4">
          <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-semibold text-slate-500 hover:bg-slate-50">
            <Settings className="size-4" />
            Cài đặt
          </button>
          <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3">
            <div className="flex size-8 items-center justify-center rounded-full bg-teal-100 text-teal-700">
              <UserRound className="size-4" />
            </div>
            <div>
              <p className="text-xs font-bold text-slate-700">{user.name}</p>
              <p className="text-[10px] text-slate-400">{roleLabel}</p>
            </div>

          </div>
          <LogoutButton onLogout={onLogout} onError={setError} className="w-full border border-slate-200" />
        </div>
      </aside>
      <main className="min-h-screen lg:pl-[248px]">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-2 border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:h-[76px] sm:px-8">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <BrandLogo size={44} alt="VINMEC" className="h-auto w-11 lg:hidden" />
            <button
              onClick={() => setMobileNav(true)}
              aria-label="Mở menu"
              aria-expanded={mobileNav}
              className="-ml-1 min-h-[44px] min-w-[44px] rounded-lg p-2.5 text-slate-500 transition hover:bg-slate-100 active:bg-slate-200 lg:hidden"
            >
              <Menu className="size-5" />
            </button>
            <div className="min-w-0">
              <p className="hidden truncate text-xs font-medium text-slate-400 min-[400px]:block">
                Xin chào, {user.name}
              </p>
              <h1 className="truncate text-base font-extrabold sm:text-lg">
                {active}
              </h1>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-4">
            <LogoutButton onLogout={onLogout} onError={setError} compact className="lg:hidden" />
            <ThemeToggle compact />
            <div className="relative">
              <button
                onClick={() => setBellOpen((open) => !open)}
                aria-label={reviewBadge > 0 ? `Thông báo: ${reviewBadge} mục mới` : "Thông báo"}
                aria-expanded={bellOpen}
                className="relative flex min-h-[40px] min-w-[40px] items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100"
              >
                <Bell className="size-[18px]" />
                {reviewBadge > 0 && (
                  <span className="absolute right-0.5 top-0.5 rounded-full bg-rose-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                    {reviewBadge}
                  </span>
                )}
              </button>
              {bellOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setBellOpen(false)} />
                  <div className="absolute right-0 top-full z-50 mt-2 w-[320px] max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white shadow-lg">
                    <p className="border-b border-slate-100 px-4 py-3 text-sm font-extrabold">Thông báo</p>
                    {bellItems.length === 0 ? (
                      <p className="px-4 py-6 text-center text-xs text-slate-500">Không có thông báo mới.</p>
                    ) : (
                      <ul className="max-h-[320px] overflow-y-auto">
                        {bellItems.map((r) => (
                          <li key={r.id}>
                            <button
                              onClick={() => { setBellOpen(false); setActive("Yêu cầu trao đổi"); }}
                              className="block w-full border-b border-slate-100 px-4 py-3 text-left hover:bg-slate-50"
                            >
                              <p className="text-xs font-bold text-slate-800">
                                {isDoctor
                                  ? `${r.creatorName || "Dược sĩ"} gửi yêu cầu trao đổi về đơn ${r.prescriptionId}`
                                  : `${r.responderName || "Bác sĩ"} đã phản hồi yêu cầu về đơn ${r.prescriptionId}`}
                              </p>
                              <p className="mt-1 line-clamp-2 text-xs text-slate-500">{isDoctor ? r.message : r.response}</p>
                              <p className="mt-1 text-[10px] text-slate-400">{isDoctor ? r.date : r.respondedAt}</p>
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                    {!isDoctor && newResponses.length > 0 && (
                      <button
                        onClick={() => { markResponsesSeen(); setBellOpen(false); }}
                        className="w-full px-4 py-3 text-xs font-bold text-teal-600 hover:bg-slate-50"
                      >
                        Đánh dấu đã đọc
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
            <div className="flex size-8 items-center justify-center rounded-full bg-teal-100 text-xs font-bold text-teal-700 sm:size-9 sm:text-sm">
              {user.name.trim().split(/\s+/).slice(-2).map(part => part[0]).join("").toUpperCase()}
            </div>
          </div>
        </header>
        <div className="mx-auto max-w-[1280px] space-y-6 p-4 pb-28 sm:space-y-7 sm:p-8 sm:pb-8 xl:p-10">
          {loading && (
            <p role="status" className="rounded-xl bg-white p-5 text-sm">
              Đang tải đơn thuốc…
            </p>
          )}
          {newResponses.length > 0 && active !== "Yêu cầu trao đổi" && (
            <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
              <span>
                Bác sĩ đã phản hồi <b>{newResponses.length}</b> yêu cầu trao đổi của bạn
                {" "}(đơn {[...new Set(newResponses.map((r) => r.prescriptionId))].join(", ")}).
              </span>
              <button onClick={() => setActive("Yêu cầu trao đổi")} className="min-h-[40px] rounded-md bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-700">
                Xem phản hồi
              </button>
            </div>
          )}
          {error && (
            <div
              role="alert"
              className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
            >
              {error}
              <button
                onClick={() => {
                  setLoading(true);
                  setError("");
                  reload()
                    .catch((e) => setError(e.message))
                    .finally(() => setLoading(false));
                }}
                className="ml-3 font-bold underline"
              >
                Thử lại
              </button>
            </div>
          )}
          {!loading && !error && prescriptions.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
              <p>Chưa có đơn thuốc. Thêm đơn để bắt đầu.</p>
              <Button
                onClick={() => setAddMode("new")}
                className="mt-4 bg-teal-500"
              >
                Thêm đơn thuốc
              </Button>
            </div>
          )}
          {active === "Tổng quan" && (
            <Overview
              prescriptions={prescriptions}
              onOpen={() => setActive("Đơn thuốc")}
              onCheck={() => runCheck(selectedId)}
            />
          )}
          {active === "Đơn thuốc" && (
            <Library
              items={visiblePrescriptions}
              query={query}
              setQuery={setQuery}
              filter={filter}
              setFilter={setFilter}
              onOpen={openPrescription}
              onCheck={runCheck}
              onAdd={() => setAddMode("new")}
            />
          )}
          {active === "Kiểm tra an toàn" && selected && (checkLoading ? <p role="status" className="p-4 text-sm text-slate-500">Đang tải kết quả kiểm tra…</p> :
            <SafetyView
              prescription={selected}
              checking={checking}
              checked={checkedId === selected.id}
              findings={findings}
              checkRecord={checkRecord}
              onBack={() => setActive("Đơn thuốc")}
              onCheck={() => runCheck(selected.id)}
              onAdd={() => setAddMode("append")}
              onDetail={setDetail}
              canSendReview={!isDoctor}
              onSendReview={sendReviewRequest}
              onViewRequests={() => setActive("Yêu cầu trao đổi")}
              onContextSaved={reload}
            />
          )}
          {active === "Lịch sử" && (historyLoading ? <p role="status" className="p-4 text-sm text-slate-500">Đang tải lịch sử kiểm tra…</p> :
            <HistoryView
              records={checkRecords}
              prescriptions={prescriptions}
              onView={openPrescription}
            />
          )}
          {active === "Yêu cầu trao đổi" && isDoctor && <DoctorReviewPanel />}
          {active === "Chất lượng AI" && <QualityView />}
          {active === "Yêu cầu trao đổi" && !isDoctor && (
            <ReviewView
              requests={reviewRequests}
              newIds={newResponses.map((r) => r.id)}
              onSeen={markResponsesSeen}
              onNew={() => setActive("Kiểm tra an toàn")}
              onView={openPrescription}
            />
          )}
        </div>
      </main>
      {assistantLoaded || showAssistant ? <MedicationAssistantWidget
        key={selected?.id}
        prescriptionId={selected?.id || "chưa chọn"}
        checkId={checkRecord?.check_id}
        open={showAssistant}
        onOpen={() => setShowAssistant(true)}
        onClose={() => setShowAssistant(false)}
        onSaved={reload}
        onView={openPrescription}
      /> : <button type="button" onClick={() => setShowAssistant(true)} aria-label="Mở trợ lý An toàn Thuốc" className="fixed bottom-24 right-4 z-[9999] flex min-h-[48px] items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-xs font-bold text-white shadow-lg hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-500 sm:right-5 lg:bottom-7 lg:right-8"><Bot className="size-4" /> Hỏi trợ lý</button>}
      <nav
        aria-label="Điều hướng di động"
        className="fixed inset-x-0 bottom-0 z-30 flex border-t border-slate-200 bg-white/95 px-1 pb-[calc(env(safe-area-inset-bottom)+6px)] pt-1.5 backdrop-blur lg:hidden"
      >
        {navItems.map(({ label, icon: Icon }) => {
          const short =
            label === "Kiểm tra an toàn"
              ? "Kiểm tra"
              : label === "Yêu cầu trao đổi"
                ? "Trao đổi"
                : label === "Chất lượng AI"
                  ? "Chất lượng"
                  : label;
          const badge =
            label === "Kiểm tra an toàn"
              ? prescriptions.filter((p) => p.status === "Có tương tác").length
              : label === "Yêu cầu trao đổi"
                ? reviewBadge
                : 0;
          const isActive = active === label;
          return (
            <button
              key={label}
              onClick={() => setActive(label)}
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-[54px] min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-1 text-[9px] font-bold transition ${isActive ? "text-teal-600" : "text-slate-400 active:text-slate-600"}`}
            >
              <span className="relative">
                <Icon className="size-5" />
                {badge > 0 && (
                  <span className="absolute -right-2.5 -top-1.5 flex min-h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[9px] font-bold leading-none text-white">
                    {badge}
                  </span>
                )}
              </span>
              <span className="max-w-full truncate">{short}</span>
              {isActive && <span className="h-1 w-8 rounded-full bg-teal-500" />}
            </button>
          );
        })}
      </nav>
      {mobileNav && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Đóng menu"
            onClick={() => setMobileNav(false)}
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-[2px]"
          />
          <div className="absolute inset-y-0 left-0 flex w-[280px] max-w-[85vw] flex-col bg-white shadow-2xl animate-in slide-in-from-left duration-200">
            <div className="flex h-16 items-center justify-between border-b border-slate-100 px-4">
              <BrandLogo size={96} alt="VINMEC" className="h-auto w-24" />
              <button
                onClick={() => setMobileNav(false)}
                aria-label="Đóng menu"
                className="min-h-[44px] min-w-[44px] rounded-lg p-2.5 text-slate-500 hover:bg-slate-100"
              >
                <X className="size-5" />
              </button>
            </div>
            <nav
              className="flex-1 space-y-1 overflow-y-auto px-3 py-4"
              aria-label="Điều hướng chính"
            >
              {navItems.map(({ label, icon: Icon }) => (
                <button
                  key={label}
                  onClick={() => {
                    setActive(label);
                    setMobileNav(false);
                  }}
                  aria-current={active === label ? "page" : undefined}
                  className={`flex min-h-[48px] w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-semibold transition ${active === label ? "bg-teal-50 text-teal-700" : "text-slate-500 active:bg-slate-100"}`}
                >
                  <Icon className="size-[18px]" />
                  {label}
                  {label === "Yêu cầu trao đổi" && reviewBadge > 0 && (
                      <span className="ml-auto rounded-full bg-rose-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                        {reviewBadge}
                      </span>
                    )}
                </button>
              ))}
            </nav>
            <div className="border-t border-slate-100 p-4">
              <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3">
                <div className="flex size-8 items-center justify-center rounded-full bg-teal-100 text-teal-700">
                  <UserRound className="size-4" />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-700">{user.name}</p>
                  <p className="text-[10px] text-slate-400">
                    {roleLabel}
                  </p>
                </div>
              </div>
              <LogoutButton onLogout={onLogout} onError={setError} className="mt-3 w-full border border-slate-200" />
            </div>
          </div>
        </div>
      )}
      {addMode && (
        <PrescriptionEditor
          initialName={
            addMode === "append" ? selected?.name || selected?.id : ""
          }
          existingMedications={
            addMode === "append" ? (selected?.medications ?? []) : []
          }
          onClose={() => setAddMode(null)}
          onSave={savePrescription}
        />
      )}
      {detail !== null && findings[detail] && (
        <InteractionModal
          item={findings[detail]}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  );
}

function Overview({
  prescriptions,
  onOpen,
  onCheck,
}: {
  prescriptions: Prescription[];
  onOpen: () => void;
  onCheck: () => void;
}) {
  return (
    <>
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-teal-600">
            Dữ liệu từ hệ thống
          </p>
          <h2 className="text-xl font-extrabold tracking-tight sm:text-[28px]">
            Quản lý an toàn thuốc
          </h2>
          <p className="mt-1.5 text-sm text-slate-500">
            Theo dõi đơn thuốc, kiểm tra tương tác và lưu lại kết quả.
          </p>
        </div>
        <Button
          disabled={!prescriptions.length}
          onClick={onCheck}
          className="h-11 w-full justify-center gap-2 rounded-lg bg-teal-500 px-5 font-bold hover:bg-teal-600 sm:w-auto"
        >
          <ClipboardCheck className="size-4" /> Kiểm tra an toàn
        </Button>
      </section>
      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {(
          [
            ["Đơn thuốc", prescriptions.length, "Đang quản lý", Pill],
            [
              "Đã kiểm tra",
              prescriptions.filter((p) => p.checks > 0).length,
              "Lịch sử đã lưu",
              History,
            ],
            [
              "Có tương tác",
              prescriptions.filter((p) => p.status === "Có tương tác").length,
              "Cần xem xét",
              AlertCircle,
            ],
            [
              "Cần xác minh",
              prescriptions.reduce(
                (n, p) => n + p.medications.filter((m) => !m.verified).length,
                0,
              ),
              "Thông tin chưa đủ",
              Info,
            ],
          ] as const
        ).map(([title, value, sub, Icon]) => (
          <div
            key={String(title)}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(15,23,42,0.03)] sm:p-5"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500">{title}</p>
                <p className="mt-2 text-xl font-extrabold sm:mt-3 sm:text-2xl">
                  {value}
                </p>
                <p className="mt-1 text-[11px] text-slate-400">{sub}</p>
              </div>
              <div className="flex size-9 items-center justify-center rounded-lg bg-teal-50 text-teal-600">
                <Icon className="size-[18px]" />
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-7 xl:grid-cols-[1.45fr_1fr]">
        <section className="rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4 sm:px-5">
            <div>
              <h3 className="text-sm font-extrabold">Đơn thuốc gần đây</h3>
              <p className="mt-0.5 text-xs text-slate-400">
                Mở đơn để xem thuốc và kết quả
              </p>
            </div>
            <button onClick={onOpen} className="text-xs font-bold text-teal-600">
              Xem tất cả
            </button>
          </div>
          {prescriptions.slice(0, 5).map((p) => (
            <button
              key={p.id}
              onClick={onOpen}
              className="flex w-full items-center gap-4 border-b border-slate-100 px-4 py-4 sm:px-5 text-left last:border-0 hover:bg-slate-50"
            >
              <div className="flex size-10 items-center justify-center rounded-lg bg-teal-50 text-teal-600">
                <FileText className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold">
                  {p.name || p.id} · {p.patient}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {p.medications.length} thuốc · {p.lastChecked}
                </p>
              </div>
              <StatusBadge status={p.status} />
              <ChevronRight className="size-4 text-slate-300" />
            </button>
          ))}
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg bg-teal-50 text-teal-600">
              <ShieldCheck className="size-5" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold">Quy trình an toàn</h3>
              <p className="text-xs text-slate-400">
                Từ đơn thuốc đến bằng chứng
              </p>
            </div>
          </div>
          <div className="mt-6 space-y-4">
            {[
              "Chọn đơn thuốc",
              "Xem lại danh sách thuốc",
              "Chạy kiểm tra tương tác",
              "Xem kết quả và bằng chứng",
            ].map((step, i) => (
              <div
                key={step}
                className="flex items-center gap-3 text-xs font-semibold text-slate-600"
              >
                <span className="flex size-7 items-center justify-center rounded-full bg-teal-50 text-teal-600">
                  {i + 1}
                </span>
                {step}
              </div>
            ))}
          </div>
        </section>
      </div>
      <div className="flex gap-3 rounded-xl border border-teal-600 bg-teal-600 p-4 text-xs leading-relaxed text-white">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-white" />
        <p>
          <strong>Lưu ý an toàn:</strong> Đây là công cụ hỗ trợ quyết định,
          không thay thế tư vấn y tế. Không tự ý thay đổi thuốc.
        </p>
      </div>
    </>
  );
}

function Library({
  items,
  query,
  setQuery,
  filter,
  setFilter,
  onOpen,
  onCheck,
  onAdd,
}: {
  items: Prescription[];
  query: string;
  setQuery: (v: string) => void;
  filter: string;
  setFilter: (v: string) => void;
  onOpen: (id: string) => void;
  onCheck: (id: string) => void;
  onAdd: () => void;
}) {
  return (
    <>
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-teal-600">
            Prescription management
          </p>
          <h2 className="text-xl font-extrabold tracking-tight sm:text-2xl">
            Thư viện đơn thuốc
          </h2>
          <p className="mt-1.5 text-sm text-slate-500">
            Quản lý đơn thuốc và kiểm tra các tương tác tiềm ẩn.
          </p>
        </div>
        <Button
          onClick={onAdd}
          className="w-full justify-center gap-2 rounded-lg bg-teal-500 font-bold hover:bg-teal-600 sm:w-auto"
        >
          <Plus className="size-4" /> Thêm đơn thuốc
        </Button>
      </section>
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row">
        <div className="flex flex-1 items-center gap-2 rounded-lg border border-slate-200 px-3">
          <Search className="size-4 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm tên đơn, mã đơn, bệnh nhân hoặc thuốc..."
            className="h-11 flex-1 text-sm outline-none"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto">
          {["Tất cả", "Chưa kiểm tra", "Có tương tác", "Cần xem lại"].map(
            (item) => (
              <button
                key={item}
                onClick={() => setFilter(item)}
                className={`min-h-[40px] whitespace-nowrap rounded-lg px-4 py-2.5 text-xs font-bold transition active:scale-[0.98] ${filter === item ? "bg-teal-500 text-white" : "bg-slate-50 text-slate-500"}`}
              >
                {item}
              </button>
            ),
          )}
        </div>
      </div>
      <div className="hidden overflow-hidden rounded-xl border border-slate-200 bg-white md:block">
        <table className="w-full text-left">
          <thead className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold uppercase tracking-wide text-slate-400">
            <tr>
              <th className="px-5 py-4">Đơn thuốc</th>
              <th>Ngày tạo</th>
              <th>Số thuốc</th>
              <th>Kiểm tra gần nhất</th>
              <th>Trạng thái</th>
              <th>Mức độ</th>
              <th className="px-5">Thao tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((p) => (
              <tr key={p.id} className="text-xs">
                <td className="px-5 py-4">
                  <button onClick={() => onOpen(p.id)} className="text-left">
                    <p className="font-extrabold text-slate-800">
                      {p.name || p.id}
                    </p>
                    <p className="mt-1 break-all font-mono text-[11px] text-teal-700">
                      Mã đơn: {p.id}
                    </p>
                    <p className="mt-1 text-slate-400">{p.patient}</p>
                  </button>
                </td>
                <td className="text-slate-500">{p.date}</td>
                <td className="text-slate-500">{p.medications.length} thuốc</td>
                <td className="text-slate-500">{p.lastChecked}</td>
                <td>
                  <StatusBadge status={p.status} />
                </td>
                <td>
                  <SeverityBadge severity={p.highest} />
                </td>
                <td className="px-5">
                  <div className="flex gap-2">
                    <button
                      onClick={() => onOpen(p.id)}
                      className="rounded-md border border-slate-200 px-2.5 py-1.5 font-bold text-slate-600"
                    >
                      Mở
                    </button>
                    <button
                      onClick={() => onCheck(p.id)}
                      className="rounded-md bg-teal-50 px-2.5 py-1.5 font-bold text-teal-700"
                    >
                      Kiểm tra
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="space-y-3 md:hidden">
        {items.map((p) => (
          <div
            key={p.id}
            className="rounded-xl border border-slate-200 bg-white p-4"
          >
            <div className="flex items-start justify-between">
              <div>
                <button
                  onClick={() => onOpen(p.id)}
                  className="text-sm font-extrabold"
                >
                  {p.name || p.id}
                </button>
                <p className="mt-1 break-all font-mono text-[11px] text-teal-700">
                  Mã đơn: {p.id}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {p.patient} · {p.medications.length} thuốc
                </p>
              </div>
              <StatusBadge status={p.status} />
            </div>
            <div className="mt-4 flex items-center justify-between">
              <SeverityBadge severity={p.highest} />
              <button
                onClick={() => onCheck(p.id)}
                className="min-h-[40px] rounded-md bg-teal-500 px-4 py-2 text-xs font-bold text-white active:bg-teal-600"
              >
                Kiểm tra
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function SafetyView({
  prescription,
  checking,
  checked,
  findings,
  checkRecord,
  onBack,
  onCheck,
  onAdd,
  onDetail,
  canSendReview,
  onSendReview,
  onViewRequests,
  onContextSaved,
}: {
  prescription: Prescription;
  checking: boolean;
  checked: boolean;
  findings: Finding[];
  checkRecord: CheckRecord | null;
  onBack: () => void;
  onCheck: () => void;
  onAdd: () => void;
  onDetail: (id: number) => void;
  canSendReview: boolean;
  onSendReview: (message: string) => Promise<void>;
  onViewRequests: () => void;
  onContextSaved: () => Promise<void>;
}) {
  return (
    <>
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-xs font-bold text-slate-500 hover:text-teal-600"
      >
        <ArrowLeft className="size-4" /> Quay lại thư viện
      </button>
      {checking ? (
        <Analysis prescription={prescription} />
      ) : (
        <>
          <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-teal-600">
                Prescription detail
              </p>
              <h2 className="break-words text-xl font-extrabold sm:text-2xl">
                {prescription.name || prescription.id}{" "}
                <span className="font-normal text-slate-300">/</span>{" "}
                {prescription.patient}
              </h2>
              <p className="mt-1.5 text-sm text-slate-500">
                {prescription.id} · Ngày tạo {prescription.date} ·{" "}
                {prescription.medications.length} thuốc
              </p>
            </div>
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
              <Button
                variant="outline"
                onClick={onAdd}
                className="w-full justify-center gap-2 rounded-lg font-bold sm:w-auto"
              >
                <Plus className="size-4" /> Thêm thuốc
              </Button>
            </div>
          </section>
          <section className="rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4 sm:px-5">
              <div>
                <h3 className="text-sm font-extrabold">Thuốc trong đơn</h3>
                <p className="mt-1 text-xs text-slate-400">
                  Rà soát trước khi chạy kiểm tra
                </p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold text-slate-500">
                {prescription.medications.length} mục
              </span>
            </div>
            <div className="divide-y divide-slate-100">
              {prescription.medications.map((med) => (
                <div
                  key={med.id}
                  className="flex items-center gap-3 px-4 py-4 sm:gap-4 sm:px-5"
                >
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-600">
                    <Pill className="size-[18px]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-bold">{med.name}</p>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500">
                        {med.type}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {med.ingredient}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {med.dose} · {med.frequency}
                    </p>
                  </div>
                  {med.verified ? (
                    <span className="rounded-md bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700 shrink-0 whitespace-nowrap">
                      Đã xác minh
                    </span>
                  ) : (
                    <span className="rounded-md bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700 shrink-0 whitespace-nowrap">
                      Cần xác minh
                    </span>
                  )}
                </div>
              ))}
            </div>
          </section>
          <PatientContextPanel
            prescriptionId={prescription.id}
            value={prescription.context}
            onSaved={onContextSaved}
          />
          <div className="flex justify-end">
            <Button
              disabled={prescription.medications.length === 0}
              onClick={onCheck}
              className="w-full justify-center gap-2 rounded-lg bg-teal-500 font-bold hover:bg-teal-600 sm:w-auto"
            >
              <ClipboardCheck className="size-4" /> Kiểm tra tương tác
            </Button>
          </div>
          {checked && (
            <Results
              key={checkRecord?.check_id ?? prescription.id}
              findings={findings}
              checkRecord={checkRecord}
              onDetail={onDetail}
              prescription={prescription}
              canSendReview={canSendReview}
            />
          )}
          {canSendReview && <DoctorRequestForm
            key={prescription.id}
            prescription={prescription}
            onSend={onSendReview}
            onViewRequests={onViewRequests}
          />}
        </>
      )}
    </>
  );
}

function Analysis({ prescription }: { prescription: Prescription }) {
  return (
    <section
      role="status"
      className="rounded-xl border border-slate-200 bg-white p-8 text-center"
    >
      <ShieldCheck className="mx-auto size-8 animate-pulse text-teal-500" />
      <h2 className="mt-4 text-xl font-bold">
        Đang kiểm tra đơn {prescription.id}
      </h2>
      <p className="mt-2 text-sm text-slate-500">
        Đang chờ kết quả từ hệ thống.
      </p>
    </section>
  );
}

function Results({
  prescription,
  onDetail,
  findings,
  checkRecord,
  canSendReview,
}: {
  prescription: Prescription;
  onDetail: (id: number) => void;
  findings: Finding[];
  checkRecord: CheckRecord | null;
  canSendReview: boolean;
}) {
  const [severityFilter, setSeverityFilter] = useState<Severity | "Chưa có" | "Tất cả">("Tất cả");
  const severityOptions: { value: Severity | "Chưa có"; count: number }[] =
    (["Chống chỉ định", "Nghiêm trọng", "Trung bình", "Nhẹ"] as Severity[])
      .map((value) => ({ value, count: findings.filter((item) => item.severity === value).length }))
      .filter((option) => option.count > 0);
  const unclassifiedCount = findings.filter((item) => item.severity === null).length;
  if (unclassifiedCount) severityOptions.push({ value: "Chưa có", count: unclassifiedCount });
  const visibleFindings = findings.filter((item) =>
    severityFilter === "Tất cả" ||
    (severityFilter === "Chưa có" ? item.severity === null : item.severity === severityFilter),
  );

  return (
    <section className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-teal-600">
              Safety check · {prescription.id}
            </p>
            <h3 className="mt-1 text-xl font-extrabold">
              Kết quả kiểm tra an toàn
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              {checkRecord?.check_id} · {dateLabel(checkRecord?.created_at)}
            </p>
          </div>
          {canSendReview && <button
            onClick={() =>
              document
                .getElementById("doctor-form")
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
            className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 hover:border-teal-300 hover:text-teal-700"
          >
            Yêu cầu bác sĩ xem
          </button>}
        </div>
        <div className="mt-5 grid grid-cols-2 gap-2 sm:gap-3 lg:grid-cols-4">
          {[
            ["Thuốc đã kiểm tra", checkRecord?.summary?.meds_count || 0],
            ["Tương tác thuốc–thuốc", findings.length],
            [
              "Mức độ cao nhất",
              findings.find((f) => f.severity)?.severity || "Chưa có",
            ],
            [
              "Nguồn bằng chứng",
              new Set(
                findings.flatMap((f) => f.citations.map((c) => c.source_id)),
              ).size,
            ],
          ].map(([label, value]) => (
            <div
              key={String(label)}
              className="rounded-lg bg-slate-50 p-3 sm:p-4"
            >
              <p className="truncate text-[11px] font-semibold text-slate-500">
                {label}
              </p>
              <p className="mt-2 text-lg font-extrabold">{value}</p>
            </div>
          ))}
        </div>
      </div>
      {checkRecord?.disclaimer && (
        <div role="note" className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-900">
          <ShieldCheck className="mt-0.5 size-4 shrink-0" />
          <p>
            <strong>Lưu ý:</strong> {checkRecord.disclaimer} Mức độ hiển thị đúng như nguồn dữ liệu ghi;
            &quot;chưa có bản ghi&quot; không có nghĩa là an toàn.
          </p>
        </div>
      )}
      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-4 py-4 sm:px-5">
          <h3 className="text-sm font-extrabold">Tương tác thuốc–thuốc theo mức độ</h3>
          <p className="mt-1 text-xs text-slate-400">
            Kết quả dựa trên nguồn dữ liệu hiện tại, không đảm bảo an toàn tuyệt
            đối.
          </p>
        </div>
        {findings.length > 0 && (
          <div role="group" aria-label="Lọc tương tác theo mức độ" className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3 sm:px-5">
            <span className="mr-1 text-xs font-semibold text-slate-600">Lọc mức độ:</span>
            {([{ value: "Tất cả", count: findings.length }, ...severityOptions] as const).map(({ value, count }) => (
              <button
                key={value}
                type="button"
                aria-pressed={severityFilter === value}
                onClick={() => setSeverityFilter(value)}
                className={`rounded-full border px-3 py-1.5 text-xs font-bold transition focus-visible:outline-2 focus-visible:outline-teal-500 ${severityFilter === value ? "border-teal-500 bg-teal-500 text-white" : "border-slate-200 bg-white text-slate-600 hover:border-teal-300"}`}
              >
                {value} ({count})
              </button>
            ))}
          </div>
        )}
        <div className="space-y-3 p-5">
          {findings.length === 0 && (
            <p className="text-sm text-slate-500">
              Chưa có bản ghi tương tác trong nguồn dữ liệu hiện tại.
            </p>
          )}
          {!!checkRecord?.unknown?.length && (
            <p className="text-sm text-amber-700">
              Có thuốc chưa được xác minh. Hãy kiểm tra lại tên thuốc và trao
              đổi với dược sĩ.
            </p>
          )}
          {visibleFindings.map((item) => (
            <button
              key={item.id}
              onClick={() => onDetail(item.id)}
              className="flex w-full items-center gap-4 rounded-xl border border-slate-200 p-4 text-left transition hover:border-teal-300 hover:shadow-sm"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-extrabold">
                    {item.a}{" "}
                    <span className="font-normal text-slate-300">↕</span>{" "}
                    {item.b}
                  </p>
                  <SeverityBadge severity={item.severity} />
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {item.kind} · {item.text}
                </p>
                <p className="mt-2 text-[11px] font-semibold text-slate-400">
                  {item.sources} nguồn bằng chứng
                </p>
                {item.untranslatedFields.length > 0 && (
                  <p className="mt-1 text-[11px] text-amber-700">
                    Một số nội dung chưa có bản dịch tiếng Việt; đang hiển thị
                    nguyên văn.
                  </p>
                )}
                {item.machineTranslation && (
                  <p className="mt-1 text-[11px] text-slate-500">
                    Bản dịch tự động, chưa được rà soát chuyên môn.
                  </p>
                )}
              </div>
              <ChevronRight className="size-4 shrink-0 text-slate-300" />
            </button>
          ))}
        </div>
      </div>
    <DuplicateFindings record={checkRecord} />
    <ContextFindings key={`context-${checkRecord?.check_id}`} record={checkRecord} />
    <FoodInteractions key={checkRecord?.check_id} record={checkRecord} />
      </section>
  );
}

function HistoryView({
  prescriptions,
  records,
  onView,
}: {
  prescriptions: Prescription[];
  records: Record<string, CheckRecord[]>;
  onView: (id: string, checkId?: string) => void;
}) {
  return (
    <>
      <h2 className="text-xl font-bold">Lịch sử kiểm tra</h2>
      <div className="space-y-3">
        {prescriptions.flatMap((p) =>
          (records[p.id] || []).map((record) => (
            <div
              key={record.check_id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-5"
            >
              <div>
                <p className="font-bold">{record.check_id}</p>
                <p className="mt-2 text-xs text-slate-500">
                  {p.name || p.id} · {dateLabel(record.created_at)} ·{" "}
                  {record.summary?.meds_count || 0} thuốc ·{" "}
                  {record.summary?.findings_count || 0} phát hiện
                </p>
              </div>
              <button
                onClick={() => onView(p.id, record.check_id)}
                className="rounded-lg bg-teal-50 px-4 py-2 text-xs font-bold text-teal-700"
              >
                Xem kết quả
              </button>
            </div>
          )),
        )}
      </div>
      {Object.values(records).every((rows) => !rows.length) && (
        <p className="text-sm text-slate-500">Chưa có lần kiểm tra nào.</p>
      )}
    </>
  );
}

function DoctorRequestForm({
  prescription,
  onSend,
  onViewRequests,
}: {
  prescription: Prescription;
  onSend: (message: string) => Promise<void>;
  onViewRequests: () => void;
}) {
  const [message, setMessage] = useState("");
  const [justSent, setJustSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const handleSend = async () => {
    if (sending) return;
    setSending(true);
    setSendError("");
    try {
      await onSend(message);
      setJustSent(true);
      setMessage("");
    } catch (e) {
      setSendError((e as Error).message);
    } finally {
      setSending(false);
    }
  };
  return (
    <section
      id="doctor-form"
      className="scroll-mt-20 rounded-xl border border-slate-200 bg-white p-4 sm:p-6"
    >
      <div className="flex items-center gap-3">
        <div className="flex size-11 items-center justify-center rounded-xl bg-teal-50 text-teal-600">
          <Users className="size-5" />
        </div>
        <div>
          <h3 className="text-sm font-extrabold">
            Yêu cầu trao đổi · {prescription.id}
          </h3>
          <p className="mt-0.5 text-xs text-slate-400">
            {prescription.medications.length} thuốc · {prescription.status} ·{" "}
            {prescription.patient}
          </p>
        </div>
      </div>
      {justSent ? (
        <div className="mt-6 space-y-3">
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">
            Đã gửi yêu cầu. Trạng thái: Đang chờ bác sĩ xem xét. Yêu cầu của bạn
            đã được chuyển sang mục Trao đổi với bác sĩ.
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <Button
              onClick={() => setJustSent(false)}
              variant="outline"
              className="w-full justify-center font-bold sm:w-auto"
            >
              Gửi yêu cầu khác
            </Button>
            <Button
              onClick={onViewRequests}
              className="w-full justify-center bg-teal-500 font-bold hover:bg-teal-600 sm:w-auto"
            >
              Xem yêu cầu đã gửi
            </Button>
          </div>
        </div>
      ) : (
        <>
          {sendError && (
            <p role="alert" className="mt-4 text-sm text-rose-600">
              {sendError}
            </p>
          )}
          <label
            htmlFor="doctor-message"
            className="mt-6 block text-xs font-bold"
          >
            Tin nhắn cho bác sĩ
          </label>
          <textarea
            id="doctor-message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Tôi muốn được hỗ trợ hiểu các phát hiện này..."
            className="mt-2 min-h-32 w-full rounded-lg border border-slate-200 p-3 text-sm outline-none focus:border-teal-400"
          />
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button
              disabled={sending}
              onClick={handleSend}
              className="w-full justify-center gap-2 bg-teal-500 font-bold hover:bg-teal-600 sm:w-auto"
            >
              <Send className="size-4" /> Gửi yêu cầu tới bác sĩ
            </Button>
            <span className="text-[11px] text-slate-400">
              Yêu cầu sẽ hiển thị trong mục Trao đổi với bác sĩ.
            </span>
          </div>
        </>
      )}
    </section>
  );
}

function ReviewView({
  requests,
  newIds,
  onSeen,
  onNew,
  onView,
}: {
  requests: ReviewRequest[];
  newIds: string[];
  onSeen: () => void;
  onNew: () => void;
  onView: (id: string) => void;
}) {
  const waiting = requests.filter((r) => r.status === "Đang chờ").length;
  return (
    <>
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-teal-600">
            Professional review
          </p>
          <h2 className="text-xl font-extrabold tracking-tight sm:text-2xl">
            Yêu cầu trao đổi
          </h2>
          <p className="mt-1.5 text-sm text-slate-500">
            Các yêu cầu bạn đã gửi từ form dưới phần kiểm tra an toàn.
          </p>
        </div>
        <Button
          onClick={onNew}
          className="gap-2 rounded-lg bg-teal-500 font-bold hover:bg-teal-600"
        >
          <Plus className="size-4" /> Tạo yêu cầu mới
        </Button>
      </section>
      <div className="grid grid-cols-3 gap-2 sm:gap-4">
        {(
          [
            ["Tổng yêu cầu", requests.length],
            ["Đang chờ", waiting],
            ["Đã phản hồi", requests.length - waiting],
          ] as const
        ).map(([label, value]) => (
          <div
            key={String(label)}
            className="rounded-xl border border-slate-200 bg-white p-3 sm:p-5"
          >
            <p className="truncate text-[11px] font-semibold text-slate-500 sm:text-xs">
              {label}
            </p>
            <p className="mt-1 text-lg font-extrabold sm:mt-2 sm:text-2xl">
              {value}
            </p>
          </div>
        ))}
      </div>
      {requests.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-xl bg-teal-50 text-teal-600">
            <Users className="size-5" />
          </div>
          <h3 className="mt-4 text-sm font-extrabold">Chưa có yêu cầu nào</h3>
          <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-slate-500">
            Mở một đơn trong Kiểm tra an toàn, kéo xuống form Trao đổi với bác
            sĩ ở phía dưới và gửi yêu cầu. Yêu cầu sẽ hiển thị tại đây.
          </p>
          <Button
            onClick={onNew}
            className="mt-5 bg-teal-500 font-bold hover:bg-teal-600"
          >
            Đi tới kiểm tra an toàn
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {newIds.length > 0 && (
            <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
              <span>Có <b>{newIds.length}</b> phản hồi mới từ bác sĩ.</span>
              <button onClick={onSeen} className="min-h-[40px] rounded-md bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-700">
                Đánh dấu đã đọc
              </button>
            </div>
          )}
          {requests.map((req) => (
            <div
              key={req.id}
              className="rounded-xl border border-slate-200 bg-white p-5"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-extrabold">{req.id}</p>
                    <span
                      className={`rounded-md px-2 py-1 text-[11px] font-bold ${req.status === "Đang chờ" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}
                    >
                      {req.status}
                    </span>
                    {newIds.includes(req.id) && (
                      <span className="rounded-md bg-rose-500 px-2 py-1 text-[11px] font-bold text-white">
                        Phản hồi mới
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    Đơn {req.prescriptionId} · {req.patient} · {req.medCount}{" "}
                    thuốc · {req.date}
                  </p>
                </div>
                <button
                  onClick={() => onView(req.prescriptionId)}
                  className="min-h-[40px] rounded-md bg-teal-50 px-3 py-2 text-xs font-bold text-teal-700 hover:bg-teal-100"
                >
                  Xem đơn thuốc
                </button>
              </div>
              <p className="mt-4 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-700">
                {req.message}
              </p>
              {req.response && <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50 p-4"><p className="text-xs font-bold text-emerald-700">Phản hồi: {req.responderName} · {req.respondedAt}</p><p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{req.response}</p></div>}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    return () => { previousFocus?.focus(); };
  }, []);
  return (
    <dialog ref={dialog} onCancel={onClose} aria-label={title} className="m-auto max-h-[92dvh] w-[calc(100%_-_32px)] max-w-lg bg-transparent p-0 backdrop:bg-slate-950/25 backdrop:backdrop-blur-sm">
      <div className="flex max-h-[92dvh] w-full max-w-lg flex-col overflow-hidden rounded-t-2xl border border-slate-200 bg-white shadow-2xl sm:rounded-2xl">
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-100 p-4 sm:p-6">
          <div className="flex items-start gap-3">
            <BrandLogo size={36} />
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-teal-600">
                Medication safety
              </p>
              <h2 className="mt-1 text-xl font-extrabold">{title}</h2>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="shrink-0 rounded-lg p-1 text-slate-400 hover:bg-slate-50"
          >
            <X className="size-5" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4 sm:p-6">{children}</div>
      </div>
    </dialog>
  );
}

function InteractionModal({
  item,
  onClose,
}: {
  item: Finding;
  onClose: () => void;
}) {
  return (
    <Modal title="Chi tiết phát hiện" onClose={onClose}>
      <div className="flex items-center gap-3">
        <SeverityBadge severity={item.severity} />
        <span className="text-xs font-semibold text-slate-500">
          {item.kind}
        </span>
      </div>
      {item.untranslatedFields.length > 0 && (
        <p className="mt-3 text-xs text-amber-700">
          Một số nội dung chưa có bản dịch tiếng Việt; đang hiển thị nguyên văn.
        </p>
      )}
      {item.machineTranslation && (
        <p className="mt-3 text-xs text-slate-500">
          Bản dịch tự động, chưa được rà soát chuyên môn.
        </p>
      )}
      <h3 className="mt-4 text-xl font-extrabold">
        {item.a} <span className="px-2 text-slate-300">↕</span> {item.b}
      </h3>
      <div className="mt-6 space-y-5">
        <div>
          <h4 className="text-sm font-extrabold">Phát hiện gì?</h4>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            {item.text} Đây là thông tin cần được xem xét trong bối cảnh liều
            dùng, thời gian sử dụng và tình trạng sức khỏe.
          </p>
        </div>
        <InteractionExplanation a={item.a} b={item.b} />
        <div>
          <h4 className="text-sm font-extrabold">Bạn nên làm gì?</h4>
          <p className="mt-2 rounded-lg bg-teal-600 p-4 text-sm leading-relaxed text-white">
            {item.management ||
              "Hãy trao đổi với bác sĩ hoặc dược sĩ trước khi thay đổi thuốc."}
          </p>
        </div>
        <div>
          <h4 className="text-sm font-extrabold">Bằng chứng</h4>
          <div className="mt-2 rounded-lg border border-slate-200 p-3 text-xs text-slate-600">
            <div className="flex items-center gap-2 font-bold">
              <FileText className="size-4 text-teal-500" />{" "}
              {item.citations
                .map((c) => c.source_name || c.source_id)
                .join(", ") || "Chưa có nguồn"}
            </div>
            <p className="mt-2">
              {item.citations.map((c, i) => (
                <span key={i} className="block">
                  {c.label}
                  {c.source_url && /^https?:\/\//.test(c.source_url) && (
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="ml-2 text-teal-600 underline"
                    >
                      Xem nguồn
                    </a>
                  )}
                </span>
              ))}
            </p>
          </div>
        </div>
      </div>
    </Modal>
  );
}

function _UnusedIcons() {
  return (
    <>
      <Clock3 />
      <Send />
    </>
  );
}
