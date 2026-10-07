// Keep image decoding and preprocessing local to the user's browser.
export type PrescriptionImageCrop = { x: number; y: number; width: number; height: number }

export function prescriptionCropRegion(width: number, height: number, crop?: PrescriptionImageCrop) {
  if (!crop) return { x: 0, y: 0, width, height }
  if (![crop.x, crop.y, crop.width, crop.height].every(Number.isFinite) || crop.width <= 0 || crop.height <= 0) throw new Error('Vùng thuốc không hợp lệ.')
  const x = Math.max(0, Math.min(width - 1, Math.round(crop.x * width)))
  const y = Math.max(0, Math.min(height - 1, Math.round(crop.y * height)))
  return { x, y, width: Math.max(1, Math.min(width - x, Math.round(crop.width * width))), height: Math.max(1, Math.min(height - y, Math.round(crop.height * height))) }
}

export async function preparePrescriptionImage(file: File, crop?: PrescriptionImageCrop): Promise<HTMLCanvasElement> {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  try {
    if (!bitmap.width || !bitmap.height || bitmap.width * bitmap.height > 40000000) {
      throw new Error('Ảnh quá lớn. Hãy chọn ảnh dưới 40 megapixel.')
    }
    const region = prescriptionCropRegion(bitmap.width, bitmap.height, crop)
    const scale = Math.min(3, 2400 / region.width, 3600 / region.height)
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(region.width * scale))
    canvas.height = Math.max(1, Math.round(region.height * scale))
    const context = canvas.getContext('2d', { willReadFrequently: true })
    if (!context) throw new Error('Trình duyệt không hỗ trợ xử lý ảnh.')
    context.fillStyle = '#fff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, region.x, region.y, region.width, region.height, 0, 0, canvas.width, canvas.height)
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height)
    for (let i = 0; i < pixels.data.length; i += 4) {
      const grey = .299 * pixels.data[i] + .587 * pixels.data[i + 1] + .114 * pixels.data[i + 2]
      // A mild contrast adjustment preserves faint decimal points and accents.
      const value = Math.max(0, Math.min(255, (grey - 128) * 1.12 + 128))
      pixels.data[i] = pixels.data[i + 1] = pixels.data[i + 2] = value
    }
    context.putImageData(pixels, 0, 0)
    return canvas
  } finally { bitmap.close() }
}
