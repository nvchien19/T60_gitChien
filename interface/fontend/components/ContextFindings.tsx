'use client'

import { useEffect, useRef, useState } from 'react'
import { ChevronRight, Dna, ExternalLink, HeartPulse, X } from 'lucide-react'
import type { CheckRecord, ContextFinding } from '@/lib/api'

type Kind = 'disease' | 'gene'

const TEXT = {
  disease: {
    title: 'Tương tác thuốc – bệnh nền',
    intro: 'Bản ghi của nguồn dữ liệu về thuốc trong đơn với các bệnh nền đã khai.',
    none: 'Chưa có bản ghi thuốc–bệnh nền cho các bệnh đã khai. Điều này không có nghĩa là thuốc phù hợp với bệnh nhân; nguồn dữ liệu không phủ hết mọi cặp.',
    undeclared: 'Chưa khai bệnh nền cho đơn này nên phần này chưa được tra.',
    detail: 'Chi tiết thuốc – bệnh nền',
  },
  gene: {
    title: 'Thuốc – kiểu gen (dược lý di truyền)',
    intro: 'Khuyến cáo của CPIC ứng với kết quả xét nghiệm gen đã khai. CPIC viết cho người kê đơn; đây là thông tin tham khảo có nguồn, không phải chỉ định điều trị.',
    none: 'CPIC không có khuyến cáo ứng với thuốc trong đơn và kết quả gen đã khai.',
    undeclared: 'Chưa khai kết quả xét nghiệm gen cho đơn này nên phần này chưa được tra.',
    detail: 'Chi tiết thuốc – kiểu gen',
  },
}

const tone = (row: ContextFinding) => row.severity === 'contraindicated' || row.severity === 'major' ? 'bg-rose-50 text-rose-800' : row.severity === 'pgx' ? 'bg-violet-50 text-violet-800' : 'bg-amber-50 text-amber-800'

export function ContextFindings({ record }: { record: CheckRecord | null }) {
  if (!record) return null
  const context = record.patient_context
  return <>
    <Section kind="disease" rows={record.disease_findings || []} declared={!!context?.conditions?.length} />
    <Section kind="gene" rows={record.gene_findings || []} declared={!!Object.keys(context?.genes || {}).length} />
  </>
}

function Section({ kind, rows, declared }: { kind: Kind; rows: ContextFinding[]; declared: boolean }) {
  const [active, setActive] = useState<ContextFinding | null>(null)
  const text = TEXT[kind]
  const Icon = kind === 'disease' ? HeartPulse : Dna
  return <section aria-labelledby={`${kind}-title`} className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h3 id={`${kind}-title`} className="flex items-center gap-2 text-base font-extrabold"><Icon className={`size-5 ${kind === 'disease' ? 'text-rose-500' : 'text-violet-600'}`} /> {text.title}</h3>
        <p className="mt-2 text-sm text-slate-500">{text.intro}</p></div>
      <div className="flex items-center gap-2"><span className="rounded-full bg-violet-50 px-3 py-1 text-[11px] font-bold text-violet-700">Thử nghiệm</span>
        <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800">{rows.length} lưu ý</span></div>
    </div>
    <p className="mt-3 text-xs leading-relaxed text-slate-500">Dữ liệu chưa được dược sĩ thẩm định. Mọi thay đổi về thuốc cần theo chỉ định của bác sĩ.</p>
    {!rows.length && <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">{declared ? text.none : text.undeclared}</p>}
    <div className="mt-4 space-y-3">{rows.map((row, index) => <button type="button" key={`${row.pair.join('|')}-${index}`} onClick={() => setActive(row)} className="flex w-full items-center gap-4 rounded-xl border border-slate-200 p-4 text-left transition hover:border-teal-300 hover:shadow-sm focus-visible:outline-2 focus-visible:outline-teal-500">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-words text-sm font-extrabold">{row.pair[0]} <span className="font-normal text-slate-300">↕</span> {row.pair[1]}</p>
          {row.severity_vi && <span className={`rounded-md px-2 py-1 text-[11px] font-bold ${tone(row)}`}>{row.severity_vi}</span>}
          {row.details?.same_as_normal === true && <span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-600">Giống khuyến cáo cho kiểu gen bình thường</span>}
        </div>
        {!!row.details?.populations?.length && <p className="mt-2 text-[11px] text-slate-500">Nhóm bệnh nhân (theo CPIC): {row.details.populations.join('; ')}</p>}
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-500">{kind === 'gene' ? row.management || row.summary : row.summary}</p>
        <p className="mt-2 text-[11px] font-semibold text-slate-400">Nguồn: {[...new Set(row.citations.map(c => c.source_name || c.source_id))].join(', ')} · Xem chi tiết</p>
        {row.machine_translation && <p className="mt-1 text-[11px] text-slate-500">Bản dịch tự động, chưa được rà soát chuyên môn.</p>}
        {!!row.untranslated_fields?.length && <p className="mt-1 text-[11px] text-amber-700">Một số nội dung chưa có bản dịch tiếng Việt; đang hiển thị nguyên văn.</p>}
      </div>
      <ChevronRight aria-hidden="true" className="size-4 shrink-0 text-slate-300" />
    </button>)}</div>
    {active && <Detail kind={kind} row={active} onClose={() => setActive(null)} />}
  </section>
}

function Detail({ kind, row, onClose }: { kind: Kind; row: ContextFinding; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null
    dialog.current?.showModal()
    return () => { previousFocus?.focus() }
  }, [])
  const details = row.details || {}
  return <dialog ref={dialog} onCancel={onClose} aria-labelledby={`${kind}-detail-title`} className="m-auto max-h-[92dvh] w-[calc(100%_-_32px)] max-w-lg bg-transparent p-0 backdrop:bg-slate-950/25 backdrop:backdrop-blur-sm">
    <div className="flex max-h-[92dvh] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
      <div className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-100 p-4 sm:p-6">
        <h2 id={`${kind}-detail-title`} className="text-lg font-extrabold">{TEXT[kind].detail}</h2>
        <button type="button" onClick={onClose} aria-label="Đóng chi tiết" className="rounded-lg p-2 text-slate-500 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-teal-500"><X className="size-5" /></button>
      </div>
      <div className="overflow-y-auto overscroll-contain p-4 sm:p-6">
        <p className="text-xs font-bold text-teal-700">{row.pair[0]}</p>
        <h4 className="mt-1 break-words text-base font-bold">{row.pair[1]}{details.disease_en && details.disease_en !== row.pair[1] && <span className="font-normal text-slate-400"> · {details.disease_en}</span>}</h4>
        {kind === 'disease' && row.severity_vi && <p className="mt-1 text-xs text-slate-500">Mức độ theo nguồn: {row.severity_vi}</p>}
        {kind === 'gene' && <>
          {row.severity_vi && <p className="mt-1 text-xs text-slate-500">Độ mạnh của khuyến cáo theo CPIC: {row.severity_vi}</p>}
          {!!details.populations?.length && <p className="mt-1 text-xs text-slate-500">Nhóm bệnh nhân áp dụng (theo CPIC): {details.populations.join('; ')}</p>}
          {!!details.untested_genes?.length && <p className="mt-1 text-xs text-amber-700">Khuyến cáo này còn phụ thuộc gen chưa khai: {details.untested_genes.join(', ')}. Đang hiển thị trường hợp chưa có kết quả các gen đó.</p>}
          <div className="mt-3 rounded-lg bg-violet-50 p-3 text-sm leading-relaxed text-violet-950"><p className="font-bold">Khuyến cáo của CPIC cho người kê đơn</p><p className="mt-1 whitespace-pre-line">{row.management || 'CPIC không nêu khuyến cáo cho trường hợp này.'}</p></div>
          {details.same_as_normal === true && <p className="mt-2 text-xs text-slate-500">Khuyến cáo này trùng với khuyến cáo của CPIC cho người có kiểu gen bình thường.</p>}
        </>}
        {row.summary && <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-slate-600"><strong>{kind === 'gene' ? 'Ảnh hưởng theo nguồn: ' : 'Nội dung theo nguồn: '}</strong>{row.summary}</p>}
        {details.comments?.map((note, i) => <p key={i} className="mt-2 whitespace-pre-line text-xs leading-relaxed text-slate-500"><strong>Ghi chú của nguồn: </strong>{note}</p>)}
        {!!row.untranslated_fields?.length && <p className="mt-2 text-xs text-amber-700">Một phần nội dung đang hiển thị nguyên văn nguồn, chưa có bản dịch tiếng Việt.</p>}
        {row.machine_translation && <p className="mt-2 text-xs text-slate-500">Bản dịch máy, chưa được chuyên gia duyệt. Khi có khác biệt, nguyên văn nguồn là căn cứ.</p>}
        {(row.original_management || row.original_mechanism) && <details open={kind === 'gene'} className="mt-3 text-xs text-slate-500"><summary className="cursor-pointer font-semibold">Xem nguyên văn nguồn</summary><p className="mt-2 whitespace-pre-line">{row.original_management}</p><p className="mt-2 whitespace-pre-line">{row.original_mechanism}</p></details>}
        <div className="mt-3 space-y-2 text-xs text-slate-500">{row.citations.map((citation, i) => <div key={i}>
          {/^https?:\/\//i.test(citation.source_url) ? <a href={citation.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-semibold text-teal-700 underline">Nguồn: {citation.source_name || citation.source_id}<ExternalLink className="size-3" /></a> : <span>Nguồn: {citation.source_name || citation.source_id}</span>}
          {citation.label && <details className="mt-1"><summary className="cursor-pointer">Tài liệu tham khảo</summary><p className="mt-2 break-words leading-relaxed">{citation.label}</p></details>}
        </div>)}</div>
      </div>
    </div>
  </dialog>
}
