export type MedicationDraft = { name: string; dose: string; frequency: string }

// Preserve uncertain text for review; never infer ingredients or correct drug names.
export function normalizePrescriptionText(text: string): MedicationDraft[] {
  const rows: MedicationDraft[] = []
  for (const raw of text.normalize('NFC').split(/\r?\n/)) {
    const line = raw.replace(/\s+/g, ' ').trim()
    if (!line) continue
    if (/^(?:cách dùng|liều dùng|uống|ngày|sáng|trưa|chiều|tối|sau ăn|trước ăn)\b/iu.test(line) && rows.length) {
      rows[rows.length - 1].frequency += (rows[rows.length - 1].frequency ? ' ' : '') + line
      continue
    }
    const numbered = /^\d{1,2}\s*[.)-]\s*/.test(line)
    const cleaned = line.replace(/^\d{1,2}\s*[.)-]\s*/, '')
    const strength = cleaned.match(/\d+(?:[.,]\d+)?\s*(?:mcg|µg|mg|g|ml|iu|ui|%)(?:\s*\/\s*\d*\s*(?:ml|g|viên))?/i)
    if (!numbered && !strength) continue
    if (/^(?:họ tên|họ và tên|bệnh nhân|chẩn đoán|địa chỉ|điện thoại|ngày sinh|tuổi|tái khám)\s*:/iu.test(cleaned)) continue
    const index = strength?.index ?? -1
    const name = index > 0 ? cleaned.slice(0, index).trim() : cleaned
    if (!name || !/\p{L}/u.test(name)) continue
    rows.push({ name, dose: index > 0 ? strength![0].replace(/(\d)([a-zµ%])/i, '$1 $2') : '', frequency: index > 0 ? cleaned.slice(index + strength![0].length).replace(/^[\s,;:-]+/, '') : '' })
  }
  return rows
}
