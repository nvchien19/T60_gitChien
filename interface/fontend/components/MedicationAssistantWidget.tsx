'use client'

import { BrandLogo } from '@/components/BrandLogo'
import { AssistantMessageText } from '@/components/AssistantMessageText'
import { useEffect, useRef, useState } from 'react'
import { Bot, ChevronRight, CircleHelp, Loader2, Minus, Send, Sparkles, X } from 'lucide-react'

import { api, type AssistantReply, type AssistantUsage, type Citation } from '@/lib/api'

type History = { role: 'assistant' | 'user'; content: string }[]

type Message = { id: number; role: 'assistant' | 'user'; text: string; usage?: AssistantUsage; question?: string; history?: History; citations?: Citation[]; disclaimer?: string; severity?: 'Nghiêm trọng' | 'Trung bình' | 'Nhẹ' }

const suggestions = ['Vì sao có tương tác?', 'Mức độ này có nghĩa là gì?', 'Thực phẩm giàu vitamin K gồm những gì?']

export function MedicationAssistantWidget({ prescriptionId, checkId, open, onOpen, onClose }: { prescriptionId: string; checkId?: string; open: boolean; onOpen: () => void; onClose: () => void }) {
  const [minimized, setMinimized] = useState(false)
  const [draft, setDraft] = useState('')
  const [typing, setTyping] = useState(false)
  const generation = useRef(0)
  const sending = useRef(false)
  const bottom = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Message[]>([{ id: 1, role: 'assistant', text: `Xin chào! Tôi là trợ lý An toàn Thuốc. Tôi có thể giúp bạn hiểu kết quả kiểm tra của ${prescriptionId}, tìm hiểu thực phẩm cung cấp vitamin/khoáng chất và chuẩn bị câu hỏi cho dược sĩ.` }])

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => { if (event.key === 'Escape' && open) onClose() }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [open, onClose])

  useEffect(() => {
    generation.current += 1
    sending.current = false
    setTyping(false)
    setDraft('')
    setMessages([{ id: Date.now(), role: 'assistant', text: `Tôi hỗ trợ tra cứu thuốc và tìm hiểu thực phẩm cung cấp vitamin/khoáng chất. Để hỏi về kết quả của ${prescriptionId}, hãy chạy kiểm tra đơn trước; câu hỏi dinh dưỡng phổ thông có thể hỏi ngay.` }])
    return () => { generation.current += 1 }
  }, [prescriptionId, checkId])

  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest' }) }, [messages, typing, open])

  const sendMessage = async (text = draft, detail: 'brief' | 'expanded' = 'brief', selected?: Message) => {
    const value = text.trim()
    if (!value || sending.current || value.length > 5000) return
    sending.current = true
    const requestGeneration = generation.current
    const history: History = selected?.history ?? messages.filter(item => item.role === 'user' || item.citations?.length).slice(-8).map(item => ({ role: item.role, content: item.text.slice(0, 3000) }))
    setMessages((items) => [...items, { id: Date.now(), role: 'user', text: detail === 'expanded' ? `Giải thích thêm: ${value}` : value }])
    setDraft('')
    setTyping(true)
    try {
      const reply = await api<AssistantReply>('/assistant/chat', { prescription_id: prescriptionId, check_id: checkId || '', message: value, history, detail })
      if (requestGeneration !== generation.current) return
      setMessages(items => [...items, { id: Date.now() + 1, role: 'assistant', text: reply.reply, usage: reply.usage, question: value, history, citations: reply.citations, disclaimer: reply.disclaimer }])
    } catch (e) {
      if (requestGeneration !== generation.current) return
      setMessages(items => [...items, { id: Date.now() + 1, role: 'assistant', text: (e as Error).message }])
    } finally { if (requestGeneration === generation.current) { sending.current = false; setTyping(false) } }
  }

  const launcher = <button onClick={() => { setMinimized(false); onOpen() }} aria-label="Mở trợ lý An toàn Thuốc" className="fixed bottom-24 right-4 z-[9999] flex min-h-[48px] items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-xs font-bold text-white shadow-[0_12px_30px_rgba(15,23,42,0.2)] transition hover:-translate-y-0.5 hover:bg-slate-800 active:bg-slate-700 sm:right-5 lg:bottom-7 lg:right-8"><Bot className="size-4" /> Hỏi trợ lý</button>
  if (!open || minimized) return launcher

  return <>
    <div className="fixed inset-0 z-[9998] hidden bg-slate-900/10 max-[520px]:block" onClick={onClose} aria-hidden="true" />
    <section role="dialog" aria-label="Trợ lý An toàn Thuốc" className="fixed bottom-5 right-5 z-[9999] flex h-[min(680px,calc(100dvh-40px))] w-[min(480px,calc(100vw-40px))] flex-col overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22)] animate-in slide-in-from-bottom-4 duration-200 max-[520px]:bottom-0 max-[520px]:right-0 max-[520px]:h-[100dvh] max-[520px]:w-full max-[520px]:rounded-none">
      <header className="flex shrink-0 items-center gap-3 border-b border-slate-100 bg-white px-5 py-4"><div className="relative flex size-11 items-center justify-center rounded-2xl bg-teal-50 text-teal-600"><BrandLogo size={34} /><span className="absolute -right-0.5 -top-0.5 size-3 rounded-full border-2 border-white bg-emerald-500" /></div><div className="min-w-0 flex-1"><h2 className="truncate text-sm font-extrabold text-slate-900">Trợ lý An toàn Thuốc</h2><p className="mt-0.5 truncate text-[11px] font-medium text-slate-400">Hỗ trợ thuốc và dinh dưỡng phổ thông</p></div><button onClick={() => setMinimized(true)} aria-label="Thu nhỏ trợ lý" className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-50 hover:text-slate-700"><Minus className="size-4" /></button><button onClick={onClose} aria-label="Đóng trợ lý" className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"><X className="size-4" /></button></header>
      <div role="log" aria-live="polite" aria-relevant="additions" className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain bg-[#f3f8f7] px-4 py-5 sm:px-5"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400"><Sparkles className="size-3.5 text-teal-500" /> Hỗ trợ an toàn thuốc</div>{messages.map((message) => <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[88%] rounded-2xl px-4 py-3 whitespace-pre-wrap break-words text-[13px] leading-relaxed ${message.role === 'user' ? 'rounded-br-md bg-teal-500 text-white shadow-sm' : 'rounded-bl-md border border-slate-200 bg-white text-slate-600 shadow-[0_2px_8px_rgba(15,23,42,0.03)]'}`}>{message.role === 'assistant' ? <AssistantMessageText text={message.text} /> : message.text}{message.role === 'assistant' && message.question && <button type="button" disabled={typing} onClick={() => sendMessage(message.question, 'expanded', message)} className="mt-3 block rounded px-1 py-1 text-xs font-semibold text-teal-700 underline underline-offset-4 hover:text-teal-900 focus-visible:outline-2 focus-visible:outline-teal-500 disabled:opacity-40">Giải thích thêm</button>}{message.citations && message.citations.length > 0 && <details className="mt-3 border-t border-slate-200 pt-2"><summary className="cursor-pointer text-xs font-bold text-teal-700">Nguồn tham khảo ({message.citations.length})</summary><ol className="mt-2 space-y-2 text-xs">{message.citations.map((cite, index) => <li key={`${cite.source_id}-${index}`}>[{index + 1}] {/^https?:\/\//i.test(cite.source_url) ? <a href={cite.source_url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">{cite.source_name || cite.source_id}</a> : <span>{cite.source_name || cite.source_id}</span>}</li>)}</ol></details>}{message.usage && <details className="mt-3 border-t border-slate-200 pt-2 text-xs"><summary className="cursor-pointer font-semibold text-slate-500">Token và chi phí AI</summary><p className="mt-2">{message.usage.api_calls} lượt gọi AI · {message.usage.input_tokens.toLocaleString('vi-VN')} token vào · {message.usage.output_tokens.toLocaleString('vi-VN')} token ra</p><p className="mt-1">{!message.usage.measured ? 'Chưa nhận đủ số liệu token từ nhà cung cấp.' : message.usage.cost_usd_min === null || message.usage.cost_usd_max === null ? 'Chưa có giá xác minh cho model của lượt hỏi này.' : `Chi phí tham khảo: $${message.usage.cost_usd_min.toFixed(6)}–$${message.usage.cost_usd_max.toFixed(6)} USD, tùy khung giờ (giá ngày ${message.usage.pricing_date}).`}</p></details>}{message.disclaimer && <p className="mt-3 border-t border-slate-200 pt-2 text-[10px] text-slate-500">{message.disclaimer}</p>}{message.severity && <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-bold text-amber-800"><div className="flex items-center gap-2"><CircleHelp className="size-4" /> Mức độ: {message.severity}</div><p className="mt-1 font-medium text-amber-700">Cần xác nhận với chuyên gia y tế.</p></div>}</div></div>)}{messages.length === 1 && <div className="space-y-2 pt-1"><p className="text-[11px] font-bold text-slate-400">Gợi ý câu hỏi</p>{suggestions.map((suggestion) => <button key={suggestion} onClick={() => sendMessage(suggestion)} className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-left text-xs font-semibold text-slate-600 transition hover:border-teal-300 hover:text-teal-700"><span className="flex items-center gap-2"><CircleHelp className="size-3.5 text-teal-500" />{suggestion}</span><ChevronRight className="size-4 text-slate-300" /></button>)}</div>}{typing && <div className="flex items-center gap-2 text-xs font-medium text-slate-400"><Loader2 className="size-4 animate-spin text-teal-500" /> Trợ lý đang soạn trả lời...</div>}<div ref={bottom} /></div>
      <div className="shrink-0 border-t border-slate-100 bg-white p-4"><div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2 transition focus-within:border-teal-400 focus-within:ring-2 focus-within:ring-teal-100"><textarea aria-label="Câu hỏi về thuốc hoặc nguồn thực phẩm cung cấp chất dinh dưỡng" maxLength={5000} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); sendMessage() } }} rows={1} placeholder="Hỏi về thuốc hoặc thực phẩm..." className="max-h-24 min-h-9 flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none placeholder:text-slate-400" /><button onClick={() => sendMessage()} disabled={!draft.trim() || typing} aria-label="Gửi tin nhắn" className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-teal-500 text-white transition hover:bg-teal-600 disabled:cursor-not-allowed disabled:opacity-40"><Send className="size-4" /></button></div><p className="mt-2 text-center text-[10px] text-slate-400">Không thay thế chẩn đoán hoặc chỉ định y khoa</p></div>
    </section>
  </>
}
