'use client'

import { useEffect, useRef, useState } from 'react'
import type { Worker } from 'tesseract.js'
import { api, type Medication } from '@/lib/api'
import { preparePrescriptionImage, type PrescriptionImageCrop } from '@/lib/prescription-ocr'
import { choosePrescriptionCandidate, prescriptionNeedsAnotherPass, type OcrPage } from '@/lib/prescription-layout'
import { PrescriptionImagePreview } from '@/components/PrescriptionImagePreview'
import { Plus, Trash2, Upload, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { BrandLogo } from '@/components/BrandLogo'
import { extractPrescriptionText, prescriptionLookupName, matchCatalogProduct, replaceOcrRows, type CatalogProduct, type MedicationDraft } from '@/lib/prescription-normalize'

type CatalogMatch = { input: string; canonical_name: string; status: string; note: string; suggestions: { canonical_name: string; drug_id: string }[] }
export type EditableMedicationDraft = MedicationDraft & { id?: number; type?: Medication['type']; ocrSource?: boolean; catalogMatch?: CatalogMatch }

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
  const [crop, setCrop] = useState<PrescriptionImageCrop | undefined>()
  const [rawText, setRawText] = useState('')
  const [normalizedText, setNormalizedText] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [activity, setActivity] = useState('')
  const [unparsedLines, setUnparsedLines] = useState<string[]>([])
  const [confidence, setConfidence] = useState<number | null>(null)
  const [coverageWarning, setCoverageWarning] = useState('')
  const operationRef = useRef(false)
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
    setRows(items => items.map((row, i) => i === index ? { ...row, [field]: value, catalogMatch: field === 'frequency' ? row.catalogMatch : undefined } : row))
    setReviewed(false)
  }

  async function extract(selected: File, selectedCrop?: PrescriptionImageCrop) {
    if (operationRef.current) return
    operationRef.current = true
    setBusy(true); setError(''); setNotice(''); setProgress(0); setConfidence(null); setCoverageWarning(''); setActivity('Đang chuẩn bị ảnh…')
    setRows(items => items.filter(row => !row.ocrSource))
    let worker: Worker | undefined
    try {
      const image = await preparePrescriptionImage(selected, selectedCrop)
      const { createWorker, PSM } = await import('tesseract.js')
      if (!mounted.current) return
      setActivity('Đang tải bộ nhận dạng…')
      worker = await createWorker('vie+eng', 1, {
        workerPath: '/ocr/worker.min.js', corePath: '/ocr/core', langPath: '/ocr/lang', gzip: false,
        logger: message => {
        if (mounted.current && message.status === 'recognizing text') { setActivity('Đang nhận dạng đơn thuốc…'); setProgress(Math.round(message.progress * 100)) }
      } })
      if (!mounted.current) return
      workerRef.current = worker
      await worker.setParameters({ tessedit_pageseg_mode: PSM.AUTO, preserve_interword_spaces: '1', user_defined_dpi: '300' })
      const pages: OcrPage[] = []
      // Both modes are needed: AUTO may split a table into separate columns;
      // SINGLE_COLUMN keeps drug descriptions and usage together more often.
      for (const mode of [PSM.AUTO, PSM.SINGLE_COLUMN]) {
        if (!mounted.current) return
        await worker.setParameters({ tessedit_pageseg_mode: mode })
        const result = await worker.recognize(image, { rotateAuto: true }, { text: true, blocks: true })
        pages.push(result.data)
      }
      let candidate = choosePrescriptionCandidate(pages)
      if (prescriptionNeedsAnotherPass(candidate.text, candidate.confidence)) {
        await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT })
        const sparse = await worker.recognize(image, { rotateAuto: true }, { text: true, blocks: true })
        pages.push(sparse.data)
        candidate = choosePrescriptionCandidate(pages)
      }
      if (!mounted.current) return
      setRawText(candidate.text); setConfidence(candidate.confidence)
      setNeedsReview(true); setReviewed(false)
      if (candidate.text.trim()) await fillFromText(candidate.text, selected.name.replace(/\.[^.]+$/, ''))
      else setError('Chưa đọc được chữ. Hãy chọn ảnh rõ hơn hoặc nhập thuốc thủ công.')
    } catch (error) {
      if (mounted.current) setError(error instanceof Error && error.message.includes('megapixel') ? error.message : 'Không đọc được ảnh. Thử ảnh rõ hơn hoặc dán văn bản và nhập thủ công.')
    } finally {
      if (worker && workerRef.current === worker) workerRef.current = null
      await worker?.terminate().catch(() => {})
      operationRef.current = false
      if (mounted.current) { setBusy(false); setActivity('') }
    }
  }

  async function fillFromText(text: string, fallbackName = '') {
    const extracted = extractPrescriptionText(text)
    setUnparsedLines(extracted.unparsedLines)
    const sequence = text.split(/\r?\n/).map(line => line.match(/^\s*(\d{1,2})\s*[.)]\s*\p{L}/u)).filter(Boolean).map(match => Number(match![1]))
    const lastNumber = Math.max(0, ...sequence)
    setCoverageWarning(lastNumber > extracted.medications.length && lastNumber <= 50 ? `Ảnh có số thứ tự đến ${lastNumber}, nhưng chỉ tách được ${extracted.medications.length} thuốc. Cần quét lại vùng thuốc hoặc bổ sung các dòng bị thiếu.` : '')
    if (!extracted.medications.length) {
      setError('Chưa tách được thuốc. Sửa văn bản, mỗi thuốc một dòng có số thứ tự hoặc hàm lượng, rồi thử lại.')
      return
    }
    if (extracted.medications.length > 50) {
      setError('Đơn có hơn 50 dòng nhận dạng. Hãy chia nhỏ ảnh hoặc bỏ các dòng không phải thuốc.')
      return
    }
    if (!initialName) setName(previous => previous.trim() ? previous : (extracted.name || fallbackName).slice(0, 150))
    setRows(items => replaceOcrRows(items, extracted.medications))
    setNeedsReview(true); setReviewed(false); setError(''); setNormalizedText(text)
    setNotice(`Đã điền ${extracted.medications.length} thuốc vào tên, hàm lượng và cách dùng. Đối chiếu ảnh trước khi lưu.`)
    setActivity('Đang đối chiếu tên thuốc với DB…')
    try {
      const response = await api<{ items: CatalogMatch[] }>('/drugs/normalize', { drugs: extracted.medications.map(row => row.name) })
      const unresolved = extracted.medications.filter((row, index) => row.dose && response.items[index]?.status !== 'ok')
      const fallback = unresolved.length ? await api<{ items: CatalogMatch[] }>('/drugs/normalize', { drugs: unresolved.map(row => prescriptionLookupName(row.name) !== row.name ? prescriptionLookupName(row.name) : `${row.name} ${row.dose}`) }).catch(() => ({ items: [] as CatalogMatch[] })) : { items: [] }
      const products = new Map<string, CatalogProduct>()
      const missing = extracted.medications.filter((row, index) => response.items[index]?.status !== 'ok')
      for (let offset = 0; offset < missing.length; offset += 5) {
        await Promise.all(missing.slice(offset, offset + 5).map(async row => {
          if (row.name.length < 2) return
          const response = await api<{ items: CatalogProduct[] }>(`/drugs/products/search?q=${encodeURIComponent(row.name)}&limit=50`).catch(() => ({ items: [] as CatalogProduct[] }))
          const product = matchCatalogProduct(row, response.items)
          if (product) products.set(`${row.name}|${row.dose}`, product)
        }))
      }
      if (!mounted.current) return
      setRows(items => items.map(row => {
        if (!row.ocrSource) return row
        const primary = response.items.find(match => match.input === row.name)
        const fullName = fallback.items.find(match => match.input === `${row.name} ${row.dose}` || match.input === prescriptionLookupName(row.name))
        const product = products.get(`${row.name}|${row.dose}`)
        if (product) return { ...row, catalogMatch: { input: row.name, canonical_name: product.name, status: 'product', note: '', suggestions: [] } }
        return { ...row, catalogMatch: fullName?.status === 'ok' ? fullName : primary }
      }))
    } catch {
      if (mounted.current) setNotice('Đã điền các trường từ OCR; chưa kết nối được DB để đối chiếu tên thuốc. Kiểm tra tên trên ảnh trước khi lưu.')
    }
  }

  async function normalize() {
    if (operationRef.current) return
    operationRef.current = true; setBusy(true)
    try { await fillFromText(rawText) }
    finally { operationRef.current = false; if (mounted.current) { setBusy(false); setActivity('') } }
  }

  return <dialog ref={dialogRef} aria-labelledby="prescription-editor-title" onCancel={onClose} className="fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/30 backdrop:backdrop-blur-sm">
    <form className="flex max-h-[90dvh] flex-col overflow-hidden" onSubmit={async event => {
      event.preventDefault()
      if (busy || operationRef.current) return
      if (!name.trim() || (!initialName && !rows.length) || rows.some(row => !row.name.trim())) { setError('Nhập tên đơn và tên cho từng thuốc. Xóa những dòng không sử dụng.'); return }
      if (needsReview && !reviewed) { setError('Vui lòng đối chiếu nội dung nhận dạng và xác nhận đã kiểm tra.'); return }
      setBusy(true); setError(''); setActivity('Đang lưu đơn thuốc…')
      try { await onSave(name.trim(), rows.map(row => ({ id: row.id, type: row.type, name: row.name.trim(), dose: row.dose.trim(), frequency: row.frequency.trim() }))) }
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
          <h3 className="text-sm font-bold">Đọc thuốc từ ảnh đơn thuốc</h3><p className="mt-1 text-xs text-slate-500">PNG, JPG hoặc WebP · tối đa 10 MB. Chọn ảnh rõ, chụp thẳng và đủ toàn bộ bảng thuốc để tự động điền tên thuốc, hàm lượng và cách dùng. Ảnh xử lý trên thiết bị; tên thuốc được đối chiếu với DB.</p>
          <p className="mt-2 text-xs"><a href="/samples/don-thuoc-mau-db.png" download className="font-semibold text-sky-700 underline underline-offset-2">Tải ảnh đơn mẫu từ DB</a><span className="mx-2 text-slate-400">·</span><a href="/samples/don-thuoc-mau-db.pdf" target="_blank" rel="noreferrer" className="font-semibold text-sky-700 underline underline-offset-2">Xem bản PDF</a></p>
          <div className="mt-3 flex flex-wrap items-center gap-3"><label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold"><Upload className="size-4 text-sky-600" /> Chọn ảnh đơn thuốc<input type="file" aria-label="Ảnh đơn thuốc" accept="image/png,image/jpeg,image/webp" disabled={busy} className="sr-only" onChange={event => {
            const selected = event.target.files?.[0]; event.target.value = ''
            if (!selected) return
            if (!['image/png', 'image/jpeg', 'image/webp'].includes(selected.type) || selected.size > 10 * 1024 * 1024) { setError('Chọn ảnh PNG, JPG hoặc WebP không quá 10 MB.'); return }
            setFile(selected); setCrop(undefined); setRawText(''); setNormalizedText(null); setUnparsedLines([]); setError(''); setNotice(''); setReviewed(false); setNeedsReview(true)
            void extract(selected)
          }} /></label><span className="max-w-64 truncate text-xs text-slate-500">{file?.name}</span></div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {preview && <PrescriptionImagePreview key={preview} src={preview} crop={crop} disabled={busy} onCrop={setCrop} onScan={() => file && void extract(file, crop)} />}
            <div className={preview ? '' : 'sm:col-span-2'}><label className="text-xs font-bold">Văn bản nhận dạng — có thể sửa hoặc dán nội dung đơn<textarea value={rawText} disabled={busy} onChange={event => { setRawText(event.target.value); setReviewed(false); setNeedsReview(true) }} placeholder="1. Tên thuốc 500 mg&#10;Uống theo hướng dẫn ghi trên đơn…" className={`${inputClass} min-h-40 font-normal`} /></label><Button type="button" variant="outline" className="mt-2 whitespace-normal" disabled={!rawText.trim() || busy || normalizedText === rawText} onClick={() => void normalize()}>Điền các trường từ văn bản</Button><p className="mt-2 text-xs text-slate-500">Điền lại sẽ thay các dòng OCR trước đó; giữ các thuốc nhập thủ công và thuốc đã lưu.</p></div>
          </div>
          {busy && <p role="status" className="mt-3 text-xs text-sky-700">{activity} {activity.includes('nhận dạng đơn') ? `${progress}%` : ''}</p>}
          {coverageWarning && <p role="alert" className="mt-3 text-xs text-amber-700">{coverageWarning}</p>}
          {confidence !== null && confidence < 75 && <p className="mt-3 text-xs text-amber-700">Ảnh có độ rõ thấp. Kiểm tra kỹ dấu thập phân, hàm lượng và các dòng có thể bị thiếu.</p>}
          {unparsedLines.length > 0 && <details className="mt-3 text-xs text-amber-700"><summary className="cursor-pointer">{unparsedLines.length} dòng chưa điền vào trường — mở để đối chiếu</summary><pre className="mt-2 whitespace-pre-wrap font-sans">{unparsedLines.join('\n')}</pre></details>}
          {notice && <p role="status" className="mt-3 text-xs text-sky-800">{notice}</p>}
        </section>
        <section><div className="mb-3 flex items-center justify-between gap-2"><h3 className="text-sm font-bold">2. Các thuốc trong đơn ({rows.length})</h3><Button type="button" variant="outline" disabled={busy} onClick={() => { setRows(items => [...items, emptyRow()]); setReviewed(false) }}><Plus className="size-4" /> Thêm thuốc</Button></div>
          <div className="space-y-3">{rows.map((row, index) => <div key={index} className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50/50 p-3 sm:grid-cols-[1.2fr_.7fr_1fr_auto]">
            <label className="min-w-0 text-xs font-semibold">Tên thuốc {index + 1} * {row.id !== undefined && <span className="ml-1 font-normal text-sky-600">Đã có trong đơn</span>}<input required disabled={busy} maxLength={200} value={row.name} onChange={event => updateRow(index, 'name', event.target.value)} placeholder="Paracetamol" className={inputClass} /></label>
            <label className="min-w-0 text-xs font-semibold">Hàm lượng / liều ghi trên đơn<input disabled={busy} value={row.dose} onChange={event => updateRow(index, 'dose', event.target.value)} placeholder="500 mg" className={inputClass} /></label>
            <label className="min-w-0 text-xs font-semibold">Cách dùng / số lượng ghi trên đơn<textarea aria-label="Cách dùng / số lượng ghi trên đơn" rows={2} disabled={busy} value={row.frequency} onChange={event => updateRow(index, 'frequency', event.target.value)} placeholder="Nhập theo đơn gốc" className={inputClass} /></label>
            <button type="button" aria-label={`Xóa thuốc ${index + 1}`} disabled={busy} onClick={() => { setRows(items => items.filter((_, i) => i !== index)); setReviewed(false) }} className="self-end rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600"><Trash2 className="size-4" /></button>
          </div>)}</div><p className="mt-3 text-xs text-slate-500">Có thể sửa hoặc xóa từng thuốc và thêm thuốc mới. Thay đổi được áp dụng khi lưu; hãy kiểm tra lại tương tác sau khi chỉnh sửa.</p>
        </section>
        {needsReview && <label className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><input type="checkbox" disabled={busy} checked={reviewed} onChange={event => setReviewed(event.target.checked)} className="mt-1" />Tôi đã đối chiếu ảnh gốc, kiểm tra tên thuốc, hàm lượng, cách dùng và bổ sung các thuốc còn thiếu.</label>}
        {error && <p role="alert" className="text-sm text-rose-600">{error}</p>}
      </div>
      <footer className="flex shrink-0 flex-col-reverse gap-2 border-t border-slate-100 p-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:flex-row sm:items-center sm:justify-end sm:p-5"><Button type="button" variant="outline" onClick={onClose} className="w-full justify-center sm:w-auto">Hủy</Button><Button type="submit" disabled={busy || (needsReview && !reviewed)} className="w-full justify-center bg-sky-500 hover:bg-sky-600 sm:w-auto">{initialName ? 'Lưu thay đổi' : 'Lưu đơn thuốc'}</Button></footer>
    </form>
  </dialog>
}
