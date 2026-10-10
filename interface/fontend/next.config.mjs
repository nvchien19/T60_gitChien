/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['127.0.0.1'],
  async rewrites() {
    const backend = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
    return [{ source: '/api/v1/:path*', destination: `${backend}/api/v1/:path*` }]
  },

  images: {
    unoptimized: true,
  },
}

export default nextConfig
