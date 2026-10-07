import { api } from '@/lib/api'
import { prescriptionCropRegion, type PrescriptionImageCrop } from '@/lib/prescription-ocr'

type GeminiMedication = { name: string; dose: string; frequency: string; quantity: string; uncertain_fields: string[] }
export type GeminiPrescription = { name: string; raw_text: string; medications: GeminiMedication[]; warnings: string[]; model: string; provider: 'gemini'; attempted_models?: string[] }

export async function recognizePrescriptionWithGemini(file: File, crop?: PrescriptionImageCrop): Promise<GeminiPrescription> {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  try {
    if (!bitmap.width || !bitmap.height || bitmap.width * bitmap.height > 40000000) throw new Error('Ảnh quá lớn. Hãy chọn ảnh dưới 40 megapixel.')
    const region = prescriptionCropRegion(bitmap.width, bitmap.height, crop)
    const scale = Math.min(1, 2400 / region.width, 3600 / region.height)
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(region.width * scale))
    canvas.height = Math.max(1, Math.round(region.height * scale))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Trình duyệt không hỗ trợ xử lý ảnh.')
    context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, region.x, region.y, region.width, region.height, 0, 0, canvas.width, canvas.height)
    const url = canvas.toDataURL('image/jpeg', .92)
    const image_base64 = url.split(',')[1]
    if (!image_base64 || image_base64.length > 5592408) throw new Error('Ảnh gửi Gemini quá lớn. Chọn vùng thuốc nhỏ hơn.')
    return await api<GeminiPrescription>('/prescription-ocr', { mime_type: 'image/jpeg', image_base64, model: 'auto' })
  } finally { bitmap.close() }
}
