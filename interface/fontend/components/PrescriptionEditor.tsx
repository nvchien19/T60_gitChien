'use client'

import { useEffect, useRef, useState } from 'react'
import type { Worker } from 'tesseract.js'
import type { Medication } from '@/lib/api'
import { Plus, Trash2, Upload, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { BrandLogo } from '@/components/BrandLogo'
import { normalizePrescriptionText, type MedicationDraft } from '@/lib/prescription-normalize'

export type EditableMedicationDraft = MedicationDraft & { id?: number; type?: Medication['type'] }

const emptyRow = (): MedicationDraft => ({ name: '', dose: '', frequency: '' })
const inputClass = 'mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-sky-500'

export function PrescriptionEditor({ initialName = '', existingMedications = [], onClose, onSave }: {
  initialName?: string
  existingMedications?: Medication[]
  onClose: () => void
  onSave: (name: string, medications: EditableMedicationDraft[]) => Promise<void>
}) {
  const [name, setName] = useState(initialName)
  const [rows, setRows] = useState<EditableMedicationDraft[]>(() => existingMedications.length ? existingMedications.map(({ id, name, dose, frequency, type }) => ({ id, name, dose, frequency, type })) : [emptyRow()])
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState('')
  const [rawText, setRawText] = useState('')
  const [normalizedText, setNormalizedText] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [needsReview, setNeedsReview] = useState(false)
  const workerRef = useRef<Worker | null>(null)
  const mounted = useRef(true)
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    mounted.current = true
    const previousFocus = document.activeElement as HTMLElement | null
    dialogRef.current?.showModal()
    return () => { mounted.current = false; void workerRef.current?.terminate(); previousFocus?.focus() }
  }, [])
  useEffect(() => {
    if (!file) { setPreview(''); return }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function updateRow(index: number, field: keyof MedicationDraft, value: string) {
    setRows(items => items.map((row, i) => i === index ? { ...row, [field]: value } : row))
    setReviewed(false)
  }

  async function extract(selected: File) {
    if (busy) return
    setBusy(true); setError(''); setNotice(''); setProgress(0)
    let worker: Worker | undefined
    try {
      const { createWorker } = await import('tesseract.js')
      if (!mounted.current) return
      worker = await createWorker('vie+eng', 1, { logger: message => {
        if (mounted.current && message.status === 'recognizing text') setProgress(Math.round(message.progress * 100))
      } })
      if (!mounted.current) return
      workerRef.current = worker
      const result = await worker.recognize(selected)
      if (!mounted.current) return
      setRawText(result.data.text)
      setNeedsReview(true); setReviewed(false)
      setNotice(result.data.text.trim() ? 'Đã đọc ảnh. Kiểm tra văn bản, rồi chọn “Chuẩn hóa thành danh sách thuốc”.' : 'Chưa đọc được chữ. Hãy chọn ảnh rõ hơn hoặc nhập thuốc thủ công.')
    } catch {
      if (mounted.current) setError('Không đọc được ảnh. Kiểm tra kết nối để tải bộ nhận dạng, thử ảnh rõ hơn hoặc nhập thủ công.')
    } finally {
      if (worker && workerRef.current === worker) workerRef.current = null
      await worker?.terminate().catch(() => {})
      if (mounted.current) setBusy(false)
    }
  }

  function normalize() {
    const extracted = normalizePrescriptionText(rawText)
    if (!extracted.length) { setError('Chưa tách được thuốc. Hãy sửa văn bản, mỗi thuốc một dòng có số thứ tự hoặc hàm lượng, hoặc nhập thủ công.'); return }
    setRows(items => [...items.filter(row => row.name.trim() || row.dose.trim() || row.frequency.trim()), ...extracted])
    setNeedsReview(true); setReviewed(false); setError('')
    setNormalizedText(rawText)
    setNotice(`Đã thêm ${extracted.length} dòng để kiểm tra. Đối chiếu toàn bộ ảnh, bổ sung thuốc còn thiếu và xóa dòng không phải thuốc.`)
  }

  return <dialog ref={dialogRef} aria-labelledby="prescription-editor-title" onCancel={onClose} className="fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/30 backdrop:backdrop-blur-sm">
    <form className="flex max-h-[90dvh] flex-col overflow-hidden" onSubmit={async event => {
      event.preventDefault()
      if (busy) return
      if (!name.trim() || (!initialName && !rows.length) || rows.some(row => !row.name.trim())) { setError('Nhập tên đơn và tên cho từng thuốc. Xóa những dòng không sử dụng.'); return }
      if (needsReview && !reviewed) { setError('Vui lòng đối chiếu nội dung nhận dạng và xác nhận đã kiểm tra.'); return }
      setBusy(true); setError('')
      try { await onSave(name.trim(), rows.map(row => ({ ...row, name: row.name.trim(), dose: row.dose.trim(), frequency: row.frequency.trim() }))) }
      catch (e) { if (mounted.current) setError((e as Error).message) }
      finally { if (mounted.current) setBusy(false) }
    }}>
      <header className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-100 p-5 sm:p-6">
        <div className="flex items-start gap-3"><BrandLogo size={36} /><div><p className="text-xs font-bold uppercase tracking-wider text-sky-600">Medication safety</p><h2 id="prescription-editor-title" className="mt-1 text-xl font-extrabold">{initialName ? 'Chỉnh sửa thuốc trong đơn' : 'Thêm đơn thuốc'}</h2><p className="mt-2 text-sm text-slate-500">Nhập thuốc hoặc đọc từ ảnh, sau đó kiểm tra trước khi lưu.</p></div></div>
        <button type="button" onClick={onClose} aria-label="Đóng" className="shrink-0 rounded-lg p-1 text-slate-400"><X className="size-5" /></button>
      </header>
      <div className="min-h-0 flex-1 space-y-6 overflow-y-auto overscroll-contain p-5 sm:p-6">
        <label className="block text-sm font-bold">1. Tên đơn thuốc <span className="text-rose-500">*</span><input autoFocus required maxLength={150} value={name} readOnly={Boolean(initialName)} onChange={event => setName(event.target.value)} placeholder="Ví dụ: Đơn tái khám tháng 10" className={inputClass} /></label>
        <section className="rounded-xl border border-sky-100 bg-sky-50/40 p-4">
          <h3 className="text-sm font-bold">Đọc thuốc từ ảnh đơn thuốc</h3><p className="mt-1 text-xs text-slate-500">PNG, JPG hoặc WebP · tối đa 10 MB. Ảnh được tự động đọc sau khi chọn và xử lý trên thiết bị. Lần đầu cần mạng để tải bộ nhận dạng.</p>
          <div className="mt-3 flex flex-wrap items-center gap-3"><label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold"><Upload className="size-4 text-sky-600" /> Chọn ảnh đơn thuốc<input type="file" aria-label="Ảnh đơn thuốc" accept="image/png,image/jpeg,image/webp" disabled={busy} className="sr-only" onChange={event => {
            const selected = event.target.files?.[0]; event.target.value = ''
            if (!selected) return
            if (!['image/png', 'image/jpeg', 'image/webp'].includes(selected.type) || selected.size > 10 * 1024 * 1024) { setError('Chọn ảnh PNG, JPG hoặc WebP không quá 10 MB.'); return }
            setFile(selected); setRawText(''); setNormalizedText(null); setError(''); setNotice(''); setReviewed(false)
            void extract(selected)
          }} /></label><span className="max-w-64 truncate text-xs text-slate-500">{file?.name}</span></div>
          {preview && <div className="mt-4 grid gap-4 sm:grid-cols-2"><div><p className="mb-2 text-xs font-bold">Ảnh gốc để đối chiếu</p><a href={preview} target="_blank" rel="noreferrer"><img src={preview} alt="Ảnh đơn thuốc đã chọn" className="max-h-80 w-full rounded-lg border border-slate-200 bg-white object-contain" /></a></div><div><label className="text-xs font-bold">Văn bản nhận dạng — có thể sửa<textarea value={rawText} disabled={busy} onChange={event => { setRawText(event.target.value); setReviewed(false); setNeedsReview(true) }} placeholder="Nội dung đọc từ ảnh sẽ hiển thị tại đây…" className={`${inputClass} min-h-56 font-normal`} /></label><Button type="button" variant="outline" className="mt-2 whitespace-normal" disabled={!rawText.trim() || busy || normalizedText === rawText} onClick={normalize}>Chuẩn hóa thành danh sách thuốc</Button></div></div>}
          {busy && <p role="status" className="mt-3 text-xs text-sky-700">Đang nhận dạng chữ tiếng Việt và tên thuốc… {progress}%</p>}
          {notice && <p role="status" className="mt-3 text-xs text-sky-800">{notice}</p>}
        </section>
        <section><div className="mb-3 flex items-center justify-between gap-2"><h3 className="text-sm font-bold">2. Các thuốc trong đơn ({rows.length})</h3><Button type="button" variant="outline" onClick={() => { setRows(items => [...items, emptyRow()]); setReviewed(false) }}><Plus className="size-4" /> Thêm thuốc</Button></div>
          <div className="space-y-3">{rows.map((row, index) => <div key={index} className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50/50 p-3 sm:grid-cols-[1.2fr_.7fr_1fr_auto]">
            <label className="min-w-0 text-xs font-semibold">Tên thuốc {index + 1} * {row.id !== undefined && <span className="ml-1 font-normal text-sky-600">Đã có trong đơn</span>}<input required value={row.name} onChange={event => updateRow(index, 'name', event.target.value)} placeholder="Paracetamol" className={inputClass} /></label>
            <label className="min-w-0 text-xs font-semibold">Hàm lượng / liều ghi trên đơn<input value={row.dose} onChange={event => updateRow(index, 'dose', event.target.value)} placeholder="500 mg" className={inputClass} /></label>
            <label className="min-w-0 text-xs font-semibold">Cách dùng ghi trên đơn<input value={row.frequency} onChange={event => updateRow(index, 'frequency', event.target.value)} placeholder="Nhập theo đơn gốc" className={inputClass} /></label>
            <button type="button" aria-label={`Xóa thuốc ${index + 1}`} onClick={() => { setRows(items => items.filter((_, i) => i !== index)); setReviewed(false) }} className="self-end rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600"><Trash2 className="size-4" /></button>
          </div>)}</div><p className="mt-3 text-xs text-slate-500">Có thể sửa hoặc xóa từng thuốc và thêm thuốc mới. Thay đổi được áp dụng khi lưu; hãy kiểm tra lại tương tác sau khi chỉnh sửa.</p>
        </section>
        {needsReview && <label className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><input type="checkbox" checked={reviewed} onChange={event => setReviewed(event.target.checked)} className="mt-1" />Tôi đã đối chiếu ảnh gốc, kiểm tra tên thuốc, hàm lượng, cách dùng và bổ sung các thuốc còn thiếu.</label>}
        {error && <p role="alert" className="text-sm text-rose-600">{error}</p>}
      </div>
      <footer className="flex shrink-0 flex-col-reverse gap-2 border-t border-slate-100 p-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:flex-row sm:items-center sm:justify-end sm:p-5"><Button type="button" variant="outline" onClick={onClose} className="w-full justify-center sm:w-auto">Hủy</Button><Button type="submit" disabled={busy || (needsReview && !reviewed)} className="w-full justify-center bg-sky-500 hover:bg-sky-600 sm:w-auto">{initialName ? 'Lưu thay đổi' : 'Lưu đơn thuốc'}</Button></footer>
    </form>
  </dialog>
}
