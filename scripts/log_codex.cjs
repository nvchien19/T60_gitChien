// Codex prompt logger. Same JSONL contract as .opencode/plugin/ai-log.ts.
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { createHash } = require('node:crypto');

function main() {
  const input = JSON.parse(fs.readFileSync(0, 'utf8').replace(/^\uFEFF/, ''));
  if (input.hook_event_name !== 'UserPromptSubmit') return;
  const prompt = typeof input.prompt === 'string' ? input.prompt.trim() : '';
  if (!prompt || !input.session_id || !input.turn_id) return;
  const git = (...args) => execFileSync('git', args, {
    cwd: __dirname, encoding: 'utf8', windowsHide: true,
    stdio: ['ignore', 'pipe', 'ignore'], timeout: 2000,
  }).trim();
  const root = git('rev-parse', '--show-toplevel');
  const origin = git('remote', 'get-url', 'origin');
  const student = git('config', 'user.email');
  if (!root || !origin || !student) return;
  const logDir = process.env.AI_LOG_DIR
    ? path.resolve(root, process.env.AI_LOG_DIR) : path.join(root, '.ai-log');
  const logFile = path.join(logDir, 'session.jsonl');
  const digest = createHash('sha256').update(prompt).digest('hex').slice(0, 16);
  const entryId = `codex-${input.session_id}-${input.turn_id}-${digest}`;
  const contains = (file) => {
    try {
      return fs.readFileSync(file, 'utf8').split('\n').some((line) => {
        try { return JSON.parse(line).entry_id === entryId; } catch { return false; }
      });
    } catch { return false; }
  };
  if (contains(logFile)) return;
  const archive = path.join(logDir, 'archive');
  if (fs.existsSync(archive) && fs.readdirSync(archive)
    .some((name) => name.endsWith('.jsonl') && contains(path.join(archive, name)))) return;
  const entry = {
    ts: new Date(Date.now() + 7 * 3600 * 1000).toISOString().replace('Z', '+07:00'),
    tool: 'codex', event: 'UserPromptSubmit', entry_id: entryId,
    session_id: input.session_id, model: input.model || '',
    repo: origin.replace(/\/$/, '').split('/').pop().replace(/\.git$/, ''),
    branch: git('rev-parse', '--abbrev-ref', 'HEAD'),
    commit: git('rev-parse', '--short', 'HEAD'), student,
    prompt: prompt.slice(0, 1000),
  };
  fs.mkdirSync(logDir, { recursive: true });
  fs.appendFileSync(logFile, JSON.stringify(entry) + '\n', 'utf8');
}

// Logging failures must not block the conversation, as with OpenCode.
try { main(); } catch {}
