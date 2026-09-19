import { execFileSync } from "node:child_process"
import { appendFileSync, readFileSync } from "node:fs"
import { join } from "node:path"

const VN_OFFSET_MS = 7 * 3600 * 1000
const LOG_FILE = ".ai-log"
const SESSION_FILE = "session.jsonl"

function git(cwd, cmd, ...args) {
  try {
    return execFileSync(cmd, args, { cwd, encoding: "utf8" }).trim()
  } catch {
    return ""
  }
}

function toVnIso(epochMs) {
  const d = new Date(epochMs + VN_OFFSET_MS)
  const pad = (n) => String(n).padStart(2, "0")
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}` +
    `.${String(d.getUTCMilliseconds()).padStart(3, "0")}+07:00`
  )
}

function repoContext(cwd) {
  const origin = git(cwd, "git", "remote", "get-url", "origin")
  const parts = origin.split("/").filter(Boolean)
  let repo = parts.length ? parts[parts.length - 1] : ""
  if (repo.endsWith(".git")) repo = repo.slice(0, -4)
  return {
    repo: repo || "unknown",
    branch: git(cwd, "git", "rev-parse", "--abbrev-ref", "HEAD"),
    commit: git(cwd, "git", "rev-parse", "--short", "HEAD"),
    student: git(cwd, "git", "config", "user.email"),
  }
}

export default async ({ worktree, directory }) => {
  const root = worktree || directory
  const logPath = join(root, LOG_FILE, SESSION_FILE)
  const seen = new Set()
  try {
    for (const line of readFileSync(logPath, "utf8").split("\n")) {
      const t = line.trim()
      if (!t) continue
      try {
        const id = JSON.parse(t).entry_id
        if (id) seen.add(id)
      } catch {}
    }
  } catch {}

  return {
    "chat.message": async (input, output) => {
      const message = (output && output.message) || {}
      if (message.role && message.role !== "user") return
      const prompt = (output.parts || [])
        .filter((p) => p.type === "text" && !p.synthetic)
        .map((p) => p.text || "")
        .join("\n")
        .trim()
      if (prompt.length < 2) return
      const entryId = `opencode-msg_${input.messageID || message.id}`
      if (seen.has(entryId)) return
      seen.add(entryId)
      const model = input.model || message.model || {}
      const ctx = repoContext(root)
      const entry = {
        ts: toVnIso(Date.now()),
        tool: "opencode",
        event: "UserPromptSubmit",
        entry_id: entryId,
        session_id: input.sessionID,
        model:
          model.providerID && model.modelID
            ? `${model.providerID}/${model.modelID}`
            : "opencode",
        repo: ctx.repo,
        branch: ctx.branch,
        commit: ctx.commit,
        student: ctx.student,
        prompt: prompt.slice(0, 1000),
        response_summary: "",
      }
      try {
        appendFileSync(logPath, JSON.stringify(entry) + "\n", "utf8")
      } catch {}
    },
  }
}