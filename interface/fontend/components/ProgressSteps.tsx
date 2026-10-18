'use client'

import { useEffect, useState } from 'react'
import { Check, Loader2 } from 'lucide-react'

import type { ProgressStage } from '@/lib/api'

// Các bước backend gửi qua SSE. Kết quả không hiện dần từng chữ vì phải qua kiểm trích dẫn trước khi gửi.
export function ProgressSteps({ title, stages, note, className = '' }: { title: string; stages: ProgressStage[]; note: string; className?: string }) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const started = Date.now()
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const current = stages.length - 1
  return <div role="status" className={`rounded-2xl border border-teal-200 bg-white px-4 py-3 text-xs text-slate-500 ${className}`}>
    <div className="flex items-center justify-between gap-3 font-semibold text-slate-600"><span className="flex items-center gap-2"><Loader2 className="size-4 animate-spin text-teal-500" /> {title}</span><span aria-hidden="true" className="tabular-nums text-slate-400">{elapsed} giây</span></div>
    {stages.length > 0 && <ol className="mt-2 space-y-1.5">{stages.map((item, index) => <li key={`${item.stage}-${index}`} className={`flex items-center gap-2 ${index === current ? 'font-semibold text-teal-700' : 'text-slate-400'}`}>{index === current ? <span className="size-3.5 shrink-0 animate-pulse rounded-full border-2 border-teal-500" /> : <Check className="size-3.5 shrink-0 text-teal-500" />}{item.label}</li>)}</ol>}
    <p className="mt-2 border-t border-slate-100 pt-2 text-[11px] text-slate-400">{note}</p>
  </div>
}
