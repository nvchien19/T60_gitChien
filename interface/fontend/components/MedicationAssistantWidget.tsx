'use client'

import { BrandLogo } from '@/components/BrandLogo'
import { AssistantMessageText } from '@/components/AssistantMessageText'
import { ProgressSteps } from '@/components/ProgressSteps'
import { recognizePrescriptionWithGemini } from '@/lib/prescription-gemini'
import { cleanOcrMedications } from '@/lib/prescription-ocr-clean'
import { preparePrescriptionImage } from '@/lib/prescription-ocr'
import { choosePrescriptionCandidate, prescriptionNeedsAnotherPass, type OcrPage } from '@/lib/prescription-layout'
import { extractPrescriptionText } from '@/lib/prescription-normalize'
import { useEffect, useRef, useState } from 'react'
import { Bot, ChevronRight, CircleHelp, Minus, Send, Sparkles, Upload, X } from 'lucide-react'

import { api, ApiError, askAssistant, type ProgressStage, type AssistantUsage, type Citation } from '@/lib/api'

type History = { role: 'assistant' | 'user'; content: string }[]

type Message = { id: number; role: 'assistant' | 'user'; text: string; usage?: AssistantUsage; question?: string; history?: History; citations?: Citation[]; disclaimer?: string; severity?: 'Chống chỉ định' | 'Nghiêm trọng' | 'Trung bình' | 'Nhẹ'; imageResult?: boolean; saved?: { prescriptionId: string; checkId: string } }
type ImageFinding = { pair: string[]; severity_vi: string; summary: string; citations: Citation[] }
type ImageCheck = { findings: ImageFinding[]; duplicate_findings: ImageFinding[]; food_findings: ImageFinding[]; unknown: { input: string }[]; no_record_pairs: string[][]; max_severity_vi: string; disclaimer: string }

const suggestions = ['Vì sao có tương tác?', 'Mức độ này có nghĩa là gì?', 'Thực phẩm giàu vitamin K gồm những gì?']

export function MedicationAssistantWidget({ prescriptionId, checkId, open, onOpen, onClose, onSaved, onView }: { prescriptionId: string; checkId?: string; open: boolean; onOpen: () => void; onClose: () => void; onSaved: () => Promise<void>; onView: (id: string, checkId: string) => void }) {
  const [minimized, setMinimized] = useState(false)
  const [draft, setDraft] = useState('')
  const [typing, setTyping] = useState(false)
  const [imageActivity, setImageActivity] = useState('')
  const [stages, setStages] = useState<ProgressStage[]>([])
  const pending = useRef<AbortController | null>(null)
  const generation = useRef(0)
  const sending = useRef(false)
  const imageRunning = useRef(false)
  const bottom = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Message[]>([{ id: 1, role: 'assistant', text: `Xin chào! Tôi là trợ lý An toàn Thuốc. Tôi có thể giúp bạn hiểu kết quả kiểm tra của ${prescriptionId}, tìm hiểu thực phẩm cung cấp vitamin/khoáng chất và chuẩn bị câu hỏi cho dược sĩ.` }])

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => { if (event.key === 'Escape' && open) onClose() }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [open, onClose])

  useEffect(() => {
    generation.current += 1
    pending.current?.abort()
    sending.current = false
    imageRunning.current = false
    setTyping(false)
    setImageActivity('')
    setDraft('')
    setMessages([{ id: Date.now(), role: 'assistant', text: `Tôi hỗ trợ tra cứu thuốc và tìm hiểu thực phẩm cung cấp vitamin/khoáng chất. Để hỏi về kết quả của ${prescriptionId}, hãy chạy kiểm tra đơn trước; câu hỏi dinh dưỡng phổ thông có thể hỏi ngay.` }])
    return () => { generation.current += 1; pending.current?.abort() }
  }, [prescriptionId, checkId])

  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest' }) }, [messages, typing, stages, open])

  const sendMessage = async (text = draft, detail: 'brief' | 'expanded' = 'brief', selected?: Message) => {
    const value = text.trim()
    if (!value || sending.current || value.length > 5000) return
    sending.current = true
    const requestGeneration = generation.current
    const imageContext = messages.slice().reverse().find(item => item.imageResult)
    const savedContext = imageContext?.saved
    const history: History = selected?.history ?? messages.filter(item => item.role === 'user' || item.citations?.length).slice(-8).map(item => ({ role: item.role, content: item.text.slice(0, 3000) }))
    setMessages((items) => [...items, { id: Date.now(), role: 'user', text: detail === 'expanded' ? `Giải thích thêm: ${value}` : value }])
    setDraft('')
    setStages([])
    setTyping(true)
    const controller = new AbortController()
    pending.current = controller
    try {
      const reply = await askAssistant({ prescription_id: imageContext ? savedContext?.prescriptionId || '' : prescriptionId, check_id: imageContext ? savedContext?.checkId || '' : checkId || '', message: value, history, detail }, stage => {
        if (requestGeneration === generation.current) setStages(items => items.at(-1)?.stage === stage.stage ? items : [...items, stage])
      }, controller.signal)
      if (requestGeneration !== generation.current) return
      setMessages(items => [...items, { id: Date.now() + 1, role: 'assistant', text: reply.reply, usage: reply.usage, question: value, history, citations: reply.citations, disclaimer: reply.disclaimer }])
    } catch (e) {
      if (requestGeneration !== generation.current) return
      setMessages(items => [...items, { id: Date.now() + 1, role: 'assistant', text: (e as Error).message }])
    } finally {
      if (pending.current === controller) pending.current = null
      if (requestGeneration === generation.current) { sending.current = false; setTyping(false); setStages([]) }
    }
  }

  const checkImage = async (file: File) => {
    if (imageRunning.current) return
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) {
      setMessages(items => [...items, { id: Date.now(), role: 'assistant', text: 'Chọn ảnh PNG, JPG hoặc WebP không quá 10 MB.' }])
      return
    }
    imageRunning.current = true
    const requestGeneration = generation.current
    const current = () => requestGeneration === generation.current
    setMessages(items => [...items, { id: Date.now(), role: 'user', text: `Kiểm tra ảnh đơn thuốc: ${file.name}` }])
    setImageActivity('Đang đọc ảnh bằng Gemini…')
    try {
      let extracted: ReturnType<typeof extractPrescriptionText>
      let candidate: { text: string; confidence: number } = { text: '', confidence: 0 }
      let provider = 'Gemini'
      let warnings: string[] = []
      let uncertain: string[] = []
      try {
        const result = await recognizePrescriptionWithGemini(file)
        if (!current()) return
        candidate = { text: result.raw_text, confidence: 100 }
        extracted = { name: result.name, medications: result.medications.map(item => ({
          name: item.name, dose: item.dose,
          frequency: [item.frequency, item.quantity ? `Số lượng: ${item.quantity}` : ''].filter(Boolean).join('; '),
        })), unparsedLines: [] }
        warnings = result.warnings
        uncertain = result.medications.flatMap((item, index) => item.uncertain_fields.length ? [`Thuốc ${index + 1} (${item.name}): ${item.uncertain_fields.join(', ')}`] : [])
      } catch (remoteError) {
        const unavailable = remoteError instanceof ApiError
          ? [429, 500, 502, 503, 504].includes(remoteError.status)
          : remoteError instanceof Error && remoteError.message.includes('Không kết nối được backend')
        if (!unavailable) throw remoteError
        if (!current()) return
        provider = 'OCR trên thiết bị (Gemini không khả dụng)'
        setImageActivity('Gemini không khả dụng; đang đọc ảnh trên thiết bị…')
        const canvas = await preparePrescriptionImage(file)
        const { createWorker, PSM } = await import('tesseract.js')
        const worker = await createWorker('vie+eng', 1, {
          workerPath: '/ocr/worker.min.js', corePath: '/ocr/core', langPath: '/ocr/lang', gzip: false,
        })
        try {
          await worker.setParameters({ preserve_interword_spaces: '1', user_defined_dpi: '300' })
          const pages: OcrPage[] = []
          for (const mode of [PSM.AUTO, PSM.SINGLE_COLUMN]) {
            await worker.setParameters({ tessedit_pageseg_mode: mode })
            pages.push((await worker.recognize(canvas, { rotateAuto: true }, { text: true, blocks: true })).data)
          }
          candidate = choosePrescriptionCandidate(pages)
          if (prescriptionNeedsAnotherPass(candidate.text, candidate.confidence)) {
            await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT })
            pages.push((await worker.recognize(canvas, { rotateAuto: true }, { text: true, blocks: true })).data)
            candidate = choosePrescriptionCandidate(pages)
          }
        } finally { await worker.terminate() }
        if (!current()) return
        extracted = extractPrescriptionText(candidate.text)
        warnings = extracted.unparsedLines
      }
      if (!current()) return
      const cleaned = cleanOcrMedications(extracted.medications)
      extracted.medications = cleaned.medications
      if (cleaned.rejected) warnings = [...warnings, `Đã bỏ ${cleaned.rejected} dòng không phải tên thuốc.`]
      const names = extracted.medications.map(item => item.name.trim()).filter(Boolean)
      if (!names.length) throw new Error('Chưa đọc được tên thuốc. Hãy thử ảnh rõ hơn hoặc nhập thủ công trong mục Đơn thuốc.')
      setImageActivity('Đang kiểm tra tương tác từ danh mục…')
      const result = await api<ImageCheck>('/interactions/check', { drugs: names })
      if (!current()) return
      const findings = [...result.findings, ...result.duplicate_findings, ...result.food_findings]
      const unknown = result.unknown.map(item => item.input)
      const matchedCount = Math.max(0, names.length - unknown.length)
      const numbered = candidate.text.split(/\r?\n/).map(line => line.match(/^\s*(\d{1,2})\s*[.)]\s*\p{L}/u)).filter(Boolean)
      const lastNumber = Math.max(0, ...numbered.map(match => Number(match![1])))
      const canSave = candidate.confidence >= 80 && !uncertain.length && !warnings.length && !unknown.length && (!lastNumber || lastNumber <= names.length)
      let saved: Message['saved']
      let saveNotice = 'OCR chưa đủ chắc chắn hoặc có tên thuốc chưa đối chiếu được; chưa tự lưu đơn.'
      if (canSave) {
        setImageActivity('Đang lưu đơn và ghi nhận lần kiểm tra…')
        try {
          const created = await api<{ id: string }>('/prescriptions', {
            name: `Đơn OCR cần đối chiếu ${new Date().toLocaleString('vi-VN')}`,
            medications: extracted.medications.map(item => ({ name: item.name.trim(), dose: item.dose, frequency: item.frequency, type: 'Kê đơn' })),
          })
          if (!current()) return
          try {
            const checked = await api<{ check_id: string }>(`/prescriptions/${created.id}/checks`, {})
            saved = { prescriptionId: created.id, checkId: checked.check_id }
            saveNotice = `Đã tự lưu đơn ${created.id} và lần kiểm tra ${checked.check_id}. Mở đơn để đối chiếu từng thuốc với ảnh gốc.`
          } catch (error) {
            saved = { prescriptionId: created.id, checkId: '' }
            saveNotice = `Đã lưu đơn ${created.id}, nhưng chưa ghi nhận được lần kiểm tra: ${error instanceof Error ? error.message : 'lỗi không xác định'}. Kết quả sơ bộ vẫn hiển thị bên dưới.`
          }
        } catch (error) {
          saveNotice = `Đã kiểm tra sơ bộ nhưng chưa lưu được đơn: ${error instanceof Error ? error.message : 'lỗi không xác định'}.`
        }
      }
      if (!current()) return
      const lines = [
        `Đã tự đọc bằng ${provider} và kiểm tra sơ bộ ${names.length} thuốc từ ảnh.`,
        `Tên nhận dạng: ${names.join(', ')}.`,
        `Đã đối chiếu được ${matchedCount}/${names.length} tên thuốc với danh mục.`,
        matchedCount ? `Tìm thấy ${findings.length} cảnh báo trong phần dữ liệu đối chiếu được${findings.length ? `; mức cao nhất: ${result.max_severity_vi}` : ''}. Không có cảnh báo không có nghĩa là an toàn.` : 'Chưa đối chiếu được thuốc nào, nên chưa thể đánh giá tương tác.',
        ...findings.slice(0, 8).map((item, index) => `${index + 1}. ${item.pair.join(' + ')} (${item.severity_vi}): ${item.summary}`),
        ...(findings.length > 8 ? [`Còn ${findings.length - 8} cảnh báo khác.`] : []),
        ...(unknown.length ? [`Chưa đối chiếu được: ${unknown.join(', ')}.`] : []),
        ...(candidate.confidence < 70 ? ['Ảnh được nhận dạng với độ tin cậy thấp. Cần kiểm tra lại toàn bộ tên thuốc.'] : []),
        ...(uncertain.length ? [`OCR chưa chắc chắn: ${uncertain.join('; ')}.`] : []),
        ...(warnings.length ? [`OCR có ${warnings.length} dòng hoặc trường cần đối chiếu với ảnh gốc.`] : []),
        ...(result.no_record_pairs.length ? [`Có ${result.no_record_pairs.length} cặp chưa có bản ghi; không thể kết luận là an toàn.`] : []),
        saveNotice,
        'Kết quả từ OCR chỉ để rà soát ban đầu. Hãy đối chiếu từng tên thuốc, hàm lượng và cách dùng với ảnh gốc trước khi sử dụng kết quả. Ảnh được gửi đến Google để nhận dạng bằng Gemini; tên thuốc nhận dạng được gửi đến API kiểm tra.',
      ]
      const citations = findings.flatMap(item => item.citations).filter((item, index, all) => all.findIndex(other => other.source_id === item.source_id && other.source_url === item.source_url) === index)
      setMessages(items => [...items, { id: Date.now() + 1, role: 'assistant', text: lines.join('\n\n'), citations, disclaimer: result.disclaimer, imageResult: true, saved }])
    } catch (error) {
      if (current()) setMessages(items => [...items, { id: Date.now() + 1, role: 'assistant', text: error instanceof Error ? error.message : 'Không xử lý được ảnh. Vui lòng thử lại.' }])
    } finally {
      if (current()) { imageRunning.current = false; setImageActivity('') }
    }
  }

  const latestSaved = messages.slice().reverse().find(item => item.saved)?.saved
  const launcher = <button onClick={() => { setMinimized(false); onOpen() }} aria-label="Mở trợ lý An toàn Thuốc" className="fixed bottom-24 right-4 z-[9999] flex min-h-[48px] items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-xs font-bold text-white shadow-[0_12px_30px_rgba(15,23,42,0.2)] transition hover:-translate-y-0.5 hover:bg-slate-800 active:bg-slate-700 sm:right-5 lg:bottom-7 lg:right-8"><Bot className="size-4" /> Hỏi trợ lý</button>
  if (!open || minimized) return launcher

  return <>
    <div className="fixed inset-0 z-[9998] hidden bg-slate-900/10 max-[520px]:block" onClick={onClose} aria-hidden="true" />
    <section role="dialog" aria-label="Trợ lý An toàn Thuốc" className="fixed bottom-5 right-5 z-[9999] flex h-[min(680px,calc(100dvh-40px))] w-[min(480px,calc(100vw-40px))] flex-col overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22)] animate-in slide-in-from-bottom-4 duration-200 max-[520px]:bottom-0 max-[520px]:right-0 max-[520px]:h-[100dvh] max-[520px]:w-full max-[520px]:rounded-none">
      <header className="flex shrink-0 items-center gap-3 border-b border-slate-100 bg-white px-5 py-4"><div className="relative flex size-11 items-center justify-center rounded-2xl bg-teal-50 text-teal-600"><BrandLogo size={34} /><span className="absolute -right-0.5 -top-0.5 size-3 rounded-full border-2 border-white bg-emerald-500" /></div><div className="min-w-0 flex-1"><h2 className="truncate text-sm font-extrabold text-slate-900">Trợ lý An toàn Thuốc</h2><p className="mt-0.5 truncate text-[11px] font-medium text-slate-400">Hỗ trợ thuốc và dinh dưỡng phổ thông</p></div><button onClick={() => setMinimized(true)} aria-label="Thu nhỏ trợ lý" className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-50 hover:text-slate-700"><Minus className="size-4" /></button><button onClick={onClose} aria-label="Đóng trợ lý" className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"><X className="size-4" /></button></header>
      <div role="log" aria-live="polite" aria-relevant="additions" className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain bg-[#f3f8f7] px-4 py-5 sm:px-5"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400"><Sparkles className="size-3.5 text-teal-500" /> Hỗ trợ an toàn thuốc</div>{messages.map((message) => <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[88%] rounded-2xl px-4 py-3 whitespace-pre-wrap break-words text-[13px] leading-relaxed ${message.role === 'user' ? 'rounded-br-md bg-teal-500 text-white shadow-sm' : 'rounded-bl-md border border-slate-200 bg-white text-slate-600 shadow-[0_2px_8px_rgba(15,23,42,0.03)]'}`}>{message.role === 'assistant' ? <AssistantMessageText text={message.text} /> : message.text}{message.role === 'assistant' && message.question && <button type="button" disabled={typing} onClick={() => sendMessage(message.question, 'expanded', message)} className="mt-3 block rounded px-1 py-1 text-xs font-semibold text-teal-700 underline underline-offset-4 hover:text-teal-900 focus-visible:outline-2 focus-visible:outline-teal-500 disabled:opacity-40">Giải thích thêm</button>}{message.citations && message.citations.length > 0 && <details className="mt-3 border-t border-slate-200 pt-2"><summary className="cursor-pointer text-xs font-bold text-teal-700">Nguồn tham khảo ({message.citations.length})</summary><ol className="mt-2 space-y-2 text-xs">{message.citations.map((cite, index) => <li key={`${cite.source_id}-${index}`}>[{index + 1}] {/^https?:\/\//i.test(cite.source_url) ? <a href={cite.source_url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">{cite.source_name || cite.source_id}</a> : <span>{cite.source_name || cite.source_id}</span>}</li>)}</ol></details>}{message.usage && <details className="mt-3 border-t border-slate-200 pt-2 text-xs"><summary className="cursor-pointer font-semibold text-slate-500">Token và chi phí AI</summary><p className="mt-2">{message.usage.api_calls} lượt gọi AI · {message.usage.input_tokens.toLocaleString('vi-VN')} token vào · {message.usage.output_tokens.toLocaleString('vi-VN')} token ra</p><p className="mt-1">{!message.usage.measured ? 'Chưa nhận đủ số liệu token từ nhà cung cấp.' : message.usage.cost_usd_min === null || message.usage.cost_usd_max === null ? 'Chưa có giá xác minh cho model của lượt hỏi này.' : `Chi phí tham khảo: $${message.usage.cost_usd_min.toFixed(6)}–$${message.usage.cost_usd_max.toFixed(6)} USD, tùy khung giờ (giá ngày ${message.usage.pricing_date}).`}</p></details>}{message.disclaimer && <p className="mt-3 border-t border-slate-200 pt-2 text-[10px] text-slate-500">{message.disclaimer}</p>}{message.severity && <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-bold text-amber-800"><div className="flex items-center gap-2"><CircleHelp className="size-4" /> Mức độ: {message.severity}</div><p className="mt-1 font-medium text-amber-700">Cần xác nhận với chuyên gia y tế.</p></div>}</div></div>)}{messages.length === 1 && <div className="space-y-2 pt-1"><p className="text-[11px] font-bold text-slate-400">Gợi ý câu hỏi</p>{suggestions.map((suggestion) => <button key={suggestion} onClick={() => sendMessage(suggestion)} className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-left text-xs font-semibold text-slate-600 transition hover:border-teal-300 hover:text-teal-700"><span className="flex items-center gap-2"><CircleHelp className="size-3.5 text-teal-500" />{suggestion}</span><ChevronRight className="size-4 text-slate-300" /></button>)}</div>}{typing && <ProgressSteps className="max-w-[88%] rounded-bl-md shadow-[0_2px_8px_rgba(15,23,42,0.03)]" title="Trợ lý đang xử lý" stages={stages} note="Câu trả lời chỉ hiện sau khi từng câu đã được đối chiếu với nguồn." />}<div ref={bottom} /></div>
      <div className="shrink-0 border-t border-slate-100 bg-white p-4"><div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2 transition focus-within:border-teal-400 focus-within:ring-2 focus-within:ring-teal-100"><textarea aria-label="Câu hỏi về thuốc hoặc nguồn thực phẩm cung cấp chất dinh dưỡng" maxLength={5000} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); sendMessage() } }} rows={1} placeholder="Hỏi về thuốc hoặc thực phẩm..." className="max-h-24 min-h-9 flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none placeholder:text-slate-400" /><button onClick={() => sendMessage()} disabled={!draft.trim() || typing} aria-label="Gửi tin nhắn" className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-teal-500 text-white transition hover:bg-teal-600 disabled:cursor-not-allowed disabled:opacity-40"><Send className="size-4" /></button></div><p className="mt-2 text-center text-[10px] text-slate-400">Không thay thế chẩn đoán hoặc chỉ định y khoa</p></div>
      <div className="shrink-0 border-t border-slate-100 bg-white px-4 pb-3"><label className={`inline-flex min-h-9 items-center gap-2 rounded-lg px-2 text-xs font-semibold text-teal-700 ${imageActivity ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:bg-teal-50'}`}><Upload className="size-4" /> Tải ảnh và tự kiểm tra<input type="file" accept="image/png,image/jpeg,image/webp" aria-label="Tải ảnh đơn thuốc để tự kiểm tra" disabled={Boolean(imageActivity)} className="sr-only" onChange={event => { const file = event.target.files?.[0]; event.target.value = ''; if (file) void checkImage(file) }} /></label><p role="status" className="text-[10px] text-slate-500">{imageActivity || 'Ảnh được gửi đến Google Gemini để OCR; khi Gemini lỗi sẽ thử OCR trên thiết bị.'}</p></div>
      {latestSaved && <button type="button" onClick={() => { void onSaved().then(() => { onView(latestSaved.prescriptionId, latestSaved.checkId); onClose() }).catch(error => setMessages(items => [...items, { id: Date.now(), role: 'assistant', text: error instanceof Error ? error.message : 'Không tải lại được danh sách đơn.' }])) }} className="shrink-0 border-t border-teal-100 bg-teal-50 px-4 py-2 text-left text-xs font-bold text-teal-800 hover:bg-teal-100">Mở đơn {latestSaved.prescriptionId} để đối chiếu và xem kết quả →</button>}
    </section>
  </>
}
