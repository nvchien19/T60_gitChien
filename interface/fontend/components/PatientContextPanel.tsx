'use client'

import { useEffect, useState } from 'react'
import { Dna, HeartPulse, Loader2, Plus, X } from 'lucide-react'
import { api, loadContextOptions } from '@/lib/api'
import type { ContextOptions, PatientContext } from '@/lib/api'

const fold = (text: string) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/gi, 'd').toLowerCase()
const same = (a: PatientContext, b: PatientContext) => JSON.stringify([[...a.conditions].sort(), Object.entries(a.genes).sort()]) === JSON.stringify([[...b.conditions].sort(), Object.entries(b.genes).sort()])

export function PatientContextPanel({ prescriptionId, value, onSaved }: { prescriptionId: string; value: PatientContext; onSaved: () => Promise<void> | void }) {
  const [options, setOptions] = useState<ContextOptions | null>(null)
  const [draft, setDraft] = useState<PatientContext>(value)
  const [query, setQuery] = useState('')
  const [gene, setGene] = useState('')
  const [result, setResult] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => { loadContextOptions().then(setOptions).catch(e => setError((e as Error).message)) }, [])
  useEffect(() => { setDraft(value); setMessage(''); setError('') }, [prescriptionId, value])

  const conditionOf = (id: string) => options?.conditions.find(item => item.mesh_id === id)
  const geneOf = (name: string) => options?.genes.find(item => item.gene === name)
  const needle = fold(query.trim())
  const suggestions = needle.length < 2 ? [] : (options?.conditions || []).filter(item => !draft.conditions.includes(item.mesh_id) && [item.name_vi, item.name, ...item.keywords].some(text => fold(text).includes(needle))).slice(0, 8)
  const dirty = !same(draft, value)

  const save = async () => {
    setSaving(true); setError(''); setMessage('')
    try {
      await api(`/prescriptions/${prescriptionId}/context`, draft, 'PUT')
      await onSaved()
      setMessage('Đã lưu. Bấm "Kiểm tra tương tác" để tra lại theo thông tin mới.')
    } catch (e) { setError((e as Error).message) } finally { setSaving(false) }
  }

  return <section aria-labelledby="context-title" className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h3 id="context-title" className="text-sm font-extrabold">Bệnh nền và kiểu gen của bệnh nhân</h3>
        <p className="mt-1 text-xs text-slate-400">Không bắt buộc. Khai thêm để tra cảnh báo thuốc với bệnh nền và thuốc với gen.</p></div>
      <span className="rounded-full bg-violet-50 px-3 py-1 text-[11px] font-bold text-violet-700">Thử nghiệm</span>
    </div>

    <div className="mt-4 grid gap-5 lg:grid-cols-2">
      <div>
        <label htmlFor="condition-search" className="flex items-center gap-2 text-xs font-bold text-slate-600"><HeartPulse className="size-4 text-rose-500" /> Bệnh nền</label>
        <input id="condition-search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Gõ tên bệnh, ví dụ: suy thận, hen, loét dạ dày" autoComplete="off" className="mt-2 block w-full rounded-lg border border-slate-200 bg-white p-2 text-sm outline-none focus:border-teal-400" />
        {needle.length >= 2 && <div className="mt-2 space-y-1">
          {suggestions.map(item => <button type="button" key={item.mesh_id} onClick={() => { setDraft({ ...draft, conditions: [...draft.conditions, item.mesh_id] }); setQuery('') }} className="flex w-full items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-left text-xs hover:border-teal-300">
            <span className="min-w-0"><span className="font-bold">{item.name_vi || item.name}</span>{item.name_vi && <span className="text-slate-400"> · {item.name}</span>}</span>
            <span className="shrink-0 text-[11px] text-slate-400">{item.n_drugs} hoạt chất</span>
          </button>)}
          {options && !suggestions.length && <p className="text-xs text-slate-500">Không có bệnh nào khớp trong CSDL. Bệnh không có trong danh mục thì chưa tra được.</p>}
        </div>}
        <div className="mt-3 flex flex-wrap gap-2">
          {draft.conditions.map(id => <span key={id} className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-800">
            {conditionOf(id)?.name_vi || conditionOf(id)?.name || id}
            <button type="button" aria-label="Bỏ bệnh nền này" onClick={() => setDraft({ ...draft, conditions: draft.conditions.filter(item => item !== id) })} className="rounded-full p-0.5 hover:bg-rose-100"><X className="size-3" /></button>
          </span>)}
          {!draft.conditions.length && <span className="text-xs text-slate-400">Chưa khai bệnh nền.</span>}
        </div>
      </div>

      <div>
        <p className="flex items-center gap-2 text-xs font-bold text-slate-600"><Dna className="size-4 text-violet-600" /> Kết quả xét nghiệm gen</p>
        {!options && !error && <p role="status" className="mt-2 text-xs text-slate-500">Đang tải danh mục gen…</p>}
        {options && options.genes.length === 0 && <p role="status" className="mt-2 text-xs text-amber-700">Chưa có dữ liệu khuyến cáo gen trong CSDL. Cần nạp dữ liệu CPIC trước khi chọn kết quả xét nghiệm.</p>}
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <select aria-label="Gen" value={gene} disabled={!options?.genes.length} onChange={event => { setGene(event.target.value); setResult('') }} className="rounded-lg border border-slate-200 bg-white p-2 text-sm disabled:opacity-50 sm:w-36">
            <option value="">Chọn gen</option>{(options?.genes || []).map(item => <option key={item.gene} value={item.gene}>{item.gene}</option>)}
          </select>
          <select aria-label="Kết quả" value={result} disabled={!gene} onChange={event => setResult(event.target.value)} className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white p-2 text-sm disabled:opacity-50">
            <option value="">Chọn kết quả</option>{(geneOf(gene)?.results || []).map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
          <button type="button" disabled={!gene || !result} onClick={() => { setDraft({ ...draft, genes: { ...draft.genes, [gene]: result } }); setGene(''); setResult('') }} className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 hover:border-teal-300 disabled:opacity-40"><Plus className="size-3.5" /> Thêm</button>
        </div>
        {gene && <p className="mt-2 text-[11px] leading-relaxed text-slate-400">CPIC có khuyến cáo theo {gene} cho: {geneOf(gene)?.drugs.join(', ')}.</p>}
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(draft.genes).map(([name, value]) => <span key={name} className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-800">
            {name}: {geneOf(name)?.results.find(item => item.value === value)?.label || value}
            <button type="button" aria-label={`Bỏ kết quả gen ${name}`} onClick={() => setDraft({ ...draft, genes: Object.fromEntries(Object.entries(draft.genes).filter(([key]) => key !== name)) })} className="rounded-full p-0.5 hover:bg-violet-100"><X className="size-3" /></button>
          </span>)}
          {!Object.keys(draft.genes).length && <span className="text-xs text-slate-400">Chưa khai kết quả gen.</span>}
        </div>
      </div>
    </div>

    <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
      <button type="button" disabled={!dirty || saving} onClick={save} className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-40">{saving && <Loader2 className="size-3.5 animate-spin" />} Lưu thông tin bệnh nhân</button>
      {dirty && !saving && <span className="text-xs text-amber-700">Có thay đổi chưa lưu.</span>}
      {message && <span role="status" className="text-xs text-emerald-700">{message}</span>}
      {error && <span role="alert" className="text-xs text-rose-700">{error}</span>}
    </div>
    <p className="mt-3 text-[11px] leading-relaxed text-slate-400">Chỉ tra được các bệnh và kết quả gen có trong danh mục. Bệnh nền khớp theo đúng tên đã chọn, không tự suy ra bệnh rộng hơn hay hẹp hơn. Chỉ nhập thông tin cần cho việc kiểm tra đơn.</p>
  </section>
}
