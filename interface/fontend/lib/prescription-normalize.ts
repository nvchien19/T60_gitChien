export type MedicationDraft = { name: string; dose: string; frequency: string }
export type PrescriptionExtraction = { name: string; medications: MedicationDraft[]; unparsedLines: string[] }
export type CatalogProduct = { product_id: number; name: string; strength: string | null; active_ingredients: string | null }

// Match on accent-free text, but return the original characters and numeric values.
const key = (text: string) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase()
const numberPrefix = /^\s*\d{1,3}(?:\s*[.)\-:]\s*|\s+(?=\p{L}))/u
const strengthPart = String.raw`\d+(?:[.,]\d+)?\s*(?:mcg|µg|μg|mg|kg|g|m[lL]|[lL]|[iI][uU]|[uU][iI]|%)(?![\p{L}])(?:\s*\/\s*(?:\d+(?:[.,]\d+)?\s*)?(?:m[lL]|g|viên)(?![\p{L}]))?`
const strengthPattern = new RegExp(`${strengthPart}(?:\\s*[+/,;]\\s*${strengthPart})*`, 'iu')
const instructionStart = /^(?:cach dung|lieu dung|uong|ngay|sang|trua|chieu|toi|sau an|truoc an|boi|nho|xit|tiem|ngam|nhai|dung ngoai|dung theo|moi lan|lan|trong|so luong|sl)(?=\s|:|$)/
const numericInstruction = /^\d+(?:[.,]\d+)?\s*(?:lan\s*\/|vien\s*\/|ml\s*\/|ngay(?:\s|$))/
const metadata = /^(?:ho\s*(?:va\s*)?ten|benh nhan|chan doan|dia chi|dien thoai|ngay sinh|nam sinh|tuoi|gioi tinh|ma (?:benh nhan|don)|ten don(?: thuoc)?|ngay (?:kham|lap|ke)|ngay\s*\d|phong kham|benh vien|bac si|bs\.?|nguoi lap|tai kham|loi dan|luu y|chu ky|ky ten|tong cong|du lieu|khong (?:dung|co)|don thuoc|stt|ten thuoc)(?=\s|:|$)/
const quantityOnly = /^\d+\s*(?:vien|chai|lo|ong|goi|hop|tuyp)(?:\s|$)/
const formOnly = /^(?:vien (?:nen|nang)|dung dich|hon dich|siro|kem|thuoc mo)(?:\s|$)/

function tidyStrength(value: string) {
  return value.replace(/(\d)\s*(mcg|µg|μg|mg|kg|g|ml|l|iu|ui)/gi, '$1 $2')
    .replace(/\s*([+/])\s*/g, ' $1 ').replace(/\s+/g, ' ').trim()
    .replace(/\s*\/\s*(?=\d*\s*(?:ml|g|viên)\b)/gi, '/')
}

function tidyInstructions(value: string) {
  const text = value.replace(/^[\s|;,–—:-]+/, '').replace(/[|]/g, '; ').replace(/\s+/g, ' ').trim()
  return quantityOnly.test(key(text)) ? `Số lượng: ${text}` : text
}

function cleanDrugName(value: string) {
  return value.replace(/\(([^)]*)\)/g, (_, inner: string) => {
    const label = inner.replace(new RegExp(strengthPattern.source, 'giu'), '').replace(/\s+/g, ' ').trim()
    return label ? `(${label})` : ''
  }).replace(/[\s|;,–—:(]+$/, '').replace(/\s+/g, ' ').trim()
}

function drugFields(line: string): MedicationDraft {
  const cells = line.split(/\s*\|\s*/)
  const drugCells: string[] = []
  const quantity: string[] = []
  const instructions: string[] = []
  let inQuantity = false
  for (const cell of cells) {
    if (drugCells.length && /^\d+\s*(?:vien|chai|lo|ong|goi|hop|tuyp)?$/.test(key(cell))) {
      inQuantity = true; quantity.push(cell)
    } else if (inQuantity && /^(?:vien|chai|lo|ong|goi|hop|tuyp)$/.test(key(cell))) quantity.push(cell)
    else if (inQuantity) instructions.push(cell)
    else drugCells.push(cell)
  }
  const drugText = drugCells.join(' ')
  const matches = [...drugText.matchAll(new RegExp(strengthPattern.source, 'giu'))]
  // A composition/brand in parentheses can contain a different strength.
  // Prefer the dose printed outside those parentheses on the actual drug row.
  const strength = matches.find(match => {
    let depth = 0
    for (const character of drugText.slice(0, match.index)) {
      if (character === '(') depth++
      if (character === ')') depth = Math.max(0, depth - 1)
    }
    return depth === 0
  }) || matches[0]
  if (!strength) return { name: cleanDrugName(drugText), dose: '', frequency: [...instructions, ...(quantity.length ? [`Số lượng: ${quantity.join(' ')}`] : [])].join('; ') }
  let name = drugText.slice(0, strength.index)
  let trailing = drugText.slice((strength.index ?? 0) + strength[0].length).trim()
  while (trailing.startsWith('(')) {
    const end = trailing.indexOf(')')
    if (end < 0) break
    name += ' ' + trailing.slice(0, end + 1)
    trailing = trailing.slice(end + 1).trim()
  }
  // Do not leave the closing bracket of an inline strength in the instructions.
  if (name.includes('(') && trailing.startsWith(')')) { name += ')'; trailing = trailing.slice(1).trim() }
  return {
    name: cleanDrugName(name), dose: tidyStrength(strength[0]),
    frequency: [tidyInstructions(trailing), ...instructions, ...(quantity.length ? [`Số lượng: ${quantity.join(' ')}`] : [])].filter(Boolean).join('; '),
  }
}

export function extractPrescriptionText(text: string): PrescriptionExtraction {
  const result: PrescriptionExtraction = { name: '', medications: [], unparsedLines: [] }
  let current: MedicationDraft | undefined
  let pendingName = ''
  for (const raw of text.normalize('NFC').split(/\r?\n/)) {
    const line = raw.replace(/\s+/g, ' ').trim()
    if (!line) continue
    const numbered = numberPrefix.test(line)
    const cleaned = line.replace(numberPrefix, '').replace(/^\|\s*/, '')
    const folded = key(cleaned)
    if (/^hoat chat(?=\s|:|$)/.test(folded)) continue
    if (metadata.test(folded) || /^ngay\s+\d{1,2}(?:[/.\-]\d{1,2}|\s+thang)/.test(folded)) {
      const label = key(line).match(/^(?:ten don(?: thuoc)?|ma don)\s*:/)
      if (label && !result.name) result.name = line.slice(line.indexOf(':') + 1).trim()
      current = undefined; pendingName = ''
      continue
    }
    // An instruction may contain its own numbered doses; it is never a new drug.
    const originalKey = key(line)
    if (instructionStart.test(folded) || numericInstruction.test(originalKey) || quantityOnly.test(originalKey)) {
      if (current) {
        const instruction = quantityOnly.test(originalKey) ? `Số lượng: ${line}` : numericInstruction.test(originalKey) ? line : cleaned
        current.frequency += (current.frequency ? '; ' : '') + tidyInstructions(instruction)
      } else result.unparsedLines.push(line)
      continue
    }
    if (formOnly.test(folded) && current && !numbered && !strengthPattern.test(cleaned)) continue
    const strength = cleaned.match(strengthPattern)
    if (strength && strength.index === 0 && current && !current.dose) {
      current.dose = tidyStrength(strength[0])
      current.frequency = tidyInstructions(cleaned.slice(strength[0].length))
      continue
    }
    // A brand without a strength can wrap onto the following line.
    if (numbered || (strength && (strength.index ?? 0) > 0)) {
      const row = drugFields(cleaned)
      if (!row.name || !/\p{L}/u.test(row.name)) { result.unparsedLines.push(line); continue }
      current = row
      result.medications.push(current)
      pendingName = ''
      continue
    }
    if (strength?.index === 0 && pendingName) {
      current = { name: pendingName, dose: tidyStrength(strength[0]), frequency: tidyInstructions(cleaned.slice(strength[0].length)) }
      result.medications.push(current)
      result.unparsedLines = result.unparsedLines.filter(value => value !== pendingName)
      pendingName = ''
      continue
    }
    result.unparsedLines.push(line)
    pendingName = !current && /^[\p{L}][\p{L}\p{N}\s().+\/-]{1,100}$/u.test(line) ? line : ''
  }
  return result
}

export function normalizePrescriptionText(text: string): MedicationDraft[] {
  return extractPrescriptionText(text).medications
}

// Parenthetical brands/form descriptions belong in the OCR display, but the
// base name is also a useful catalog lookup. It never replaces the source name.
export function prescriptionLookupName(name: string): string {
  const base = name.split('(')[0].replace(/[\s,;:-]+$/, '').trim()
  return base.length >= 2 ? base : name
}

export function matchCatalogProduct(row: MedicationDraft, products: CatalogProduct[]): CatalogProduct | undefined {
  const nameKey = key(row.name).replace(/\s+/g, ' ').trim()
  const doseKey = key(row.dose).replace(/\s+/g, '')
  return products.find(product => {
    const parsed = normalizePrescriptionText(`1. ${product.name}`)[0]
    const productName = key(parsed?.name || product.name).replace(/\s+/g, ' ').trim()
    const strength = key(product.strength || parsed?.dose || '').replace(/\s+/g, '')
    return productName === nameKey && (!doseKey || doseKey === strength)
  })
}

// Reapplying corrected OCR replaces only the previous imported rows.
// Manual rows, saved medication IDs, and intentional duplicate drugs survive.
export function replaceOcrRows<T extends MedicationDraft & { ocrSource?: boolean }>(rows: T[], extracted: MedicationDraft[]) {
  return [...rows.filter(row => !row.ocrSource && (row.name.trim() || row.dose.trim() || row.frequency.trim())),
    ...extracted.map(row => ({ ...row, ocrSource: true }))]
}
