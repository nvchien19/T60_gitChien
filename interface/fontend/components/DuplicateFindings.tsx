'use client'

import { Copy, ExternalLink } from 'lucide-react'
import type { CheckRecord } from '@/lib/api'

// Trùng hoạt chất (hai tên trên đơn cùng chứa một hoạt chất) và trùng nhóm điều trị. Ẩn khi không có.
export function DuplicateFindings({ record }: { record: CheckRecord | null }) {
  const findings = record?.duplicate_findings || []
  if (!findings.length) return null
  return <section aria-labelledby="dup-title" className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h3 id="dup-title" className="flex items-center gap-2 text-base font-extrabold"><Copy className="size-5 text-violet-600" /> Trùng hoạt chất, trùng nhóm điều trị</h3>
        <p className="mt-2 text-sm text-slate-500">Dùng chung có thể làm tổng lượng hoạt chất vượt mức. Cần dược sĩ xem lại đơn.</p></div>
      <span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-bold text-violet-800">{findings.length} lưu ý</span>
    </div>
    <ul className="mt-4 space-y-3">{findings.map((row, index) => <li key={`${row.pair.join('|')}-${index}`} className="rounded-xl border border-slate-200 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="break-words text-sm font-extrabold">{row.pair.join(' = ')}</p>
        <span className="rounded-md bg-violet-50 px-2 py-1 text-[11px] font-bold text-violet-800">= {row.severity_vi}</span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-600">{row.summary}</p>
      {!!row.citations.length && <p className="mt-2 text-[11px] text-slate-400">Nguồn: {row.citations.map((c, i) => <span key={`${c.source_id}-${i}`}>{i > 0 && ', '}{c.source_url ? <a href={c.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 underline">{c.source_name || c.source_id}<ExternalLink className="size-3" /></a> : (c.label || c.source_name || c.source_id)}</span>)}</p>}
    </li>)}</ul>
  </section>
}
