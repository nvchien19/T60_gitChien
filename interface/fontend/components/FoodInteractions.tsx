'use client'

import { useEffect, useRef, useState } from 'react'
import { Apple, ChevronRight, ExternalLink, X } from 'lucide-react'
import type { CheckRecord, FoodFinding } from '@/lib/api'

export function FoodInteractions({ record }: { record: CheckRecord | null }) {
  const [drug, setDrug] = useState('')
  const [active, setActive] = useState<FoodFinding | null>(null)
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
    {drugs.length > 1 && <div><label htmlFor="food-drug-filter" className="mt-4 block text-xs font-semibold text-slate-600">Lọc theo thuốc</label>
      <select id="food-drug-filter" value={selected} onChange={event => setDrug(event.target.value)} className="mt-2 block w-full rounded-lg border border-slate-200 bg-white p-2 text-sm sm:max-w-sm">
        <option value="">Tất cả thuốc có lưu ý</option>{drugs.map(name => <option key={name} value={name}>{name}</option>)}
      </select>
    </div>}
    {!findings.length && <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">Chưa có bản ghi thuốc–thực phẩm trong lần kiểm tra này. Điều này không có nghĩa là mọi thực phẩm đều dùng được. Hãy kiểm tra lại với dược sĩ khi cần.</p>}
    <div className="mt-4 space-y-3">{visible.map((row, index) => <button type="button" key={`${row.pair.join('|')}-${index}`} onClick={() => setActive(row)} className="flex w-full items-center gap-4 rounded-xl border border-slate-200 p-4 text-left transition hover:border-sky-300 hover:shadow-sm focus-visible:outline-2 focus-visible:outline-sky-500">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-words text-sm font-extrabold">{row.pair[0]} <span className="font-normal text-slate-300">↕</span> {row.pair[1]}</p>
          {row.severity_vi && <span className="rounded-md bg-amber-50 px-2 py-1 text-[11px] font-bold text-amber-800">{row.severity_vi}</span>}
        </div>
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-500">Thuốc – thực phẩm · {row.summary || row.management || 'Nguồn chưa có hướng dẫn cụ thể.'}</p>
        <p className="mt-2 text-[11px] font-semibold text-slate-400">{row.citations.length} nguồn bằng chứng · Xem chi tiết</p>
        {!!row.untranslated_fields?.length && <p className="mt-1 text-[11px] text-amber-700">Một số nội dung chưa có bản dịch tiếng Việt; đang hiển thị nguyên văn.</p>}
        {row.machine_translation && <p className="mt-1 text-[11px] text-slate-500">Bản dịch tự động, chưa được rà soát chuyên môn.</p>}
      </div>
      <ChevronRight aria-hidden="true" className="size-4 shrink-0 text-slate-300" />
    </button>)}</div>
    {active && <FoodDetail row={active} onClose={() => setActive(null)} />}

  </section>
}

function FoodDetail({ row, onClose }: { row: FoodFinding; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null
    dialog.current?.showModal()
    return () => { previousFocus?.focus() }
  }, [])
  return <dialog ref={dialog} onCancel={onClose} aria-labelledby="food-detail-title" className="m-auto max-h-[92dvh] w-[calc(100%_-_32px)] max-w-lg bg-transparent p-0 backdrop:bg-slate-950/25 backdrop:backdrop-blur-sm">
    <div className="flex max-h-[92dvh] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
      <div className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-100 p-4 sm:p-6">
        <h2 id="food-detail-title" className="text-lg font-extrabold">Chi tiết tương tác thuốc – thực phẩm</h2>
        <button type="button" onClick={onClose} aria-label="Đóng chi tiết tương tác thực phẩm" className="rounded-lg p-2 text-slate-500 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-sky-500"><X className="size-5" /></button>
      </div>
      <div className="overflow-y-auto overscroll-contain p-4 sm:p-6">
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

      </div>
    </div>
  </dialog>
}
