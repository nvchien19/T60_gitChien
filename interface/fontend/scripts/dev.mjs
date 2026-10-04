import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import net from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const root = path.resolve(frontend, '../..')
const windows = process.platform === 'win32'
const backendPort = Number(process.env.BACKEND_PORT || 8000)
const frontendPort = Number(process.env.PORT || 3000)
const venvPython = path.join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python')
const python = process.env.PYTHON || (existsSync(venvPython) ? venvPython : windows ? 'python' : 'python3')
const children = []
let stopping = false

async function shutdown(code = 0) {
  if (stopping) return
  stopping = true
  await Promise.all(children.map(child => new Promise(resolve => {
    if (!child.pid) return resolve()
    if (windows) {
      // Python's Windows launcher and Next.js both create child processes.
      const killer = spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true })
      killer.once('error', resolve)
      killer.once('exit', resolve)
    } else {
      try { process.kill(-child.pid, 'SIGTERM') } catch { return resolve() }
      const timer = setTimeout(() => { try { process.kill(-child.pid, 'SIGKILL') } catch {} resolve() }, 3000)
      child.once('exit', () => { clearTimeout(timer); resolve() })
    }
  })))
  process.exit(code)
}

process.on('SIGINT', () => void shutdown())
process.on('SIGTERM', () => void shutdown())

function launch(label, command, args, cwd, env = process.env) {
  console.log(`[${label}] ${label === 'BE' ? `http://127.0.0.1:${backendPort}` : `http://localhost:${frontendPort}`}`)
  const child = spawn(command, args, { cwd, env, stdio: 'inherit', detached: !windows, windowsHide: true })
  children.push(child)
  child.once('error', error => {
    console.error(`[${label}] Không khởi động được: ${error.message}`)
    if (label === 'BE') console.error('Cài dependencies backend trong .venv hoặc đặt biến PYTHON trỏ đến Python đã cài requirements.txt.')
    void shutdown(1)
  })
  child.once('exit', (code, signal) => {
    if (!stopping) {
      console.log(`[${label}] Đã dừng (${signal || code}). Dừng cả hai dịch vụ.`)
      void shutdown(code || 0)
    }
  })
  return child
}

async function checkPort(port, label) {
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error(`${label}: cổng không hợp lệ.`)
  await new Promise((resolve, reject) => {
    const server = net.createServer()
    server.once('error', () => reject(new Error(`${label}: cổng ${port} đang được sử dụng. Dừng dịch vụ cũ rồi chạy lại npm run dev.`)))
    server.listen(port, '0.0.0.0', () => server.close(resolve))
  })
}

try {
  await checkPort(backendPort, 'BE')
  await checkPort(frontendPort, 'FE')
  if (backendPort === frontendPort) throw new Error('FE và BE cần hai cổng khác nhau.')
  launch('BE', python, ['-m', 'uvicorn', 'interface.backend.main:app', '--reload', '--host', '127.0.0.1', '--port', String(backendPort)], root)
  const deadline = Date.now() + 60000
  let ready = false
  while (!stopping && Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${backendPort}/health`, { signal: AbortSignal.timeout(1000) })
      if (response.ok) { ready = true; break }
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  if (!ready) throw new Error('Backend chưa sẵn sàng sau 60 giây. Kiểm tra lỗi backend phía trên.')
  if (!stopping) {
    launch('FE', process.execPath, [path.join(frontend, 'node_modules/next/dist/bin/next'), 'dev', '--port', String(frontendPort), ...process.argv.slice(2)], frontend, { ...process.env, BACKEND_URL: `http://127.0.0.1:${backendPort}` })
    console.log('Nhấn Ctrl+C để dừng cả frontend và backend.')
  }
} catch (error) {
  console.error(error.message)
  await shutdown(1)
}
