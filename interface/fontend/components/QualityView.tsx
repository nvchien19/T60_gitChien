'use client'

import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { ChevronDown, Info, X } from 'lucide-react'
import { api, type EvalAll, type EvalBinary, type EvalRx } from '@/lib/api'

// Chỉ số của chức năng kiểm tra đơn (eval/run_rx_eval.py). Bản thu gọn chỉ hiện các chỉ số chính; bấm "Xem tất cả chỉ
// số" để mở phần chi tiết. Đáp án của các bộ ca lấy từ nguồn bên ngoài CSDL của hệ thống (xem eval/golden/refs/README.md).

const pct = (value: number | null | undefined, digits = 1) => value === null || value === undefined ? '—' : `${(value * 100).toFixed(digits).replace('.', ',')}%`
const num = (value: number | null | undefined) => value === null || value === undefined ? '—' : String(value).replace('.', ',')
const ci = (range: number[] | null | undefined) => range ? `KTC 95%: ${pct(range[0])} – ${pct(range[1])}` : ''
const stamp = (value: string) => value.replace(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2})$/, '$3/$2/$1 $4')

function InfoButton({ open, onClick, label }: { open: boolean; onClick: () => void; label: string }) {
  return <button type="button" onClick={onClick} aria-expanded={open} aria-label={`Chú thích: ${label}`} className={`grid size-6 shrink-0 place-items-center rounded-full transition ${open ? 'bg-teal-100 text-teal-700' : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'}`}><Info className="size-4" /></button>
}

// Nút (i) và hộp chú thích. Mỗi lúc chỉ mở một hộp (mở hộp khác thì hộp cũ đóng), bấm ra ngoài, Esc, cuộn trang đều
// đóng. Hộp vẽ qua portal với vị trí cố định nên không bị khung cuộn cắt, và được kéo vào trong màn hình nếu tràn.
const NOTE_EVENT = 'quality-note-open'
const NOTE_WIDTH = 320

function Note({ label, children }: { label: string; children: ReactNode }) {
  const id = useId()
  const button = useRef<HTMLSpanElement>(null)
  const box = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)
  const open = pos !== null

  useEffect(() => {
    const onOther = (event: Event) => { if ((event as CustomEvent<string>).detail !== id) setPos(null) }
    window.addEventListener(NOTE_EVENT, onOther)
    return () => window.removeEventListener(NOTE_EVENT, onOther)
  }, [id])

  useEffect(() => {
    if (!open) return
    const close = () => setPos(null)
    const onPointer = (event: PointerEvent) => {
      const target = event.target as Node
      if (!box.current?.contains(target) && !button.current?.contains(target)) close()
    }
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') close() }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    window.addEventListener('scroll', close, true)
    window.addEventListener('resize', close)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
      window.removeEventListener('scroll', close, true)
      window.removeEventListener('resize', close)
    }
  }, [open])

  const toggle = () => {
    if (open || !button.current) { setPos(null); return }
    const rect = button.current.getBoundingClientRect()
    const width = Math.min(NOTE_WIDTH, window.innerWidth - 16)
    const left = Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8))
    window.dispatchEvent(new CustomEvent(NOTE_EVENT, { detail: id }))
    setPos({ top: rect.bottom + 6, left })
  }

  return <span ref={button} className="inline-flex">
    <InfoButton open={open} onClick={toggle} label={label} />
    {pos && createPortal(
      <div ref={box} role="note" aria-label={label} style={{ top: pos.top, left: pos.left, width: Math.min(NOTE_WIDTH, window.innerWidth - 16) }} className="fixed z-50 rounded-xl border border-teal-200 bg-white p-4 text-left text-[13px] font-normal leading-relaxed text-slate-700 shadow-xl">
        <div className="mb-2 flex items-start justify-between gap-3">
          <p className="font-semibold text-slate-900">{label}</p>
          <button type="button" onClick={() => setPos(null)} aria-label="Đóng chú thích" className="grid size-6 shrink-0 place-items-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-600"><X className="size-4" /></button>
        </div>
        <div className="space-y-2">{children}</div>
      </div>,
      document.body,
    )}
  </span>
}

// Màu nhấn của 4 chỉ số chính; tên lớp viết đủ để Tailwind giữ lại, nền và chữ đã có bản tối trong theme/dark.css.
const ACCENT = {
  teal: { card: 'bg-teal-50', text: 'text-teal-700', bar: 'bg-teal-500' },
  sky: { card: 'bg-sky-50', text: 'text-sky-800', bar: 'bg-sky-500' },
  violet: { card: 'bg-violet-50', text: 'text-violet-800', bar: 'bg-violet-500' },
  emerald: { card: 'bg-emerald-50', text: 'text-emerald-700', bar: 'bg-emerald-500' },
} as const
type Accent = keyof typeof ACCENT

type Metric = { key: 'sensitivity' | 'ppv' | 'f1' | 'specificity'; en: string; vi: string; accent: Accent; detail: string; note: ReactNode }

type Tool = { name: string; m: EvalBinary; kind: 'commercial' | 'ai'; inRef: boolean }
type Best = { name: string; value: number | null }
const COMMERCIAL = ['micromedex', 'drugscom']
const AI = ['chatgpt4', 'bingai', 'bard', 'chatgpt35']

// Các chuẩn đối chiếu người xem chọn được; 'any' (tổng hợp từ nguồn có thẩm quyền) là mặc định.
type RefKey = 'any' | 'labels' | 'two' | 'micromedex'
const REF_TABS: { key: RefKey; label: string }[] = [
  { key: 'any', label: 'Chuẩn tổng hợp' },
  { key: 'labels', label: 'Chỉ nhãn thuốc FDA + Nhật' },
  { key: 'two', label: '≥ 2 nguồn đồng ý' },
  { key: 'micromedex', label: 'Chỉ Micromedex' },
]

function MetricCard({ metric, value, best }: { metric: Metric; value: number | null; best: { commercial: Best; ai: Best } }) {
  const a = ACCENT[metric.accent]
  return <div className={`relative rounded-2xl border border-slate-200 ${a.card} p-4 pt-5 sm:p-5 sm:pt-6`}>
    <div aria-hidden className={`absolute inset-x-0 top-0 h-1.5 rounded-t-2xl ${a.bar}`} />
    <div className="flex items-start justify-between gap-2">
      <div><p className={`text-base font-extrabold tracking-tight ${a.text}`}>{metric.en}</p><p className="text-xs font-semibold text-slate-600">{metric.vi}</p></div>
      <Note label={metric.en}>{metric.note}</Note>
    </div>
    <p className={`mt-3 text-4xl font-black tabular-nums tracking-tight sm:text-5xl ${a.text}`}>{pct(value)}</p>
    <div className="mt-3 h-2 rounded-full bg-slate-200/70"><div className={`h-2 rounded-full ${a.bar}`} style={{ width: `${(value ?? 0) * 100}%` }} /></div>
    <p className="mt-2 text-[11px] text-slate-500">{metric.detail}</p>
    <p className="mt-1 text-[11px] text-slate-500">Phần mềm thương mại tốt nhất ({best.commercial.name}): <span className="font-semibold tabular-nums">{pct(best.commercial.value)}</span></p>
    <p className="text-[11px] text-slate-500">Chatbot AI tốt nhất ({best.ai.name}): <span className="font-semibold tabular-nums">{pct(best.ai.value)}</span></p>
  </div>
}

const BAR = { own: 'bg-teal-500', commercial: 'bg-amber-400', ai: 'bg-slate-300' }

// Biểu đồ cột ngang: Rà Thuốc so với phần mềm thương mại và chatbot AI trên cùng bộ cặp thuốc, mỗi chỉ số một nhóm.
function CompareChart({ metrics, system, tools }: { metrics: Metric[]; system: EvalBinary; tools: Tool[] }) {
  const rows = [{ name: 'Rà Thuốc', m: system, bar: BAR.own, own: true, inRef: false }, ...tools.map(t => ({ name: t.name, m: t.m, bar: BAR[t.kind], own: false, inRef: t.inRef }))]
  return <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500">
      <span className="font-bold text-slate-700">So sánh trên cùng {system.n} cặp</span>
      <span className="flex items-center gap-1.5"><span className={`size-2.5 rounded-sm ${BAR.own}`} /> Rà Thuốc</span>
      <span className="flex items-center gap-1.5"><span className={`size-2.5 rounded-sm ${BAR.commercial}`} /> Phần mềm tra tương tác thương mại</span>
      <span className="flex items-center gap-1.5"><span className={`size-2.5 rounded-sm ${BAR.ai}`} /> Chatbot AI</span>
    </div>
    <div className="mt-4 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(metric => <div key={metric.key}>
      <p className="text-xs font-extrabold text-slate-700">{metric.en} <span className="font-semibold text-slate-400">· {metric.vi}</span></p>
      <div className="mt-2 space-y-1.5">{rows.map(row => <div key={row.name} className="grid grid-cols-[5.5rem_1fr_2.75rem] items-center gap-2 text-[11px]">
        <span className={`truncate ${row.own ? 'font-bold text-slate-800' : 'text-slate-500'}`}>{row.name}{row.inRef ? ' *' : ''}</span>
        <span className="h-2.5 rounded-full bg-slate-100"><span className={`block h-2.5 rounded-full ${row.bar}`} style={{ width: `${(row.m[metric.key] ?? 0) * 100}%` }} /></span>
        <span className={`text-right tabular-nums ${row.own ? 'font-bold text-slate-800' : 'text-slate-500'}`}>{pct(row.m[metric.key], 0)}</span>
      </div>)}</div>
    </div>)}</div>
    <p className="mt-4 text-[11px] leading-relaxed text-slate-500">Số của Micromedex, Drugs.com và 4 chatbot chép từ phụ lục nghiên cứu Al-Ashwal 2023 rồi chấm lại theo cùng chuẩn với Rà Thuốc.{rows.some(r => r.inRef) ? ' * Nằm trong chuẩn đối chiếu nên được lợi (mọi cặp nó báo đều được tính là đúng).' : ''}</p>
  </div>
}

function KeyCard({ label, value, sub, note }: { label: string; value: string; sub: string; note: string }) {
  return <div className="relative rounded-xl border border-slate-200 bg-white p-4">
    <div className="flex items-start justify-between gap-2"><p className="text-xs font-semibold text-slate-500">{label}</p><Note label={label}>{note}</Note></div>
    <p className="mt-2 text-3xl font-extrabold tracking-tight text-slate-800">{value}</p>
    <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{sub}</p>
  </div>
}

function Section({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return <section className="rounded-xl border border-slate-200 bg-white p-5">
    <h3 className="text-sm font-extrabold">{title}</h3><p className="mt-1 text-xs text-slate-400">{hint}</p>
    <div className="mt-4">{children}</div>
  </section>
}

function Table({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return <div className="overflow-x-auto"><table className="w-full min-w-[32rem] text-left text-xs">
    <thead><tr className="border-b border-slate-200 text-slate-500">{head.map(h => <th key={h} className="py-2 pr-3 font-semibold">{h}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i} className="border-b border-slate-100 last:border-0">{r.map((c, j) => <td key={j} className={`py-2 pr-3 tabular-nums ${j === 0 ? 'font-semibold text-slate-700' : 'text-slate-600'}`}>{c}</td>)}</tr>)}</tbody>
  </table></div>
}

const binaryRow = (name: string, m: EvalBinary) => [name, pct(m.sensitivity), pct(m.specificity), pct(m.ppv), pct(m.npv), pct(m.f1), pct(m.accuracy)]

function Details({ data, chat }: { data: EvalRx; chat: EvalAll | null }) {
  const { alashwal: aa, onc, rx } = data
  const sys = aa.system
  const norm = rx.normalization
  const b = rx.burden
  const chatMetric = (key: string) => chat?.metrics.find(m => m.key === key)?.pooled ?? null
  const auth = data.authoritative
  const lit = data.literature ?? []
  return <div className="space-y-5">
    {auth && <Section title="Chuẩn tổng hợp từ nguồn có thẩm quyền" hint={`${auth.n} cặp Al-Ashwal 2023 · Micromedex ghi ${auth.sources.micromedex} cặp, nhãn thuốc FDA ${auth.sources.fda_label} cặp, nhãn thuốc Nhật Bản ${auth.sources.japan_label} cặp`}>
      <div className="grid gap-4 lg:grid-cols-3">{(['any', 'labels', 'two'] as const).map(k => <div key={k}>
        <p className="mb-1 text-[11px] font-semibold text-slate-500">{auth.refs[k].label} · {auth.refs[k].positives} cặp dương tính</p>
        <Table head={['Công cụ', 'Độ nhạy', 'Độ đặc hiệu', 'PPV', 'NPV', 'F1', 'Accuracy']} rows={[binaryRow('Rà Thuốc', auth.refs[k].system), ...[...COMMERCIAL, ...AI].filter(t => auth.refs[k].tools[t]).map(t => binaryRow(auth.refs[k].tools[t].label + (auth.refs[k].tools[t].in_reference ? ' *' : ''), auth.refs[k].tools[t]))]} />
      </div>)}</div>
      <p className="mt-3 text-[11px] leading-relaxed text-slate-500">Số cặp theo số nguồn ghi nhận: {Object.entries(auth.by_n_sources).map(([n, c]) => `${n} nguồn: ${c}`).join(' · ')}. Trong {auth.fp_vs_micromedex.n} cảnh báo Micromedex không coi là đáng kể, {auth.fp_vs_micromedex.supported_by_label} cảnh báo có nhãn thuốc FDA hoặc Nhật Bản làm cơ sở. Nhãn FDA được đọc bằng mô hình ngôn ngữ không thấy kết quả của Rà Thuốc; mỗi kết luận lưu kèm câu trích nguyên văn đã đối chiếu với nhãn. * Nằm trong chuẩn nên được lợi.</p>
    </Section>}

    {lit.length > 0 && <Section title="Phần mềm tra tương tác thương mại trong các nghiên cứu khác" hint="Khác bộ ca và khác chuẩn đối chiếu, chỉ để tham khảo; không so trực tiếp với số của Rà Thuốc ở trên">
      <div className="space-y-4">{lit.map(l => <div key={l.study}>
        <p className="text-[11px] font-semibold text-slate-600">{l.study}</p>
        <p className="mb-1 text-[11px] text-slate-400">{l.setting}</p>
        {l.rows && <Table head={['Phần mềm', 'Độ nhạy', 'Độ đặc hiệu', 'PPV', 'NPV']} rows={l.rows.map(r => [r[0], ...r.slice(1).map(v => pct(v as number, 0))])} />}
        {l.summary && <p className="text-xs text-slate-600">{l.summary}</p>}
      </div>)}</div>
    </Section>}

    <Section title="Đối chiếu riêng với từng phần mềm (Micromedex, Drugs.com)" hint={`${aa.n} cặp thuốc của nghiên cứu Al-Ashwal 2023 · dương tính khi nguồn tham chiếu ghi mức trung bình trở lên (Micromedex: ${aa.positives.micromedex} cặp, Drugs.com: ${aa.positives.drugscom} cặp)`}>
      <Table head={['Rà Thuốc so với', 'Độ nhạy', 'Độ đặc hiệu', 'PPV', 'NPV', 'F1', 'Accuracy']} rows={[binaryRow('Micromedex', sys.micromedex), binaryRow('Drugs.com', sys.drugscom)]} />
      <div className="mt-3 grid gap-2 text-[11px] text-slate-500 sm:grid-cols-2">
        <p>Micromedex: TP {sys.micromedex.tp} · FP {sys.micromedex.fp} · FN {sys.micromedex.fn} · TN {sys.micromedex.tn} · {ci(sys.micromedex.sensitivity_ci)} (độ nhạy) · kappa mức độ {num(sys.micromedex.kappa_weighted ?? null)}</p>
        <p>Drugs.com: TP {sys.drugscom.tp} · FP {sys.drugscom.fp} · FN {sys.drugscom.fn} · TN {sys.drugscom.tn} · {ci(sys.drugscom.sensitivity_ci)} (độ nhạy) · kappa mức độ {num(sys.drugscom.kappa_weighted ?? null)}</p>
      </div>
      <h4 className="mt-5 text-xs font-extrabold text-slate-700">Các công cụ khác trên cùng {aa.n} cặp (số liệu từ phụ lục bài báo)</h4>
      <div className="mt-2 grid gap-4 lg:grid-cols-2">{(['micromedex', 'drugscom'] as const).map(ref => <div key={ref}>
        <p className="mb-1 text-[11px] font-semibold text-slate-500">Tham chiếu {ref === 'micromedex' ? 'Micromedex' : 'Drugs.com'}</p>
        <Table head={['Công cụ', 'Độ nhạy', 'Độ đặc hiệu', 'PPV', 'NPV', 'F1', 'Accuracy']} rows={[binaryRow('Rà Thuốc', sys[ref]), ...Object.values(aa.comparators[ref]).map(c => binaryRow(c.label, c))]} />
      </div>)}</div>
      <p className="mt-3 text-[11px] leading-relaxed text-slate-500">Mức độ trong CSDL nguồn (DDInter 2.0) khớp Drugs.com ở kappa {num(sys.drugscom.kappa_weighted ?? null)}, nên cột Micromedex là thước đo độc lập hơn. Hai nguồn tham chiếu cũng không trùng nhau: lấy Micromedex làm chuẩn thì Drugs.com đạt độ nhạy {pct(aa.reference_agreement.sensitivity)}, độ đặc hiệu {pct(aa.reference_agreement.specificity)}.</p>
    </Section>

    <Section title="Cặp thuốc bắt buộc phải cảnh báo" hint={`${onc.n} cặp thuộc 14 nhóm tương tác ưu tiên cao của ONC (Phansalkar 2012), bỏ nhóm kéo dài QT`}>
      <div className="grid gap-3 sm:grid-cols-3">
        <KeyCard label="Có cảnh báo" value={pct(onc.alert_any_rate)} sub={`${onc.alert_any}/${onc.n} cặp`} note="Hệ thống đưa ra cảnh báo thuốc – thuốc (mọi mức) cho cặp nằm trong danh sách ONC." />
        <KeyCard label="Cảnh báo ở mức Nghiêm trọng trở lên" value={pct(onc.alert_major_rate)} sub={`${onc.alert_major}/${onc.n} cặp`} note="Mức Nghiêm trọng hoặc Chống chỉ định, đúng như CSDL nguồn ghi (hệ thống không tự nâng mức)." />
        <KeyCard label="Mức Nghiêm trọng trở lên, khi nhận ra cả hai tên" value={pct(onc.alert_major_rate_recognized)} sub={`${onc.recognized}/${onc.n} cặp có cả hai tên trong danh mục`} note="Chỉ tính các cặp mà cả hai thuốc có trong danh mục tên thuốc của hệ thống." />
      </div>
      <div className="mt-4"><Table head={['Nhóm ONC', 'Số cặp', 'Có cảnh báo', '≥ Nghiêm trọng']} rows={Object.entries(onc.by_rule).map(([id, r]) => [`${id.replace('ONC-', '')}. ${r.name}`, r.n, r.alert, r.major])} /></div>
    </Section>

    <Section title="Đơn thuốc thật" hint={`${rx.n_mimic} đơn nội trú MIMIC-IV (thuốc đang dùng ở giờ thứ 48, trung vị ${num(rx.median_drugs)} thuốc/đơn) và ${rx.n_vn} đơn thật Việt Nam · hoạt chất đáp án theo mã NDC → RxNorm hoặc in trên đơn`}>
      <h4 className="text-xs font-extrabold text-slate-700">Nhận diện tên thuốc</h4>
      <div className="mt-2"><Table head={['Nhóm đơn', 'Số thuốc', 'Nhận đúng hoạt chất', 'Gợi ý, chờ xác nhận', 'Chưa có trong danh mục', 'Nhận nhầm']} rows={(['mimic', 'vn', 'all'] as const).map(k => [k === 'mimic' ? 'MIMIC-IV' : k === 'vn' ? 'Việt Nam' : 'Tất cả', norm[k].drug_items, pct(norm[k].correct_rate), pct(norm[k].suggest_rate), pct(norm[k].unknown_rate), pct(norm[k].wrong_rate)])} /></div>
      <p className="mt-2 text-[11px] text-slate-500">Sản phẩm không phải thuốc trên phiếu tư vấn: {norm.vn.not_drug_rejected}/{norm.vn.not_drug_items} không bị nhận thành thuốc. Khi đã nhận ra, đúng hoạt chất {pct(norm.all.precision_when_recognized)}.</p>
      <h4 className="mt-5 text-xs font-extrabold text-slate-700">Trùng hoạt chất</h4>
      <p className="mt-1 text-xs text-slate-600">Phát hiện {rx.duplicates.detected}/{rx.duplicates.expected} cặp thuốc cùng hoạt chất ({pct(rx.duplicates.recall)}); cảnh báo trùng đưa ra đúng {rx.duplicates.flagged_confirmed}/{rx.duplicates.flagged_checkable} ({pct(rx.duplicates.precision)}). Cặp bắt buộc cảnh báo (ONC) xuất hiện trên đơn: {rx.must_alert.hit_major}/{rx.must_alert.n} được cảnh báo mức Nghiêm trọng.</p>
      <h4 className="mt-5 text-xs font-extrabold text-slate-700">Số cảnh báo trên mỗi đơn MIMIC-IV</h4>
      <div className="mt-2"><Table head={['Loại', 'Trung bình', 'Trung vị', 'P90']} rows={([['Thuốc – thuốc (mọi mức)', b.ddi], ['Nghiêm trọng, chống chỉ định', b.major_plus], ['Trung bình', b.moderate], ['Nhẹ', b.minor], ['Thuốc – thực phẩm', b.food], ['Trùng thuốc', b.dup]] as const).map(([name, s]) => [name, num(s.mean), num(s.median), num(s.p90)])} /></div>
      <p className="mt-2 text-[11px] text-slate-500">Đơn có ít nhất một cảnh báo Nghiêm trọng trở lên: {pct(b.rx_with_major_plus)}; có cảnh báo thuốc – thuốc: {pct(b.rx_with_any_ddi)}. Cảnh báo kèm nguồn: {pct(rx.citation_rate)} trên {rx.findings_total.toLocaleString('vi-VN')} cảnh báo.</p>
    </Section>

    {chat && <Section title="Trợ lý hỏi đáp" hint={`${chat.n_cases} câu hỏi mẫu nhóm dựng từ CSDL (${chat.runs.map(r => r.label).join(' + ')})`}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{([['Độ phủ (recall)', 'recall'], ['Độ chính xác (precision)', 'precision'], ['Độ đặc hiệu', 'specificity'], ['Chặn câu xin lời khuyên điều trị', 'guardrail_pass_rate'], ['Không khuyên điều trị', 'advice_free_rate'], ['Không khẳng định "an toàn"', 'no_false_safe_rate'], ['Kết luận có nguồn', 'citation_coverage'], ['Chuẩn hóa tên thuốc', 'normalization_accuracy']] as const).map(([label, key]) => <div key={key} className="rounded-lg bg-slate-50 p-3"><p className="text-[11px] font-semibold text-slate-500">{label}</p><p className="mt-1 text-lg font-extrabold text-slate-800">{pct(chatMetric(key))}</p></div>)}</div>
    </Section>}

    <Section title="Nguồn dữ liệu đánh giá" hint={`Tính lúc ${stamp(data.generated)} bằng eval/run_rx_eval.py, không qua mô hình ngôn ngữ`}>
      <ul className="list-disc space-y-1 pl-5 text-[11px] leading-relaxed text-slate-500">{Object.values(data.sources).map(s => <li key={s}>{s}</li>)}</ul>
    </Section>
  </div>
}

export function QualityView() {
  const [data, setData] = useState<EvalRx | null>(null)
  const [chat, setChat] = useState<EvalAll | null>(null)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(false)
  const [refKey, setRefKey] = useState<RefKey>('any')
  useEffect(() => {
    let cancelled = false
    api<EvalRx>('/eval/metrics/rx').then(d => { if (!cancelled) setData(d) }).catch(e => { if (!cancelled) setError(e.message) })
    api<EvalAll>('/eval/metrics/all').then(d => { if (!cancelled) setChat(d) }).catch(() => undefined)
    return () => { cancelled = true }
  }, [])

  if (error) return <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{error}</p>
  if (!data) return <p role="status" className="rounded-xl bg-white p-5 text-sm">Đang tải chỉ số…</p>
  const { alashwal: aa, onc, rx } = data
  const auth = data.authoritative
  const ref: RefKey = auth ? refKey : 'micromedex'
  const block = ref === 'micromedex' ? null : auth!.refs[ref]
  const mm = block ? block.system : aa.system.micromedex
  const toolSrc: Record<string, EvalBinary & { label: string; in_reference?: boolean }> = block ? block.tools : aa.comparators.micromedex
  const tools: Tool[] = [...COMMERCIAL, ...AI].filter(k => toolSrc[k] && !(ref === 'micromedex' && k === 'micromedex')).map(k => ({ name: toolSrc[k].label, m: toolSrc[k], kind: COMMERCIAL.includes(k) ? 'commercial' : 'ai', inRef: Boolean(toolSrc[k].in_reference) }))
  const bestOf = (key: Metric['key'], kind: Tool['kind']) => tools.filter(t => t.kind === kind && !t.inRef).reduce<Best>((top, t) => (t.m[key] ?? -1) > (top.value ?? -1) ? { name: t.name, value: t.m[key] } : top, { name: '—', value: null })
  const positives = block ? block.positives : aa.positives.micromedex
  // Câu mô tả "cặp có tương tác" theo chuẩn đang chọn, dùng trong các chú thích (i)
  const refPos = ref === 'micromedex' ? 'Micromedex ghi tương tác mức trung bình trở lên'
    : ref === 'labels' ? 'nhãn thuốc FDA hoặc nhãn thuốc Nhật Bản có khuyến cáo khi dùng chung'
    : ref === 'two' ? 'ít nhất 2 trong 3 nguồn (Micromedex, nhãn thuốc FDA, nhãn thuốc Nhật Bản) ghi có tương tác cần xử trí'
    : 'ít nhất một nguồn có thẩm quyền (Micromedex, nhãn thuốc FDA, nhãn thuốc Nhật Bản) ghi có tương tác cần xử trí, kèm giải thích'
  const refShort = ref === 'micromedex' ? 'Micromedex' : 'nguồn có thẩm quyền'
  const formula = (text: string) => <span className="mt-1.5 block rounded bg-slate-50 px-2 py-1 font-mono text-[11px] text-slate-700">{text}</span>
  const metrics: Metric[] = [
    { key: 'sensitivity', en: 'Recall', vi: 'Độ phủ, bắt được tương tác', accent: 'teal', detail: `${mm.tp}/${mm.tp + mm.fn} cặp có tương tác được cảnh báo`,
      note: <>Còn gọi là độ nhạy (sensitivity). Trong các cặp mà {refPos}, hệ thống cảnh báo (mức trung bình trở lên) được bao nhiêu phần. Cao nghĩa là ít bỏ sót.{formula(`TP / (TP + FN) = ${mm.tp} / ${mm.tp + mm.fn}`)}<span className="mt-1.5 block text-slate-500">{ci(mm.sensitivity_ci)}</span></> },
    { key: 'ppv', en: 'Precision', vi: 'Độ chính xác của cảnh báo', accent: 'sky', detail: `${mm.tp}/${mm.tp + mm.fp} cảnh báo có cơ sở trong ${refShort}`,
      note: <>Còn gọi là giá trị dự đoán dương (PPV). Trong các cảnh báo hệ thống đưa ra (mức trung bình trở lên), bao nhiêu phần có cơ sở: {refPos}. Cao nghĩa là ít cảnh báo thừa.{formula(`TP / (TP + FP) = ${mm.tp} / ${mm.tp + mm.fp}`)}<span className="mt-1.5 block text-slate-500">{ci(mm.ppv_ci)}</span></> },
    { key: 'f1', en: 'F1-score', vi: 'Cân bằng Recall và Precision', accent: 'violet', detail: `Trung bình điều hòa của ${pct(mm.sensitivity)} và ${pct(mm.ppv)}`,
      note: <>Gộp Recall và Precision thành một số; chỉ cao khi cả hai cùng cao, nên khó "ăn gian" bằng cách cảnh báo tất cả hoặc không cảnh báo gì.{formula('2 × Precision × Recall / (Precision + Recall)')}</> },
    { key: 'specificity', en: 'Specificity', vi: 'Độ đặc hiệu, không báo nhầm', accent: 'emerald', detail: `${mm.tn}/${mm.tn + mm.fp} cặp không có cơ sở cảnh báo được để yên`,
      note: <>Trong các cặp không nguồn nào ở chuẩn đang chọn ghi tương tác cần xử trí, hệ thống không đưa cảnh báo mức trung bình trở lên bao nhiêu phần. Cao nghĩa là người dùng ít bị nhờn cảnh báo.{formula(`TN / (TN + FP) = ${mm.tn} / ${mm.tn + mm.fp}`)}<span className="mt-1.5 block text-slate-500">{ci(mm.specificity_ci)}</span></> },
  ]
  const refNote = <>Một cảnh báo được tính là <b>đúng</b> khi có cơ sở trong một nguồn có thẩm quyền, không bắt buộc phải trùng một trang tra cứu cụ thể. Ba nguồn: <b>Micromedex</b> (mức trung bình trở lên); <b>nhãn thuốc FDA</b> (tờ thông tin kê đơn được FDA duyệt, có câu khuyến cáo khi dùng chung: chống chỉ định, tránh, chỉnh liều, theo dõi, thận trọng); <b>nhãn thuốc Nhật Bản</b> (tờ hướng dẫn được PMDA duyệt, tổng hợp trong KEGG, chỉ tính bản ghi có ghi cơ chế). Drugs.com không nằm trong chuẩn vì CSDL của hệ thống gần như trùng Drugs.com.</>
  const refHint = ref === 'micromedex' ? `${positives} cặp Micromedex ghi mức trung bình trở lên` : `${positives}/${aa.n} cặp có cơ sở cảnh báo theo chuẩn này`
  return <>
    <section>
      <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-teal-600">Evaluation</p>
      <h2 className="text-xl font-extrabold tracking-tight sm:text-2xl">Chất lượng kiểm tra đơn thuốc</h2>
      <p className="mt-1.5 text-sm text-slate-500">Đo trên {aa.n} cặp thuốc đã công bố (Al-Ashwal 2023), {onc.n} cặp bắt buộc cảnh báo (ONC) và {rx.n_prescriptions} đơn thuốc thật. Đáp án lấy từ nguồn bên ngoài CSDL của hệ thống; cảnh báo được tính là đúng khi có cơ sở trong một nguồn có thẩm quyền (Micromedex, nhãn thuốc FDA, nhãn thuốc Nhật Bản). Bấm <Info className="inline size-3.5 align-[-2px]" /> để xem chú thích.</p>
    </section>

    <section aria-labelledby="key-metrics">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 id="key-metrics" className="text-sm font-extrabold text-slate-700">Chỉ số chính · phát hiện tương tác thuốc – thuốc <span className="font-semibold text-slate-400">({aa.n} cặp, {refHint})</span></h3>
        {auth && <div className="relative flex flex-wrap items-center gap-1.5">
          <div role="radiogroup" aria-label="Chuẩn đối chiếu" className="flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1">{REF_TABS.map(t => <button key={t.key} type="button" role="radio" aria-checked={ref === t.key} onClick={() => setRefKey(t.key)} className={`rounded-lg px-2.5 py-1 text-[11px] font-bold transition ${ref === t.key ? 'bg-white text-teal-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>{t.label}</button>)}</div>
          <Note label="Chuẩn đối chiếu">{refNote}</Note>
        </div>}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(m => <MetricCard key={m.key} metric={m} value={mm[m.key]} best={{ commercial: bestOf(m.key, 'commercial'), ai: bestOf(m.key, 'ai') }} />)}</div>
    </section>

    <CompareChart metrics={metrics} system={mm} tools={tools} />

    <h3 className="text-sm font-extrabold text-slate-700">Cặp bắt buộc cảnh báo và đơn thuốc thật</h3>
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <KeyCard label="Cặp bắt buộc phải cảnh báo" value={pct(onc.alert_any_rate)} sub={`${onc.alert_any}/${onc.n} cặp ONC có cảnh báo; ${pct(onc.alert_major_rate)} ở mức Nghiêm trọng trở lên`} note="Danh sách 14 nhóm tương tác mà hội đồng chuyên gia của ONC (Mỹ, 2012) yêu cầu phần mềm kê đơn luôn cảnh báo, ví dụ thuốc ức chế MAO với thuốc chống trầm cảm SSRI." />
      <KeyCard label="Nhận đúng tên thuốc trên đơn thật" value={pct(rx.normalization.all.correct_rate)} sub={`${rx.normalization.all.drug_items.toLocaleString('vi-VN')} thuốc trên ${rx.n_prescriptions} đơn; nhận nhầm ${pct(rx.normalization.all.wrong_rate)}`} note="Tên thuốc như ghi trên y lệnh hoặc đơn (tên biệt dược, kèm hàm lượng, dạng bào chế) được nhận ra đúng hoạt chất. Tên chưa chắc chắn được hỏi lại người dùng thay vì đoán." />
      <KeyCard label="Cảnh báo có nguồn" value={pct(rx.citation_rate, 0)} sub={`${rx.findings_total.toLocaleString('vi-VN')} cảnh báo trên đơn thật, mỗi cảnh báo dẫn về bản ghi gốc`} note="Mỗi cảnh báo (thuốc – thuốc, thuốc – thực phẩm, trùng thuốc) đều kèm trích dẫn bản ghi trong CSDL nguồn." />
      <KeyCard label="Cảnh báo Nghiêm trọng mỗi đơn" value={num(rx.burden.major_plus.median)} sub={`Trung vị trên đơn nội trú ${num(rx.median_drugs)} thuốc; 90% số đơn có không quá ${num(rx.burden.major_plus.p90)}`} note="Số cảnh báo mức Nghiêm trọng hoặc Chống chỉ định trên mỗi đơn MIMIC-IV. Ít cảnh báo ngắt quãng giúp người dùng không bị nhờn cảnh báo." />
    </div>

    <button type="button" onClick={() => setExpanded(!expanded)} aria-expanded={expanded} className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-3 text-sm font-bold text-teal-700 transition hover:bg-teal-50">
      {expanded ? 'Thu gọn' : 'Xem tất cả chỉ số'}<ChevronDown className={`size-4 transition ${expanded ? 'rotate-180' : ''}`} />
    </button>
    {expanded && <Details data={data} chat={chat} />}
  </>
}

