export type Severity = 'Nghiêm trọng' | 'Trung bình' | 'Nhẹ'
export type Status = 'Chưa kiểm tra' | 'Đã kiểm tra' | 'Có tương tác' | 'Cần xem lại'
export type Medication = { id: number; name: string; ingredient: string; dose: string; frequency: string; type: 'Kê đơn' | 'OTC' | 'Bổ sung'; verified: boolean }
export type Prescription = { id: string; name?: string; patient: string; date: string; medications: Medication[]; status: Status; highest: Severity | null; lastChecked: string; checks: number }
export type ReviewRequest = { id: string; prescriptionId: string; patient: string; message: string; date: string; status: 'Đang chờ' | 'Đã phản hồi'; medCount: number }
export type Citation = { source_id: string; source_name: string; label: string; source_url: string }
export type Finding = { id: number; severity: Severity | null; a: string; b: string; kind: string; text: string; management: string; citations: Citation[]; sources: number }
export type CheckRecord = { check_id: string; created_at?: string | null; status: string; summary: { meds_count?: number; findings_count?: number }; max_severity: string; findings?: RawFinding[]; disclaimer?: string; unknown?: unknown[]; no_record_pairs?: string[][] }
type RawFinding = { pair: string[]; severity_vi: string; summary: string; management: string; citations: Citation[] }
type RawPrescription = { id: string; name?: string; created_at?: string | null; last_checked?: string | null; status: Status; highest_severity_vi?: string | null; checks_count: number; medications: Medication[] }
type RawReview = { id: number; prescription_id: string; patient: string; message: string; created_at: string; status: 'Đang chờ' | 'Đã phản hồi'; med_count: number }
export const dateLabel = (value?: string | null) => value ? new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`).toLocaleString('vi-VN') : 'Chưa cập nhật'
export const severityLabel = (value?: string | null): Severity | null => value === 'Nghiêm trọng' || value === 'Trung bình' || value === 'Nhẹ' ? value : null

export async function api<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, { method: body === undefined ? 'GET' : 'POST', cache: 'no-store', headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(90000) })
  } catch {
    throw new Error('Không kết nối được backend. Hãy kiểm tra dịch vụ API và thử lại.')
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(typeof error?.detail === 'string' ? error.detail : `API trả về lỗi ${response.status}. Vui lòng thử lại.`)
  }
  return response.json() as Promise<T>
}

export async function loadPrescriptions(): Promise<Prescription[]> {
  const rows: RawPrescription[] = []
  for (let offset = 0; ; offset += 100) {
    const page = await api<{ items: RawPrescription[] }>(`/prescriptions?limit=100&offset=${offset}`)
    rows.push(...page.items)
    if (page.items.length < 100) break
  }
  return rows.map(row => ({ id: row.id, name: row.name, patient: 'Chưa cập nhật bệnh nhân', date: dateLabel(row.created_at), medications: row.medications, status: row.status, highest: severityLabel(row.highest_severity_vi), lastChecked: row.last_checked ? dateLabel(row.last_checked) : 'Chưa kiểm tra', checks: row.checks_count || 0 }))
}

export async function loadReviews(): Promise<ReviewRequest[]> {
  const rows: RawReview[] = []
  for (let offset = 0; ; offset += 100) {
    const page = await api<{ items: RawReview[] }>(`/reviews?limit=100&offset=${offset}`)
    rows.push(...page.items)
    if (page.items.length < 100) break
  }
  return rows.map(row => ({ id: String(row.id), prescriptionId: row.prescription_id, patient: row.patient || 'Chưa cập nhật bệnh nhân', message: row.message || '', date: dateLabel(row.created_at), status: row.status, medCount: row.med_count }))
}

export function findingsOf(record: CheckRecord): Finding[] {
  return (record.findings || []).map((row, id) => ({ id, severity: severityLabel(row.severity_vi), a: row.pair[0] || '', b: row.pair[1] || '', kind: 'Thuốc - thuốc', text: row.summary, management: row.management, citations: row.citations, sources: row.citations.length }))
}
