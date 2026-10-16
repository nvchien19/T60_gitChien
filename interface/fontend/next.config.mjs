/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['127.0.0.1'],
  // Không đặt CSP chặn script vì Next.js cần script nội tuyến; chỉ chặn nhúng trang, plugin và đổi base URL.
  async headers() {
    const security = [
      { key: 'Content-Security-Policy', value: "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'" },
      { key: 'X-Frame-Options', value: 'DENY' },
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=(), usb=()' },
    ]
    if (process.env.NODE_ENV === 'production') {
      security.push({ key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' })
    }
    return [{ source: '/:path*', headers: security }]
  },
  async rewrites() {
    const backend = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
    return [{ source: '/api/v1/:path*', destination: `${backend}/api/v1/:path*` }]
  },

  images: {
    unoptimized: true,
  },
}

export default nextConfig
