'use client'

import { useEffect, useState } from 'react'
import { Bot, ChevronDown, ChevronRight, CircleHelp, FileText, Loader2, Minus, Paperclip, Send, ShieldCheck, Sparkles, X } from 'lucide-react'

import { api } from '@/lib/api'

type Message = { id: number; role: 'assistant' | 'user'; text: string; severity?: 'Nghiêm trọng' | 'Trung bình' | 'Nhẹ' }

const suggestions = ['Vì sao có tương tác?', 'Mức độ này có nghĩa là gì?', 'Tôi nên hỏi dược sĩ điều gì?']

export function MedicationAssistantWidget({ prescriptionId, checkId, open, onOpen, onClose }: { prescriptionId: string; checkId?: string; open: boolean; onOpen: () => void; onClose: () => void }) {
  const [minimized, setMinimized] = useState(false)
  const [draft, setDraft] = useState('')
  const [typing, setTyping] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [messages, setMessages] = useState<Message[]>([{ id: 1, role: 'assistant', text: `Xin chào! Tôi là trợ lý An toàn Thuốc. Tôi có thể giúp bạn hiểu kết quả kiểm tra của ${prescriptionId} và chuẩn bị câu hỏi cho dược sĩ.` }])

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => { if (event.key === 'Escape' && open) onClose() }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [open, onClose])

  const sendMessage = async (text = draft) => {
    const value = text.trim()
    if (!value || typing) return
    setMessages((items) => [...items, { id: Date.now(), role: 'user', text: value }])
    setDraft('')
    setTyping(true)
    try {
      const reply = await api<{ reply: string }>('/assistant/chat', { prescription_id: prescriptionId, check_id: checkId || '', message: value })
      setMessages(items => [...items, { id: Date.now() + 1, role: 'assistant', text: reply.reply }])
    } catch (e) {
      setMessages(items => [...items, { id: Date.now() + 1, role: 'assistant', text: (e as Error).message }])
    } finally { setTyping(false) }
  }

  const launcher = <button onClick={() => { setMinimized(false); onOpen() }} aria-label="Mở trợ lý An toàn Thuốc" className="fixed bottom-24 right-4 z-[9999] flex min-h-[48px] items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-xs font-bold text-white shadow-[0_12px_30px_rgba(15,23,42,0.2)] transition hover:-translate-y-0.5 hover:bg-slate-800 active:bg-slate-700 sm:right-5 lg:bottom-7 lg:right-8"><Bot className="size-4" /> Hỏi trợ lý</button>
  if (!open || minimized) return launcher

  return <>
    <div className="fixed inset-0 z-[9998] hidden bg-slate-900/10 max-[520px]:block" onClick={onClose} aria-hidden="true" />
    <section role="dialog" aria-label="Trợ lý An toàn Thuốc" className="fixed bottom-5 right-5 z-[9999] flex h-[min(680px,calc(100dvh-40px))] w-[min(480px,calc(100vw-40px))] flex-col overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22)] animate-in slide-in-from-bottom-4 duration-200 max-[520px]:bottom-0 max-[520px]:right-0 max-[520px]:h-[100dvh] max-[520px]:w-full max-[520px]:rounded-none">
      <header className="flex shrink-0 items-center gap-3 border-b border-slate-100 bg-white px-5 py-4"><div className="relative flex size-11 items-center justify-center rounded-2xl bg-sky-50 text-sky-600"><ShieldCheck className="size-6" /><span className="absolute -right-0.5 -top-0.5 size-3 rounded-full border-2 border-white bg-emerald-500" /></div><div className="min-w-0 flex-1"><h2 className="truncate text-sm font-extrabold text-slate-900">Trợ lý An toàn Thuốc</h2><p className="mt-0.5 truncate text-[11px] font-medium text-slate-400">Hỗ trợ đọc kết quả kiểm tra</p></div><button onClick={() => setMinimized(true)} aria-label="Thu nhỏ trợ lý" className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-50 hover:text-slate-700"><Minus className="size-4" /></button><button onClick={onClose} aria-label="Đóng trợ lý" className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"><X className="size-4" /></button></header>
      <div className="flex-1 space-y-4 overflow-y-auto bg-[#f7faff] px-4 py-5 sm:px-5"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400"><Sparkles className="size-3.5 text-sky-500" /> Hỗ trợ an toàn thuốc</div>{messages.map((message) => <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[88%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed ${message.role === 'user' ? 'rounded-br-md bg-sky-500 text-white shadow-sm' : 'rounded-bl-md border border-slate-200 bg-white text-slate-600 shadow-[0_2px_8px_rgba(15,23,42,0.03)]'}`}>{message.text}{message.severity && <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-bold text-amber-800"><div className="flex items-center gap-2"><CircleHelp className="size-4" /> Mức độ: {message.severity}</div><p className="mt-1 font-medium text-amber-700">Cần xác nhận với chuyên gia y tế.</p></div>}</div></div>)}{messages.length === 1 && <div className="space-y-2 pt-1"><p className="text-[11px] font-bold text-slate-400">Gợi ý câu hỏi</p>{suggestions.map((suggestion) => <button key={suggestion} onClick={() => sendMessage(suggestion)} className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-left text-xs font-semibold text-slate-600 transition hover:border-sky-300 hover:text-sky-700"><span className="flex items-center gap-2"><CircleHelp className="size-3.5 text-sky-500" />{suggestion}</span><ChevronRight className="size-4 text-slate-300" /></button>)}</div>}{typing && <div className="flex items-center gap-2 text-xs font-medium text-slate-400"><Loader2 className="size-4 animate-spin text-sky-500" /> Trợ lý đang soạn trả lời...</div>}<button onClick={() => setExpanded(!expanded)} className="flex items-center gap-2 text-[11px] font-bold text-sky-600"><FileText className="size-3.5" /> Nguồn tham khảo <ChevronDown className={`size-3.5 transition ${expanded ? 'rotate-180' : ''}`} /></button>{expanded && <div className="rounded-xl border border-slate-200 bg-white p-3 text-[11px] leading-relaxed text-slate-500">Thông tin mang tính tham khảo, được tổng hợp từ hướng dẫn sử dụng thuốc. Luôn xác nhận với bác sĩ hoặc dược sĩ.</div>}</div>
      <div className="shrink-0 border-t border-slate-100 bg-white p-4"><div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2 transition focus-within:border-sky-400 focus-within:ring-2 focus-within:ring-sky-100"><button aria-label="Đính kèm tệp" className="rounded-xl p-2 text-slate-400 hover:bg-white hover:text-sky-600"><Paperclip className="size-4" /></button><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); sendMessage() } }} rows={1} placeholder="Nhập câu hỏi về thuốc..." className="max-h-24 min-h-9 flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none placeholder:text-slate-400" /><button onClick={() => sendMessage()} disabled={!draft.trim() || typing} aria-label="Gửi tin nhắn" className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-sky-500 text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:opacity-40"><Send className="size-4" /></button></div><p className="mt-2 text-center text-[10px] text-slate-400">Không thay thế chẩn đoán hoặc chỉ định y khoa</p></div>
    </section>
  </>
}
