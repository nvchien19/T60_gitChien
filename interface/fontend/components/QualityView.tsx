'use client'

import { useEffect, useState } from 'react'
import { api, type EvalMetrics } from '@/lib/api'

const HEADLINE: { key: string; label: string; hint: string }[] = [
  { key: 'recall', label: 'Recall', hint: 'Tỉ lệ tương tác có thật được phát hiện: TP / (TP + FN)' },
  { key: 'false_negative_rate', label: 'Tỉ lệ bỏ sót (FN)', hint: 'Tương tác có thật bị bỏ sót: FN / (TP + FN). Càng thấp càng tốt' },
  { key: 'precision', label: 'Precision', hint: 'Tỉ lệ cảnh báo đúng trong các cảnh báo đã đưa ra: TP / (TP + FP)' },
  { key: 'f1', label: 'F1', hint: 'Trung bình điều hòa của precision và recall' },
]
const pct = (value: number | null) => value === null ? '—' : `${(value * 100).toFixed(1).replace('.', ',')}%`
const runLabel = (run: string) => run.replace(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/, '$3/$2/$1 $4:$5')

export function QualityView() {
  const [data, setData] = useState<EvalMetrics | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { let cancelled = false; api<EvalMetrics>('/eval/metrics').then(d => { if (!cancelled) setData(d) }).catch(e => { if (!cancelled) setError(e.message) }); return () => { cancelled = true } }, [])

  if (error) return <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{error}</p>
  if (!data) return <p role="status" className="rounded-xl bg-white p-5 text-sm">Đang tải chỉ số…</p>
  const byKey = Object.fromEntries(data.metrics.map(m => [m.key, m]))
  const { tp, fp, fn, tn } = data.confusion
  return <>
    <section><p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-sky-600">Evaluation</p><h2 className="text-xl font-extrabold tracking-tight sm:text-2xl">Chất lượng phát hiện tương tác</h2><p className="mt-1.5 text-sm text-slate-500">Đo trên bộ {data.n_cases} ca chuẩn (golden set) · lần chạy {runLabel(data.run)}</p></section>
    <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">{HEADLINE.map(({ key, label, hint }) => { const m = byKey[key]; return <div key={key} title={hint} className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5"><div className="flex items-start justify-between gap-2"><p className="text-xs font-semibold text-slate-500">{label}</p>{m && m.passed !== null && <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${m.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{m.passed ? 'Đạt' : 'Chưa đạt'}</span>}</div><p className="mt-2 text-xl font-extrabold sm:mt-3 sm:text-2xl">{pct(m?.value ?? null)}</p><p className="mt-1 text-[11px] text-slate-400">{m ? `Mục tiêu ${m.op === '>=' ? '≥' : '≤'} ${pct(m.threshold)}` : 'Chưa có số liệu'}</p></div> })}</div>
    <div className="grid gap-7 xl:grid-cols-2">
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h3 className="text-sm font-extrabold">Bảng nhầm lẫn</h3><p className="mt-1 text-xs text-slate-400">Đếm theo từng cặp thuốc, thuốc - thực phẩm, thuốc - bệnh nền</p><div className="mt-4 grid grid-cols-2 gap-2 text-center">{([['Phát hiện đúng (TP)', tp, 'bg-emerald-50 text-emerald-700'], ['Bỏ sót (FN)', fn, 'bg-rose-50 text-rose-700'], ['Cảnh báo thừa (FP)', fp, 'bg-amber-50 text-amber-700'], ['Không cảnh báo, đúng (TN)', tn, 'bg-slate-50 text-slate-600']] as const).map(([label, value, tone]) => <div key={label} className={`rounded-lg p-4 ${tone}`}><p className="text-2xl font-extrabold">{value}</p><p className="mt-1 text-[11px] font-semibold">{label}</p></div>)}</div></section>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h3 className="text-sm font-extrabold">Ca cần xem lại</h3><p className="mt-1 text-xs text-slate-400">Các ca trong bộ chuẩn còn bỏ sót hoặc cảnh báo thừa</p><div className="mt-4 space-y-2">{data.review_cases.length === 0 && <p className="text-sm text-slate-500">Không có ca nào.</p>}{data.review_cases.map(c => <div key={c.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs"><span className="font-bold text-slate-700">{c.id} <span className="font-normal text-slate-400">· {c.category}</span></span><span className="text-slate-500">bỏ sót {c.fn} · thừa {c.fp}</span></div>)}</div></section>
    </div>
    <p className="text-xs leading-relaxed text-slate-500">Số liệu đo trên bộ ca chuẩn nội bộ, quy mô nhỏ; chưa phải kết quả kiểm định lâm sàng. Chạy lại bằng <code>eval/predict.py</code> và <code>eval/run_eval.py</code> sau mỗi lần đổi dữ liệu hoặc logic.</p>
  </>
}
