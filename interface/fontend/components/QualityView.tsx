'use client'

import { useEffect, useState } from 'react'
import { Info } from 'lucide-react'
import { api, type EvalAll, type EvalAllMetric, type EvalBenchmark } from '@/lib/api'

type Meta = { label: string; note: string }
// Chú thích hiện khi bấm nút (i) ở góc phải mỗi chỉ số.
const META: Record<string, Meta> = {
  recall: { label: 'Recall (độ phủ)', note: 'Trong tất cả tương tác có thật theo CSDL, agent phát hiện được bao nhiêu phần: TP / (TP + FN). Càng cao càng ít bỏ sót.' },
  false_negative_rate: { label: 'Tỉ lệ bỏ sót (FN)', note: 'Tương tác có thật mà agent không cảnh báo: FN / (TP + FN) = 1 − Recall. Đây là lỗi nguy hiểm nhất, càng thấp càng tốt.' },
  precision: { label: 'Precision (độ chính xác)', note: 'Trong các cảnh báo agent đưa ra, bao nhiêu phần khớp đáp án: TP / (TP + FP). Thấp nghĩa là cảnh báo thừa nhiều, người dùng dễ "nhờn" cảnh báo.' },
  f1: { label: 'F1', note: 'Trung bình điều hòa của Precision và Recall: 2·TP / (2·TP + FP + FN). Chỉ cao khi cả hai cùng cao.' },
  sensitivity: { label: 'Độ nhạy (Sensitivity)', note: 'Cùng công thức với Recall: TP / (TP + FN). Tách riêng để so với ngưỡng của Lexicomp trong nghiên cứu Marcath 2018.' },
  specificity: { label: 'Độ đặc hiệu (Specificity)', note: 'Trong các cặp KHÔNG có tương tác theo đáp án, agent im lặng đúng bao nhiêu phần: TN / (TN + FP). Thấp nghĩa là hay cảnh báo nhầm.' },
  ppv: { label: 'PPV (giá trị dự đoán dương)', note: 'Khi agent cảnh báo, xác suất cảnh báo đó đúng: TP / (TP + FP). Cùng công thức với Precision, so với ngưỡng Lexicomp.' },
  npv: { label: 'NPV (giá trị dự đoán âm)', note: 'Khi agent không cảnh báo, xác suất thực sự không có bản ghi tương tác: TN / (TN + FN).' },
  accuracy: { label: 'Độ chính xác chung (Accuracy)', note: 'Tỉ lệ quyết định đúng trên mọi cặp: (TP + TN) / tổng. Dùng để so với các chatbot trong Al-Ashwal 2023.' },
  composite: { label: 'Điểm tổng hợp', note: 'Trung bình cộng của độ nhạy, độ đặc hiệu, PPV và NPV. Một con số tóm tắt, không có ngưỡng riêng.' },
  severe_recall: { label: 'Recall mức nghiêm trọng', note: 'Trong các tương tác mức NGHIÊM TRỌNG hoặc CHỐNG CHỈ ĐỊNH, bao nhiêu phần được cảnh báo ở mức từ nghiêm trọng trở lên.' },
  contraindicated_recall: { label: 'Recall chống chỉ định', note: 'Các cặp CHỐNG CHỈ ĐỊNH phải được báo đúng mức chống chỉ định, không được hạ mức. Yêu cầu 100%.' },
  severity_accuracy: { label: 'Đúng mức độ', note: 'Với các tương tác đã phát hiện đúng, mức độ (nhẹ / trung bình / nghiêm trọng / chống chỉ định) khớp CSDL bao nhiêu phần.' },
  severity_kappa: { label: 'Kappa mức độ', note: 'Hệ số Cohen kappa giữa mức độ agent báo và mức độ trong đáp án, đã trừ phần trùng do ngẫu nhiên. 1,0 là khớp hoàn toàn.' },
  max_severity_accuracy: { label: 'Đúng mức cao nhất của ca', note: 'Tỉ lệ ca mà mức cảnh báo cao nhất agent đưa ra khớp mức cao nhất trong đáp án. Cảnh báo thừa ở mức cao hơn sẽ làm chỉ số này giảm.' },
  duplicate_recall: { label: 'Phát hiện trùng thuốc', note: 'Tỉ lệ trường hợp trùng hoạt chất hoặc trùng nhóm điều trị (vd. hai thuốc cùng chứa paracetamol) được phát hiện.' },
  normalization_accuracy: { label: 'Chuẩn hóa tên thuốc', note: 'Tỉ lệ tên người dùng nhập (biệt dược, viết sai chính tả, tên ngoài CSDL) được nhận diện đúng trạng thái và đúng hoạt chất.' },
  flow_accuracy: { label: 'Đi đúng luồng', note: 'Tỉ lệ ca agent xử lý đúng hướng: tra cứu khi tên rõ ràng, hỏi lại khi tên chưa chắc, báo không nhận diện được khi tên lạ.' },
  guardrail_pass_rate: { label: 'Chặn câu bẫy', note: 'Với câu hỏi xin lời khuyên điều trị (ngưng, đổi, tăng liều, kê thuốc), tỉ lệ agent không đưa lời khuyên và hướng người dùng tới bác sĩ/dược sĩ.' },
  advice_free_rate: { label: 'Không khuyên điều trị', note: 'Tỉ lệ câu trả lời không chứa lời khuyên ngưng / đổi / chỉnh liều / kê thuốc (quy tắc G1). Kiểm bằng mẫu câu (regex), không phải người đọc.' },
  no_false_safe_rate: { label: 'Không khẳng định "an toàn"', note: 'Khi CSDL không có bản ghi, tỉ lệ agent KHÔNG nói rằng dùng chung là an toàn (quy tắc G4).' },
  no_record_stated_rate: { label: 'Nói rõ "chưa có bản ghi"', note: 'Với các ca không có bản ghi, tỉ lệ câu trả lời nói rõ CSDL chưa có dữ liệu, thay vì im lặng.' },
  disclaimer_rate: { label: 'Có lời nhắc tham khảo', note: 'Tỉ lệ câu trả lời có lời nhắc "chỉ là cảnh báo tham khảo" và hướng tới bác sĩ/dược sĩ.' },
  pii_leak_rate: { label: 'Rò rỉ thông tin cá nhân', note: 'Tỉ lệ câu trả lời chứa số điện thoại, email, số giấy tờ (quy tắc G5). Phải bằng 0.' },
  citation_validity: { label: 'Trích dẫn hợp lệ', note: 'Trong các nguồn agent trích dẫn, bao nhiêu phần nằm trong đáp án của ca. Chưa đạt chủ yếu vì cảnh báo thừa kéo theo trích dẫn của chính bản ghi thừa đó (bản ghi có thật trong CSDL, nhưng ngoài đáp án).' },
  citation_coverage: { label: 'Kết luận có nguồn', note: 'Tỉ lệ kết luận tương tác có kèm trích dẫn bản ghi CSDL (quy tắc G2: không có kết luận nào thiếu nguồn).' },
  citation_marker_rate: { label: 'Có dấu trích dẫn [n]', note: 'Tỉ lệ câu trả lời có tương tác mà phần chữ có đánh dấu [1], [2]… để người đọc lần về nguồn.' },
  latency_p50_ms: { label: 'Thời gian phản hồi (trung vị)', note: 'Một nửa số ca được trả lời nhanh hơn mức này. Đo trên máy phát triển, node giải thích tất định, chưa tính thời gian gọi LLM.' },
  latency_p95_ms: { label: 'Thời gian phản hồi (p95)', note: '95% số ca được trả lời nhanh hơn mức này. Đo trên máy phát triển, chưa tính thời gian gọi LLM giải thích (thêm khoảng 3 đến 5 giây).' },
}
const HEADLINE = ['recall', 'false_negative_rate', 'precision', 'f1']
const GROUPS: { title: string; hint: string; keys: string[] }[] = [
  { title: 'Phát hiện tương tác', hint: 'Bảng 2×2 đếm theo từng cặp, cùng cách tính với Marcath 2018', keys: ['sensitivity', 'specificity', 'ppv', 'npv', 'accuracy', 'composite'] },
  { title: 'Mức độ và trùng thuốc', hint: 'Đã phát hiện thì có xếp đúng mức không', keys: ['severe_recall', 'contraindicated_recall', 'severity_accuracy', 'severity_kappa', 'max_severity_accuracy', 'duplicate_recall'] },
  { title: 'Nhận diện tên thuốc', hint: 'Bước normalize của agent', keys: ['normalization_accuracy', 'flow_accuracy'] },
  { title: 'An toàn (guardrail)', hint: 'Không khuyên điều trị, không khẳng định an toàn', keys: ['guardrail_pass_rate', 'advice_free_rate', 'no_false_safe_rate', 'no_record_stated_rate', 'disclaimer_rate', 'pii_leak_rate'] },
  { title: 'Trích dẫn nguồn', hint: 'Mọi kết luận phải lần về được bản ghi CSDL', keys: ['citation_validity', 'citation_coverage', 'citation_marker_rate'] },
  { title: 'Vận hành', hint: 'Tốc độ phản hồi', keys: ['latency_p50_ms', 'latency_p95_ms'] },
]
const COMPARE: { key: keyof EvalBenchmark & string; label: string }[] = [
  { key: 'sensitivity', label: 'Độ nhạy' }, { key: 'specificity', label: 'Độ đặc hiệu' }, { key: 'ppv', label: 'PPV' }, { key: 'npv', label: 'NPV' }, { key: 'accuracy', label: 'Accuracy' },
]

const isMs = (key: string) => key.endsWith('_ms')
const pct = (value: number | null | undefined) => value === null || value === undefined ? '—' : `${(value * 100).toFixed(1).replace('.', ',')}%`
const show = (key: string, value: number | null | undefined) => value === null || value === undefined ? '—' : isMs(key) ? `${Math.round(value)} ms` : key === 'severity_kappa' ? value.toFixed(2).replace('.', ',') : pct(value)
const stamp = (run: string) => run.replace(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/, '$3/$2/$1 $4:$5')

function InfoButton({ open, onClick, label }: { open: boolean; onClick: () => void; label: string }) {
  return <button type="button" onClick={onClick} aria-expanded={open} aria-label={`Chú thích: ${label}`} className={`grid size-6 shrink-0 place-items-center rounded-full transition ${open ? 'bg-sky-100 text-sky-700' : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'}`}><Info className="size-4" /></button>
}

function MetricCard({ metric, runs, big }: { metric: EvalAllMetric; runs: EvalAll['runs']; big?: boolean }) {
  const [open, setOpen] = useState(false)
  const meta = META[metric.key] ?? { label: metric.key, note: 'Chưa có chú thích.' }
  const rate = !isMs(metric.key) && metric.pooled !== null
  const fill = metric.passed === false ? 'bg-rose-500' : 'bg-sky-500'
  return <div className="rounded-xl border border-slate-200 bg-white p-4">
    <div className="flex items-start justify-between gap-2">
      <p className="text-xs font-semibold text-slate-500">{meta.label}</p>
      <div className="flex items-center gap-1.5">
        {metric.passed !== null && <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${metric.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{metric.passed ? 'Đạt' : 'Chưa đạt'}</span>}
        <InfoButton open={open} onClick={() => setOpen(!open)} label={meta.label} />
      </div>
    </div>
    {open && <p className="mt-2 rounded-lg bg-sky-50 p-2.5 text-xs leading-relaxed text-slate-700">{meta.note}{metric.basis && <span className="mt-1 block text-slate-500">Căn cứ ngưỡng: {metric.basis}.</span>}</p>}
    <p className={`mt-2 font-extrabold ${big ? 'text-2xl' : 'text-xl'}`}>{show(metric.key, metric.pooled)}</p>
    {rate && <div className="relative mt-2 h-2 rounded-full bg-slate-100">
      <div className={`h-2 rounded-full ${fill}`} style={{ width: `${Math.max(0, Math.min(1, metric.pooled as number)) * 100}%` }} />
      {metric.threshold !== null && <span title="Ngưỡng" className="absolute -top-1 h-4 w-0.5 bg-slate-700" style={{ left: `${metric.threshold * 100}%` }} />}
    </div>}
    <p className="mt-2 text-[11px] text-slate-400">{metric.op && metric.threshold !== null ? `Ngưỡng ${metric.op === '>=' ? '≥' : '≤'} ${show(metric.key, metric.threshold)}` : 'Không đặt ngưỡng'}</p>
    <p className="mt-1 text-[11px] text-slate-500">{runs.map(r => `${r.id === 'golden' ? 'Golden' : 'Độc lập'} ${show(metric.key, metric.runs[r.id])}`).join(' · ')} · TB cộng {show(metric.key, metric.mean)}</p>
  </div>
}

function BenchmarkChart({ label, field, ours, benchmarks }: { label: string; field: string; ours: EvalAllMetric | undefined; benchmarks: EvalBenchmark[] }) {
  const rows = [
    ...(ours ? [{ name: 'Rà Thuốc (gộp)', value: ours.pooled, tone: 'bg-sky-500', bold: true }, { name: 'Rà Thuốc · bộ độc lập', value: ours.runs.holdout ?? null, tone: 'bg-sky-300', bold: true }] : []),
    ...benchmarks.map(b => ({ name: b.name, value: (b[field as keyof EvalBenchmark] as number | undefined) ?? null, tone: b.kind === 'db' ? 'bg-slate-400' : 'bg-amber-400', bold: false })),
  ].filter(r => r.value !== null).sort((a, b) => (b.value as number) - (a.value as number))
  return <div>
    <h4 className="text-xs font-extrabold text-slate-700">{label}</h4>
    <div className="mt-2 space-y-1.5">{rows.map(r => <div key={r.name} className="grid grid-cols-[8.5rem_1fr_3.2rem] items-center gap-2 text-[11px]">
      <span className={`truncate ${r.bold ? 'font-bold text-slate-800' : 'text-slate-500'}`}>{r.name}</span>
      <span className="h-2.5 rounded-full bg-slate-100"><span className={`block h-2.5 rounded-full ${r.tone}`} style={{ width: `${(r.value as number) * 100}%` }} /></span>
      <span className={`text-right tabular-nums ${r.bold ? 'font-bold text-slate-800' : 'text-slate-500'}`}>{pct(r.value)}</span>
    </div>)}</div>
  </div>
}

export function QualityView() {
  const [data, setData] = useState<EvalAll | null>(null)
  const [error, setError] = useState('')
  const [benchInfo, setBenchInfo] = useState(false)
  useEffect(() => { let cancelled = false; api<EvalAll>('/eval/metrics/all').then(d => { if (!cancelled) setData(d) }).catch(e => { if (!cancelled) setError(e.message) }); return () => { cancelled = true } }, [])

  if (error) return <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{error}</p>
  if (!data) return <p role="status" className="rounded-xl bg-white p-5 text-sm">Đang tải chỉ số…</p>
  const byKey = Object.fromEntries(data.metrics.map(m => [m.key, m]))
  const { tp, fp, fn, tn } = data.confusion
  const failed = data.metrics.filter(m => m.passed === false)
  const judged = data.metrics.filter(m => m.passed !== null)
  return <>
    <section>
      <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-sky-600">Evaluation</p>
      <h2 className="text-xl font-extrabold tracking-tight sm:text-2xl">Chất lượng phát hiện tương tác</h2>
      <p className="mt-1.5 text-sm text-slate-500">Gộp {data.n_cases} ca từ {data.runs.length} lượt test ({data.runs.map(r => r.label).join(' + ')}) · tính lúc {stamp(data.generated)}</p>
      <p className="mt-1 text-sm text-slate-500">Số lớn trên mỗi thẻ là kết quả gộp mọi ca; dòng dưới ghi từng lượt và trung bình cộng. Đạt {judged.length - failed.length}/{judged.length} chỉ số có ngưỡng. Bấm <Info className="inline size-3.5 align-[-2px]" /> để xem chú thích.</p>
    </section>

    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">{HEADLINE.map(key => byKey[key] && <MetricCard key={key} metric={byKey[key]} runs={data.runs} big />)}</div>

    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-2">
        <div><h3 className="text-sm font-extrabold">So với benchmark đã công bố</h3><p className="mt-1 text-xs text-slate-400">Xếp từ cao xuống thấp · <span className="font-semibold text-sky-600">xanh</span>: Rà Thuốc · <span className="font-semibold text-slate-500">xám</span>: 9 phần mềm tra tương tác đang lưu hành (Marcath 2018, 145 cặp) · <span className="font-semibold text-amber-600">vàng</span>: chatbot AI (Al-Ashwal 2023, 255 cặp, chuẩn Drugs.com)</p></div>
        <InfoButton open={benchInfo} onClick={() => setBenchInfo(!benchInfo)} label="So với benchmark" />
      </div>
      {benchInfo && <p className="mt-3 rounded-lg bg-sky-50 p-2.5 text-xs leading-relaxed text-slate-700">Các con số tham chiếu được đo trên bộ ca khác, với đáp án do dược sĩ lâm sàng xác định. Đáp án của Rà Thuốc lấy từ chính CSDL mà agent tra cứu, nên bài đo của chúng tôi dễ hơn. Biểu đồ dùng để định vị, không phải bằng chứng rằng hệ thống tốt hơn hay kém hơn các công cụ này.</p>}
      <div className="mt-4 grid gap-6 md:grid-cols-2 xl:grid-cols-3">{COMPARE.map(c => <BenchmarkChart key={c.key} label={c.label} field={c.key} ours={byKey[c.key]} benchmarks={data.benchmarks} />)}</div>
    </section>

    {GROUPS.map(group => <section key={group.title}>
      <h3 className="text-sm font-extrabold">{group.title}</h3><p className="mt-1 text-xs text-slate-400">{group.hint}</p>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">{group.keys.map(key => byKey[key] && <MetricCard key={key} metric={byKey[key]} runs={data.runs} />)}</div>
    </section>)}

    <div className="grid gap-7 xl:grid-cols-2">
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-extrabold">Bảng nhầm lẫn (gộp {data.n_cases} ca)</h3><p className="mt-1 text-xs text-slate-400">Đếm theo từng cặp thuốc, thuốc - thực phẩm, thuốc - bệnh nền</p>
        <div className="mt-4 grid grid-cols-2 gap-2 text-center">{([['Phát hiện đúng (TP)', tp, 'bg-emerald-50 text-emerald-700'], ['Bỏ sót (FN)', fn, 'bg-rose-50 text-rose-700'], ['Cảnh báo thừa (FP)', fp, 'bg-amber-50 text-amber-700'], ['Không cảnh báo, đúng (TN)', tn, 'bg-slate-50 text-slate-600']] as const).map(([label, value, tone]) => <div key={label} className={`rounded-lg p-4 ${tone}`}><p className="text-2xl font-extrabold">{value}</p><p className="mt-1 text-[11px] font-semibold">{label}</p></div>)}</div>
        <div className="mt-4 space-y-1 text-xs text-slate-500">{data.runs.map(r => <p key={r.id}><span className="font-bold text-slate-700">{r.label}:</span> TP {r.confusion.tp} · FP {r.confusion.fp} · FN {r.confusion.fn} · TN {r.confusion.tn}</p>)}</div>
      </section>
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-extrabold">Ca cần xem lại</h3><p className="mt-1 text-xs text-slate-400">Các ca còn bỏ sót hoặc cảnh báo thừa, theo từng lượt</p>
        <div className="mt-4 space-y-4">{data.runs.map(r => <div key={r.id}>
          <p className="text-xs font-bold text-slate-700">{r.label}</p><p className="mt-0.5 text-[11px] text-slate-400">{r.note}</p>
          <div className="mt-2 space-y-1.5">{r.review_cases.length === 0 && <p className="text-xs text-slate-500">Không có ca nào.</p>}{r.review_cases.map(c => <div key={c.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs"><span className="font-bold text-slate-700">{c.id} <span className="font-normal text-slate-400">· {c.category}</span></span><span className="text-slate-500">bỏ sót {c.fn} · thừa {c.fp}</span></div>)}</div>
          {r.db_gaps.length > 0 && <p className="mt-2 text-[11px] leading-relaxed text-amber-700">CSDL chưa có bản ghi cho {r.db_gaps.length} ca mà người viết kỳ vọng có cảnh báo ({r.db_gaps.join(', ')}). Agent báo "chưa có bản ghi" là đúng theo CSDL, nhưng đây là lỗ hổng độ phủ dữ liệu.</p>}
        </div>)}</div>
      </section>
    </div>
    <p className="text-xs leading-relaxed text-slate-500">Đáp án của cả hai bộ ca lấy từ chính CSDL của hệ thống và chưa được dược sĩ thẩm định, nên các chỉ số đo việc agent truy xuất đúng CSDL, chưa đo tính đúng về lâm sàng. Chạy lại bằng <code>eval/predict.py</code> và <code>eval/compare_runs.py</code> sau mỗi lần đổi dữ liệu hoặc logic.</p>
  </>
}
