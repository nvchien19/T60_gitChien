import { spawn } from 'node:child_process'
import fs, { existsSync } from 'node:fs'
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

function killTree(child) {
  return new Promise(resolve => {
    if (!child.pid || child.exitCode !== null || child.signalCode !== null) return resolve()
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
  })
}

async function shutdown(code = 0) {
  if (stopping) return
  stopping = true
  await Promise.all(children.map(killTree))
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
    if (label === 'BE' && backendReady && !stopping && !child.restarting) {
      console.log(`[BE] Backend dừng (${signal || code}), có thể do lỗi trong mã. Sửa rồi lưu file .py để chạy lại.`)
    } else if (!stopping && !child.restarting) {
      console.log(`[${label}] Đã dừng (${signal || code}). Dừng cả hai dịch vụ.`)
      void shutdown(code || 0)
    }
  })
  return child
}

// Không dùng `uvicorn --reload`: trên Windows nó khởi động lại worker bằng CTRL_C_EVENT, sự kiện này không tới được
// tiến trình chạy ẩn (windowsHide), nên reloader chờ mãi và worker cũ tiếp tục chạy mã cũ. Ở đây tự theo dõi file .py
// rồi kill cả cây tiến trình backend và chạy lại.
// DEV_PARENT_PID: backend tự thoát khi tiến trình này chết đột ngột (đóng cửa sổ, kill), không để lại tiến trình mồ côi.
let backend = null
let backendReady = false  // sau lần chạy đầu thành công, backend chết vì lỗi mã thì chờ lần lưu sau, không dừng FE
function startBackend() {
  backend = launch('BE', python, ['-m', 'uvicorn', 'interface.backend.main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
    root, { ...process.env, DEV_PARENT_PID: String(process.pid) })
}

let restartTimer = null
let restarting = Promise.resolve()
function watchBackend() {
  const onChange = (dir, file) => {
    if (!file || !file.endsWith('.py') || file.includes('__pycache__') || stopping) return
    clearTimeout(restartTimer)
    restartTimer = setTimeout(() => {
      restarting = restarting.then(async () => {
        if (stopping) return
        console.log(`[BE] Phát hiện thay đổi ở ${path.join(dir, file)}, khởi động lại backend.`)
        const old = backend
        old.restarting = true
        await killTree(old)
        children.splice(children.indexOf(old), 1)
        if (!stopping) startBackend()
      })
    }, 500)
  }
  for (const dir of ['interface/backend', 'src']) {
    fs.watch(path.join(root, dir), { recursive: true }, (_event, file) => onChange(dir, file))
  }
}

// PID đang nghe cổng (chỉ Windows, qua netstat), để thông báo lỗi chỉ đúng tiến trình cần dừng.
function portOwners(port) {
  if (!windows) return Promise.resolve([])
  return new Promise(resolve => {
    const netstat = spawn('netstat', ['-ano', '-p', 'TCP'], { windowsHide: true })
    let out = ''
    netstat.stdout.on('data', chunk => { out += chunk })
    netstat.once('error', () => resolve([]))
    netstat.once('exit', () => resolve([...new Set(out.split(/\r?\n/)
      .map(line => line.trim().split(/\s+/))
      .filter(cols => cols[3] === 'LISTENING' && cols[1]?.endsWith(`:${port}`))
      .map(cols => cols[4]))]))
  })
}

async function checkPort(port, label) {
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error(`${label}: cổng không hợp lệ.`)
  // Thử cả 127.0.0.1: trên Windows, worker uvicorn cũ giữ 127.0.0.1:8000 thì 0.0.0.0:8000 vẫn bind được, và
  // uvicorn mới (đặt SO_REUSEADDR) cũng bind được, nên hai bản cùng nghe một cổng và bản cũ trả lời bằng mã cũ.
  for (const host of ['127.0.0.1', '0.0.0.0']) {
    const free = await new Promise(resolve => {
      const server = net.createServer()
      server.once('error', () => resolve(false))
      server.listen(port, host, () => server.close(() => resolve(true)))
    })
    if (!free) {
      const pids = await portOwners(port)
      const hint = pids.length ? ` Tiến trình đang giữ cổng: PID ${pids.join(', ')} (dừng bằng: Stop-Process -Id ${pids.join(',')} -Force).` : ''
      throw new Error(`${label}: cổng ${port} đang được sử dụng.${hint} Dừng dịch vụ cũ rồi chạy lại npm run dev.`)
    }
  }
}

try {
  await checkPort(backendPort, 'BE')
  await checkPort(frontendPort, 'FE')
  if (backendPort === frontendPort) throw new Error('FE và BE cần hai cổng khác nhau.')
  startBackend()
  watchBackend()
  if (!stopping) {
    launch('FE', process.execPath, [path.join(frontend, 'node_modules/next/dist/bin/next'), 'dev', '--port', String(frontendPort), ...process.argv.slice(2)], frontend, { ...process.env, BACKEND_URL: `http://127.0.0.1:${backendPort}` })
    console.log('Nhấn Ctrl+C để dừng cả frontend và backend.')
  }
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
  backendReady = true
} catch (error) {
  console.error(error.message)
  await shutdown(1)
}
