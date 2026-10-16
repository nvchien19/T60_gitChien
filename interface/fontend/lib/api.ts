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
export type FoodFinding = RawFinding & { original_management?: string; original_mechanism?: string }
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
const explanations = new Map<string, Promise<PairExplanation | null>>()

// Lời giải thích tiếng Việt cho một cặp thuốc; null khi CSDL chưa có bản ghi của cặp. Số [k] trong text ứng với refs[k-1].
export function explainPair(a: string, b: string): Promise<PairExplanation | null> {
  const key = [a, b].sort().join('|')
  let pending = explanations.get(key)
  if (!pending) {
    pending = api<{ pairs: RawExplainedPair[] }>('/interactions/explain', { drugs: [a, b] }).then(({ pairs }) => pairs[0] ? { text: pairs[0].explanation, source: pairs[0].explanation_source, refs: [...pairs[0].mechanisms.map(m => ({ label: `${m.source_id} · bản ghi ${m.interaction_id}`, url: m.source_url })), ...pairs[0].form_notes.map(n => ({ label: `${n.source_id} · quy tắc ${n.rule_id}`, url: n.source_url }))] } : null)
    explanations.set(key, pending)
    pending.catch(() => explanations.delete(key))
  }
  return pending
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
