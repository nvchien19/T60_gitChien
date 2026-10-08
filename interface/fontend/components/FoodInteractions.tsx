'use client'

import { useState } from 'react'
import { Apple, ExternalLink } from 'lucide-react'
import type { CheckRecord } from '@/lib/api'

export function FoodInteractions({ record }: { record: CheckRecord | null }) {
  const [drug, setDrug] = useState('')
  const findings = record?.food_findings || []
  const drugs = [...new Set(findings.map(row => row.pair[0]))]
  const selected = drugs.includes(drug) ? drug : ''
  const visible = findings.filter(row => !selected || row.pair[0] === selected)
  return <section aria-labelledby="food-title" className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h3 id="food-title" className="flex items-center gap-2 text-base font-extrabold"><Apple className="size-5 text-emerald-600" /> Tương tác thuốc – thực phẩm</h3>
        <p className="mt-2 text-sm text-slate-500">Thực phẩm, đồ uống cần tránh hoặc điều chỉnh khi dùng từng thuốc.</p></div>
      <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800">{findings.length} lưu ý</span>
    </div>
    <p className="mt-3 text-xs leading-relaxed text-slate-500">Làm theo hướng dẫn của từng bản ghi: tránh dùng, giãn cách thời điểm hoặc duy trì lượng ăn ổn định. Không phải mọi thực phẩm được liệt kê đều cần kiêng hoàn toàn.</p>
    {!!record?.unknown?.length && <p className="mt-3 text-sm text-amber-700">Có thuốc chưa được nhận diện; phần thực phẩm chưa đánh giá được đầy đủ cho các thuốc này.</p>}
    {drugs.length > 1 && <label className="mt-4 block text-xs font-semibold text-slate-600">Lọc theo thuốc
      <select value={selected} onChange={event => setDrug(event.target.value)} className="mt-2 block w-full rounded-lg border border-slate-200 bg-white p-2 text-sm sm:max-w-sm">
        <option value="">Tất cả thuốc có lưu ý</option>{drugs.map(name => <option key={name} value={name}>{name}</option>)}
      </select>
    </label>}
    {!findings.length && <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">Chưa có bản ghi thuốc–thực phẩm trong lần kiểm tra này. Điều này không có nghĩa là mọi thực phẩm đều dùng được. Hãy kiểm tra lại với dược sĩ khi cần.</p>}
    <div className="mt-4 space-y-3">{visible.map((row, index) => <article key={`${row.pair.join('|')}-${index}`} className="rounded-xl border border-slate-200 p-4">
      <p className="text-xs font-bold text-sky-700">{row.pair[0]}</p>
      <h4 className="mt-1 break-words text-base font-bold">{row.pair[1]}</h4>
      {row.severity_vi && <p className="mt-1 text-xs text-slate-500">Mức độ theo nguồn: {row.severity_vi}</p>}
      <div className="mt-3 rounded-lg bg-amber-50 p-3 text-sm leading-relaxed text-amber-900"><p className="font-bold">Gợi ý sử dụng / cần tránh</p><p className="mt-1 whitespace-pre-line">{row.management || 'Nguồn chưa có hướng dẫn cụ thể. Trao đổi với dược sĩ trước khi thay đổi chế độ ăn.'}</p></div>
      {row.summary && <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-slate-600"><strong>Lý do: </strong>{row.summary}</p>}
      {!!row.untranslated_fields?.length && <p className="mt-2 text-xs text-amber-700">Một phần nội dung đang hiển thị nguyên văn nguồn, chưa có bản dịch tiếng Việt.</p>}
      {row.machine_translation && <p className="mt-2 text-xs text-slate-500">Bản dịch máy, chưa được chuyên gia duyệt.</p>}
      {(row.original_management || row.original_mechanism) && <details className="mt-3 text-xs text-slate-500"><summary className="cursor-pointer font-semibold">Xem nguyên văn nguồn</summary><p className="mt-2 whitespace-pre-line">{row.original_management}</p><p className="mt-2 whitespace-pre-line">{row.original_mechanism}</p></details>}
      <div className="mt-3 space-y-2 text-xs text-slate-500">{row.citations.map((citation, i) => <div key={i}>
        {/^https?:\/\//i.test(citation.source_url) ? <a href={citation.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-semibold text-sky-700 underline">Nguồn: {citation.source_name || citation.source_id}<ExternalLink className="size-3" /></a> : <span>Nguồn: {citation.source_name || citation.source_id}</span>}
        {citation.label && <details className="mt-1"><summary className="cursor-pointer">Tài liệu tham khảo</summary><p className="mt-2 break-words leading-relaxed">{citation.label}</p></details>}
      </div>)}</div>
    </article>)}</div>
  </section>
}
