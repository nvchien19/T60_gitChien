import type { Hooks, PluginInput } from "@opencode-ai/plugin"
import type { Part, TextPart, UserMessage } from "@opencode-ai/sdk"
import { appendFileSync, mkdirSync, readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"

const VN_TZ_OFFSET_MS = 7 * 3600 * 1000

function vnIso(): string {
  const d = new Date(Date.now() + VN_TZ_OFFSET_MS)
  return d.toISOString().replace("Z", "+07:00")
}

export default (async ({ directory, $ }: PluginInput) => {
  const sh = $.cwd(directory).nothrow()

  const root = (await sh`git rev-parse --show-toplevel`.quiet().text()).trim()
  const origin = (await sh`git remote get-url origin`.quiet().text()).trim()
  const student = (await sh`git config user.email`.quiet().text()).trim()
  if (!root || !origin || !student) return {}

  const repo = origin.split("/").pop()?.replace(/\.git$/, "") ?? ""
  const logDir = join(root, ".ai-log")
  const logFile = join(logDir, "session.jsonl")
  mkdirSync(logDir, { recursive: true })

  const append = (entry: Record<string, unknown>) => {
    try {
      appendFileSync(logFile, JSON.stringify(entry) + "\n", "utf8")
    } catch {
      /* never break the TUI on log write failure */
    }
  }

  const seen = new Set<string>()
  const seed = (path: string) => {
    let raw: string
    try {
      raw = readFileSync(path, "utf8")
    } catch {
      return
    }
    for (const line of raw.split("\n")) {
      const trimmed = line.trim()
      if (!trimmed) continue
      try {
        const id = JSON.parse(trimmed).entry_id
        if (id) seen.add(id)
      } catch {}
    }
  }
  seed(logFile)
  try {
    const archiveDir = join(logDir, "archive")
    for (const name of readdirSync(archiveDir)) {
      if (name.endsWith(".jsonl")) seed(join(archiveDir, name))
    }
  } catch {}

  const hooks: Hooks = {
    async "chat.message"(
      input: {
        sessionID: string
      },
      output: { message: UserMessage; parts: Part[] },
    ) {
      try {
        const entryId = `opencode-${output.message.id}`
        if (seen.has(entryId)) return
        const text = output.parts
          .filter((p): p is TextPart => p.type === "text")
          .filter((p) => !p.synthetic)
          .map((p) => p.text ?? "")
          .join("\n")
          .trim()
        if (!text) return
        seen.add(entryId)

        const branch = (await sh`git rev-parse --abbrev-ref HEAD`.quiet().text()).trim()
        const commit = (await sh`git rev-parse --short HEAD`.quiet().text()).trim()
        const model = output.message.model

        append({
          ts: vnIso(),
          tool: "opencode",
          event: "UserPromptSubmit",
          entry_id: entryId,
          session_id: input.sessionID,
          model: `${model?.providerID ?? ""}/${model?.modelID ?? ""}`,
          repo,
          branch,
          commit,
          student,
          prompt: text.slice(0, 1000),
        })
      } catch {
        /* never break the TUI */
      }
    },
  }
  return hooks
})