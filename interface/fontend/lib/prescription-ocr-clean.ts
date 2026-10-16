// OCR can include row numbers or a clinic footer in the medication-name field.
// Keep only plausible medicine names before catalog lookup or saving a prescription.
const fold = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase()
const administrative = /(?:^|\b)(?:zalo|sdt|dien thoai|so dien thoai|phong kham|benh vien|bac si|dia chi|benh nhan|sinh hieu|huyet ap|dat lich|tai kham|chan doan)(?:\b|$)/
const contact = /(?:https?:\/\/|www\.|@|(?:\+?84|0)[\d.\s-]{8,})/i

export function cleanOcrMedicationName(raw: string): string | null {
  const name = raw.replace(/^\s*(?:\d{1,3}\s*[/.)\-:]\s*)+/u, '').replace(/\s+/g, ' ').trim()
  if (!name || !/\p{L}/u.test(name) || administrative.test(fold(name)) || contact.test(name)) return null
  return name
}

export function cleanOcrMedications<T extends { name: string }>(rows: T[]): { medications: T[]; rejected: number } {
  const medications: T[] = []
  for (const row of rows) {
    const name = cleanOcrMedicationName(row.name)
    if (name) medications.push({ ...row, name })
  }
  return { medications, rejected: rows.length - medications.length }
}
