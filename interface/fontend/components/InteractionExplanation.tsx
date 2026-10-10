'use client'

import { useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import { explainPair, type PairExplanation } from '@/lib/api'

type State = { status: 'loading' } | { status: 'error'; message: string } | { status: 'done'; data: PairExplanation | null }

export function InteractionExplanation({ a, b }: { a: string; b: string }) {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    explainPair(a, b)
      .then(data => { if (!cancelled) setState({ status: 'done', data }) })
      .catch(e => { if (!cancelled) setState({ status: 'error', message: (e as Error).message }) })
    return () => { cancelled = true }
  }, [a, b])

  if (state.status === 'done' && !state.data) return null
  return <div>
    <h4 className="flex items-center gap-2 text-sm font-extrabold"><Sparkles className="size-4 text-sky-500" /> Giải thích bằng tiếng Việt</h4>
    {state.status === 'loading' && <p role="status" className="mt-2 animate-pulse text-sm text-slate-500">Đang diễn giải bản ghi và đối chiếu từng câu với nguồn…</p>}
    {state.status === 'error' && <p role="alert" className="mt-2 text-sm text-rose-600">Chưa lấy được lời giải thích. {state.message}</p>}
    {state.status === 'done' && state.data && <>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-600">{state.data.text}</p>
      {state.data.refs.length > 0 && <p className="mt-2 text-xs text-slate-500">{state.data.refs.map((ref, i) => <span key={i} className="block">[{i + 1}] {ref.label}{/^https?:\/\//.test(ref.url) && <a href={ref.url} target="_blank" rel="noreferrer" className="ml-2 text-sky-600 underline">Xem nguồn</a>}</span>)}</p>}
      <p className="mt-2 text-[11px] font-semibold text-slate-400">{state.data.source === 'llm' ? 'AI diễn giải từ bản ghi trong CSDL; từng câu đã được đối chiếu với nguồn. Thông tin tham khảo, cần người có chuyên môn xác nhận.' : 'Lời giải thích soạn sẵn từ bản ghi trong CSDL (không dùng AI).'}</p>
    </>}
  </div>
}
