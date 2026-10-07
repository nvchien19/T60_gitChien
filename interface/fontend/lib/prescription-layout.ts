import { extractPrescriptionText } from './prescription-normalize'

export type OcrWord = { text: string; bbox: { x0: number; y0: number; x1: number; y1: number }; confidence: number }
export type OcrPage = { text: string; confidence: number; blocks?: { paragraphs: { lines: { words: OcrWord[] }[] }[] }[] | null }

// Tesseract's text output is in block/column order. Reassemble by physical position
// so quantities from the right column stay with the medication on their left.
export function prescriptionTextFromLayout(page: OcrPage): string {
  const words = (page.blocks || []).flatMap(block => block.paragraphs.flatMap(paragraph => paragraph.lines.flatMap(line => line.words)))
    .filter(word => word.text.trim() && word.bbox.x1 > word.bbox.x0 && word.bbox.y1 > word.bbox.y0)
    .sort((a, b) => (a.bbox.y0 + a.bbox.y1) / 2 - (b.bbox.y0 + b.bbox.y1) / 2 || a.bbox.x0 - b.bbox.x0)
  if (!words.length) return page.text
  const lines: { words: OcrWord[]; center: number; height: number }[] = []
  for (const word of words) {
    const center = (word.bbox.y0 + word.bbox.y1) / 2
    const height = word.bbox.y1 - word.bbox.y0
    const line = lines.slice(-3).find(candidate => Math.abs(candidate.center - center) <= Math.max(4, Math.min(candidate.height, height) * .55))
    if (line) {
      line.center = (line.center * line.words.length + center) / (line.words.length + 1)
      line.height = (line.height * line.words.length + height) / (line.words.length + 1)
      line.words.push(word)
    } else lines.push({ words: [word], center, height })
  }
  return lines.sort((a, b) => a.center - b.center).map(line => {
    const sorted = line.words.sort((a, b) => a.bbox.x0 - b.bbox.x0)
    return sorted.map((word, index) => {
      if (!index) return word.text.trim()
      const gap = word.bbox.x0 - sorted[index - 1].bbox.x1
      // Preserve a wide column gap rather than losing it when whitespace collapses.
      return `${gap > Math.max(24, line.height * 2.8) ? ' | ' : ' '}${word.text.trim()}`
    }).join('')
  }).join('\n')
}

export function prescriptionCandidateScore(text: string, confidence: number): number {
  const parsed = extractPrescriptionText(text)
  if (!parsed.medications.length) return -1000
  const numbered = text.split(/\r?\n/).filter(line => /^\s*\d{1,2}\s*[.)]\s*\p{L}/u.test(line)).length
  const medicineFields = parsed.medications.reduce((score, row) => score + 12 + (row.dose ? 4 : 0) + (row.frequency ? 2 : 0), 0)
  return medicineFields + Math.max(0, Math.min(100, confidence)) / 10 - Math.abs(numbered - parsed.medications.length) * 4
    - parsed.unparsedLines.length * .25
}

export function choosePrescriptionCandidate(pages: OcrPage[]): { text: string; confidence: number } {
  const candidates = pages.flatMap(page => [
    { text: prescriptionTextFromLayout(page), confidence: page.confidence },
    { text: page.text, confidence: page.confidence },
  ])
  return candidates.sort((a, b) => prescriptionCandidateScore(b.text, b.confidence) - prescriptionCandidateScore(a.text, a.confidence))[0]
    || { text: '', confidence: 0 }
}

export function prescriptionNeedsAnotherPass(text: string, confidence: number): boolean {
  const count = extractPrescriptionText(text).medications.length
  const sequence = text.split(/\r?\n/).map(line => line.match(/^\s*(\d{1,2})\s*[.)]\s*\p{L}/u)).filter(Boolean)
  const lastNumber = Math.max(0, ...sequence.map(match => Number(match![1])))
  return count < 2 || confidence < 70 || (lastNumber <= 50 && lastNumber > count)
}
