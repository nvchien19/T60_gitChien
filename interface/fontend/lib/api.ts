export type AuthUser = { id: number; email: string; name: string; role: 'doctor' | 'pharmacist' }
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); this.name = 'ApiError' }
}
export type Severity = 'Chống chỉ định' | 'Nghiêm trọng' | 'Trung bình' | 'Nhẹ'
export type Status = 'Chưa kiểm tra' | 'Đã kiểm tra' | 'Có tương tác' | 'Cần xem lại'
export type Medication = { id: number; name: string; ingredient: string; dose: string; frequency: string; type: 'Kê đơn' | 'OTC' | 'Bổ sung'; verified: boolean }
export type PatientContext = { conditions: string[]; genes: Record<string, string> }
export type ConditionOption = { mesh_id: string; name: string; name_vi: string; machine_translation: boolean; n_drugs: number; sources: string[]; keywords: string[] }
export type GeneOption = { gene: string; drugs: string[]; results: { value: string; label: string }[] }
export type ContextOptions = { conditions: ConditionOption[]; genes: GeneOption[] }
export type ContextFinding = FoodFinding & { severity: string; details?: { mesh_id?: string; disease_en?: string; sources?: string[]; genes?: Record<string, string>; untested_genes?: string[]; classification?: string; populations?: string[]; comments?: string[]; same_as_normal?: boolean | null } }
export type Prescription = { id: string; name?: string; patient: string; date: string; medications: Medication[]; status: Status; highest: Severity | null; lastChecked: string; checks: number; context: PatientContext }
export type ReviewRequest = { createdBy: number | null; creatorName: string; response: string; responderName: string; respondedAt: string; id: string; prescriptionId: string; patient: string; message: string; date: string; status: 'Đang chờ' | 'Đã phản hồi'; medCount: number }
export type Citation = { source_id: string; source_name: string; label: string; source_url: string }
export type Finding = { untranslatedFields: string[]; machineTranslation: boolean; id: number; severity: Severity | null; a: string; b: string; kind: string; text: string; management: string; citations: Citation[]; sources: number }
export type CheckRecord = { check_id: string; created_at?: string | null; status: string; summary: { meds_count?: number; findings_count?: number }; max_severity: string; findings?: RawFinding[]; food_findings?: FoodFinding[]; duplicate_findings?: FoodFinding[]; disease_findings?: ContextFinding[]; gene_findings?: ContextFinding[]; patient_context?: PatientContext; disclaimer?: string; unknown?: unknown[]; no_record_pairs?: string[][] }
export type EvalMetrics = { run: string; n_cases: number; confusion: { tp: number; fp: number; fn: number; tn: number }; metrics: { key: string; value: number | null; op: '>=' | '<='; threshold: number; passed: boolean | null; basis: string }[]; review_cases: { id: string; category: string; fn: number; fp: number }[] }
export type EvalRun = { id: string; label: string; note: string; n_cases: number; confusion: { tp: number; fp: number; fn: number; tn: number }; review_cases: { id: string; category: string; fn: number; fp: number }[]; db_gaps: string[] }
export type EvalAllMetric = { key: string; op: '>=' | '<=' | null; threshold: number | null; basis: string; pooled: number | null; mean: number | null; passed: boolean | null; runs: Record<string, number | null> }
export type EvalBenchmark = { name: string; kind: 'db' | 'llm'; source: string; sensitivity?: number; specificity?: number; ppv?: number; npv?: number; accuracy?: number }
export type EvalAll = { generated: string; n_cases: number; confusion: { tp: number; fp: number; fn: number; tn: number }; runs: EvalRun[]; metrics: EvalAllMetric[]; benchmarks: EvalBenchmark[] }
export type EvalBinary = { tp: number; fp: number; fn: number; tn: number; n: number; sensitivity: number | null; sensitivity_ci: number[] | null; specificity: number | null; specificity_ci: number[] | null; ppv: number | null; ppv_ci?: number[] | null; npv: number | null; accuracy: number | null; f1: number | null; kappa_weighted?: number | null }
export type EvalNorm = { items: number; drug_items: number; correct_rate: number | null; correct_rate_ci: number[] | null; recognized_rate: number | null; wrong_rate: number | null; suggest_rate: number | null; unknown_rate: number | null; precision_when_recognized: number | null; not_drug_items: number; not_drug_rejected: number }
export type EvalStat = { mean: number; median: number; p90: number }
export type EvalRef = 'micromedex' | 'drugscom'
export type EvalAuthRef = 'any' | 'two' | 'labels'
export type EvalAuthBlock = { label: string; positives: number; system: EvalBinary; tools: Record<string, EvalBinary & { label: string; in_reference: boolean }> }
export type EvalLiterature = { study: string; setting: string; columns?: string[]; rows?: (string | number)[][]; summary?: string }
export type EvalRx = {
  generated: string
  alashwal: { n: number; positives: Record<EvalRef, number>; system: Record<EvalRef, EvalBinary>; comparators: Record<EvalRef, Record<string, EvalBinary & { label: string }>>; reference_agreement: EvalBinary }
  authoritative: { n: number; refs: Record<EvalAuthRef, EvalAuthBlock>; sources: { micromedex: number; fda_label: number; japan_label: number; fda_no_label: number }; by_n_sources: Record<string, number>; fp_vs_micromedex: { n: number; supported_by_label: number } } | null
  literature: EvalLiterature[]
  onc: { n: number; recognized: number; alert_any: number; alert_major: number; alert_any_rate: number | null; alert_major_rate: number | null; alert_major_rate_recognized: number | null; by_rule: Record<string, { name: string; n: number; recognized: number; alert: number; major: number }> }
  rx: {
    n_prescriptions: number; n_mimic: number; n_vn: number; median_drugs: number | null; normalization: Record<'all' | 'mimic' | 'vn', EvalNorm>
    must_alert: { n: number; hit_major: number }; duplicates: { expected: number; detected: number; recall: number | null; precision: number | null; flagged_checkable: number; flagged_confirmed: number }
    burden: Record<'ddi' | 'major_plus' | 'moderate' | 'minor' | 'food' | 'dup' | 'n_drugs', EvalStat> & { rx_with_major_plus: number | null; rx_with_any_ddi: number | null }
    citation_rate: number | null; findings_total: number
  }
  sources: Record<string, string>
}
export type FoodFinding = RawFinding &{ original_management?: string; original_mechanism?: string }
type RawFinding = { untranslated_fields?: string[]; machine_translation?: boolean; pair: string[]; severity_vi: string; summary: string; management: string; citations: Citation[] }
type RawPrescription = { id: string; name?: string; created_at?: string | null; last_checked?: string | null; status: Status; highest_severity_vi?: string | null; checks_count: number; medications: Medication[]; patient_context?: PatientContext }
type RawReview = { created_by?: number | null; creator_name?: string; response?: string; responder_name?: string; responded_at?: string | null; id: number; prescription_id: string; patient: string; message: string; created_at: string; status: 'Đang chờ' | 'Đã phản hồi'; med_count: number }
export const dateLabel = (value?: string | null) => value ? new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`).toLocaleString('vi-VN') : 'Chưa cập nhật'
// Hiện đúng nhãn backend trả từ CSDL; không ánh xạ lại mức. Nhãn lạ thành null ("Chưa có").
export const severityLabel = (value?: string | null): Severity | null => value === 'Chống chỉ định' || value === 'Nghiêm trọng' || value === 'Trung bình' || value === 'Nhẹ' ? value : null

export async function api<T>(path: string, body?: unknown, method?: 'POST' | 'PUT' | 'PATCH'): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, { method: method ?? (body === undefined ? 'GET' : 'POST'), cache: 'no-store', credentials: 'same-origin', headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(90000) })
  } catch {
    throw new Error('Không kết nối được backend. Hãy kiểm tra dịch vụ API và thử lại.')
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    if (response.status === 401 && !path.startsWith('/auth/') && typeof window !== 'undefined') window.dispatchEvent(new Event('session-expired'))
    throw new ApiError(typeof error?.detail === 'string' ? error.detail : `API trả về lỗi ${response.status}. Vui lòng thử lại.`, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function loadPrescriptions(): Promise<Prescription[]> {
  const rows: RawPrescription[] = []
  for (let offset = 0; ; offset += 100) {
    const page = await api<{ items: RawPrescription[] }>(`/prescriptions?limit=100&offset=${offset}`)
    rows.push(...page.items)
    if (page.items.length < 100) break
  }
  return rows.map(row => ({ id: row.id, name: row.name, patient: 'Chưa cập nhật bệnh nhân', date: dateLabel(row.created_at), medications: row.medications, status: row.status, highest: severityLabel(row.highest_severity_vi), lastChecked: row.last_checked ? dateLabel(row.last_checked) : 'Chưa kiểm tra', checks: row.checks_count || 0, context: { conditions: row.patient_context?.conditions ?? [], genes: row.patient_context?.genes ?? {} } }))
}

let contextOptions: Promise<ContextOptions> | null = null

// Danh mục bệnh nền và kết quả gen mà CSDL có bản ghi; tải một lần cho cả phiên.
export function loadContextOptions(): Promise<ContextOptions> {
  if (!contextOptions) {
    contextOptions = api<ContextOptions>('/patient-context/options')
    contextOptions.catch(() => { contextOptions = null })
  }
  return contextOptions
}

export async function loadReviews(): Promise<ReviewRequest[]> {
  const rows: RawReview[] = []
  for (let offset = 0; ; offset += 100) {
    const page = await api<{ items: RawReview[] }>(`/reviews?limit=100&offset=${offset}`)
    rows.push(...page.items)
    if (page.items.length < 100) break
  }
  return rows.map(row => ({ id: String(row.id), prescriptionId: row.prescription_id, patient: row.patient || 'Chưa cập nhật bệnh nhân', message: row.message || '', date: dateLabel(row.created_at), status: row.status, medCount: row.med_count, createdBy: row.created_by ?? null, creatorName: row.creator_name || '', response: row.response || '', responderName: row.responder_name || '', respondedAt: row.responded_at ? dateLabel(row.responded_at) : '' }))
}

export type PairExplanation = { text: string; source: 'llm' | 'template' | 'none'; refs: { label: string; url: string }[] }
type RawExplainedPair = { explanation: string; explanation_source: PairExplanation['source']; mechanisms: { source_id: string; interaction_id: number; source_url: string }[]; form_notes: { source_id: string; rule_id: string; source_url: string }[] }
type PendingExplanation = { promise: Promise<PairExplanation | null>; stages: ProgressStage[]; listeners: Set<(stages: ProgressStage[]) => void> }
const explanations = new Map<string, PendingExplanation>()

// Lời giải thích tiếng Việt cho một cặp thuốc; null khi CSDL chưa có bản ghi của cặp. Số [k] trong text ứng với refs[k-1].
// onStages nhận các bước backend đã chạy; nhiều nơi cùng chờ một cặp thì cùng nhận, nơi mở sau thấy cả các bước trước.
export function explainPair(a: string, b: string, onStages?: (stages: ProgressStage[]) => void): { promise: Promise<PairExplanation | null>; unsubscribe: () => void } {
  const key = [a, b].sort().join('|')
  let pending = explanations.get(key)
  if (!pending) {
    const entry: PendingExplanation = { stages: [], listeners: new Set(), promise: Promise.resolve(null) }
    entry.promise = streamPost<{ pairs: RawExplainedPair[] }>('/interactions/explain', { drugs: [a, b] }, stage => {
      if (entry.stages.at(-1)?.stage === stage.stage) return
      entry.stages = [...entry.stages, stage]
      entry.listeners.forEach(listener => listener(entry.stages))
    }).then(({ pairs }) => pairs[0] ? { text: pairs[0].explanation, source: pairs[0].explanation_source, refs: [...pairs[0].mechanisms.map(m => ({ label: `${m.source_id} · bản ghi ${m.interaction_id}`, url: m.source_url })), ...pairs[0].form_notes.map(n => ({ label: `${n.source_id} · quy tắc ${n.rule_id}`, url: n.source_url }))] } : null)
    entry.promise.catch(() => explanations.delete(key)).finally(() => entry.listeners.clear())
    explanations.set(key, entry)
    pending = entry
  }
  const current = pending
  if (onStages) {
    current.listeners.add(onStages)
    if (current.stages.length) onStages(current.stages)
  }
  return { promise: current.promise, unsubscribe: () => { if (onStages) current.listeners.delete(onStages) } }
}

export function findingsOf(record: CheckRecord): Finding[] {
  return (record.findings || []).map((row, id) => ({ id, untranslatedFields: row.untranslated_fields ?? [], machineTranslation: row.machine_translation ?? false, severity: severityLabel(row.severity_vi), a: row.pair[0] || '', b: row.pair[1] || '', kind: 'Thuốc - thuốc', text: row.summary, management: row.management, citations: row.citations, sources: row.citations.length }))
}

export type AssistantUsage = { api_calls: number; measured: boolean; input_tokens: number; cached_input_tokens: number; output_tokens: number; total_tokens: number; cost_usd_min: number | null; cost_usd_max: number | null; pricing_date: string }
export type AssistantReply = {
  usage: AssistantUsage
  reply: string
  mode: 'evidence-only'
  llm_used: boolean
  fallback_reason: string
  status: 'answered' | 'needs_clarification' | 'no_evidence' | 'out_of_scope'
  check_id: string
  findings: unknown[]
  citations: Citation[]
  limitations: string[]
  disclaimer: string
}
export type ProgressStage = { stage: string; label: string }

// Hỏi trợ lý: nhận từng bước đang chạy, câu trả lời chỉ đến một lần sau khi backend đã kiểm chứng.
export function askAssistant(body: unknown, onStage: (stage: ProgressStage) => void, signal?: AbortSignal): Promise<AssistantReply> {
  return streamPost<AssistantReply>('/assistant/chat', body, onStage, signal)
}

const LOST = 'Mất kết nối với máy chủ trước khi có kết quả. Vui lòng thử lại.'

// Gọi `${path}/stream` (SSE): sự kiện `stage` cho từng bước, rồi `done` mang kết quả hoặc `error`.
// Backend cũ chưa có endpoint stream (404/405) thì gọi `path` trả JSON một lần.
async function streamPost<T>(path: string, body: unknown, onStage: (stage: ProgressStage) => void, signal?: AbortSignal): Promise<T> {
  const timeout = AbortSignal.timeout(90000)
  let response: Response
  try {
    response = await fetch(`/api/v1${path}/stream`, { method: 'POST', cache: 'no-store', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' }, body: JSON.stringify(body), signal: signal && 'any' in AbortSignal ? AbortSignal.any([signal, timeout]) : signal ?? timeout })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new Error('Không kết nối được backend. Hãy kiểm tra dịch vụ API và thử lại.')
  }
  if (response.status === 404 || response.status === 405) return api<T>(path, body)
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    if (response.status === 401 && typeof window !== 'undefined') window.dispatchEvent(new Event('session-expired'))
    throw new ApiError(typeof error?.detail === 'string' ? error.detail : `API trả về lỗi ${response.status}. Vui lòng thử lại.`, response.status)
  }
  if (!response.headers.get('content-type')?.includes('text/event-stream') || !response.body) return response.json() as Promise<T>
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    for (;;) {
      const { value, done } = await reader.read()
      buffer = (buffer + decoder.decode(value, { stream: !done })).replace(/\r\n/g, '\n')
      let end: number
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const block = buffer.slice(0, end)
        buffer = buffer.slice(end + 2)
        const event = block.match(/^event: ?(.*)$/m)?.[1]
        const data = block.split('\n').filter(line => line.startsWith('data:')).map(line => line.replace(/^data: ?/, '')).join('\n')
        if (!event || !data) continue
        const payload = JSON.parse(data)
        if (event === 'stage') onStage(payload as ProgressStage)
        else if (event === 'done') return payload as T
        else if (event === 'error') throw new ApiError(typeof payload.detail === 'string' ? payload.detail : 'Hệ thống gặp lỗi. Vui lòng thử lại.', Number(payload.status) || 500)
      }
      if (done) break
    }
  } catch (error) {
    if (error instanceof ApiError || signal?.aborted) throw error
    throw new Error(LOST)
  } finally { reader.cancel().catch(() => undefined) }
  throw new Error(LOST)
}
