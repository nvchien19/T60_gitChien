'use client'

import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import type { PrescriptionImageCrop } from '@/lib/prescription-ocr'

export function PrescriptionImagePreview({ src, crop, disabled, onCrop, onScan }: {
  src: string
  crop?: PrescriptionImageCrop
  disabled: boolean
  onCrop: (crop?: PrescriptionImageCrop) => void
  onScan: () => void
}) {
  const [selecting, setSelecting] = useState(false)
  const start = useRef<{ x: number; y: number } | null>(null)
  const [draft, setDraft] = useState<PrescriptionImageCrop | undefined>()
  const [hint, setHint] = useState('')
  const shown = draft || crop
  return <div>
    <p className="mb-2 text-xs font-bold">Ảnh gốc để đối chiếu</p>
    <div className={`relative inline-block max-w-full ${selecting ? 'cursor-crosshair touch-none select-none' : ''}`}
      onPointerDown={event => {
        if (!selecting || disabled) return
        event.preventDefault()
        event.currentTarget.setPointerCapture(event.pointerId)
        const rect = event.currentTarget.getBoundingClientRect()
        start.current = { x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)), y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)) }
      }}
      onPointerMove={event => {
        if (!start.current || !selecting || disabled) return
        const rect = event.currentTarget.getBoundingClientRect()
        const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
        const y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))
        setDraft({ x: Math.min(x, start.current.x), y: Math.min(y, start.current.y), width: Math.abs(x - start.current.x), height: Math.abs(y - start.current.y) })
      }}
      onPointerUp={() => {
        if (!start.current) return
        start.current = null
        if (draft && draft.width > .03 && draft.height > .03) { onCrop(draft); setSelecting(false); setHint('Đã chọn vùng. Bấm “Quét vùng thuốc” để nhận dạng lại.'); setDraft(undefined) }
        else { setDraft(undefined); setHint('Vùng quá nhỏ. Chọn đủ tên thuốc, hàm lượng, số lượng và cách dùng.') }
      }}
      onPointerCancel={() => { start.current = null; setDraft(undefined) }}>
      <a href={src} target="_blank" rel="noreferrer" onClick={event => { if (selecting) event.preventDefault() }}>
        <img src={src} alt="Ảnh đơn thuốc đã chọn" draggable={false} className="block h-auto max-h-80 max-w-full rounded-lg border border-slate-200 bg-white" />
      </a>
      {shown && <div aria-label="Vùng thuốc đã chọn" className="pointer-events-none absolute border-2 border-sky-500 bg-sky-400/10" style={{ left: `${shown.x * 100}%`, top: `${shown.y * 100}%`, width: `${shown.width * 100}%`, height: `${shown.height * 100}%` }} />}
    </div>
    <div className="mt-2 flex flex-wrap gap-2">
      <Button type="button" variant="outline" disabled={disabled} onClick={() => { setSelecting(previous => !previous); setHint('Kéo trên ảnh để chọn vùng chứa toàn bộ các dòng thuốc.') }}>{selecting ? 'Hủy chọn vùng' : 'Chọn vùng thuốc'}</Button>
      <Button type="button" variant="outline" disabled={disabled} onClick={onScan}>{crop ? 'Quét vùng thuốc' : 'Quét lại ảnh'}</Button>
      {crop && <Button type="button" variant="outline" disabled={disabled} onClick={() => { onCrop(undefined); setDraft(undefined); setSelecting(false); setHint('Đã chọn lại toàn bộ ảnh. Bấm “Quét lại ảnh” để đọc toàn trang.') }}>Toàn bộ ảnh</Button>}
    </div>
    {hint && <p role="status" className="mt-2 text-xs text-slate-500">{hint}</p>}
  </div>
}
