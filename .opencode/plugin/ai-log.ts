import type { Plugin } from "@opencode-ai/plugin"
import type { UserMessage, TextPart } from "@opencode-ai/sdk"
import { appendFileSync, mkdirSync } from "node:fs"
import { join } from "node:path"

const VN_TZ_OFFSET_MS = 7 * 3600 * 1000

function vnIso(): string {
  const d = new Date(Date.now() + VN_TZ_OFFSET_MS)
  return d.toISOString().replace("Z", "+07:00")
}

export default (async ({ directory, $ }) => {
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

  return {
    async "chat.message"(
      input: {
        sessionID: string
      },
      output: { message: UserMessage; parts: TextPart[] },
    ) {
      try {
        if (seen.has(output.message.id)) return
        const text = (output.parts ?? [])
          .filter((p) => p.type === "text" && !p.synthetic)
          .map((p) => p.text ?? "")
          .join("\n")
          .trim()
        if (!text) return
        if (seen.size > 1000) seen.clear()
        seen.add(output.message.id)

        const branch = (await sh`git rev-parse --abbrev-ref HEAD`.quiet().text()).trim()
        const commit = (await sh`git rev-parse --short HEAD`.quiet().text()).trim()
        const model = output.message.model

        append({
          ts: vnIso(),
          tool: "opencode",
          event: "UserPromptSubmit",
          entry_id: `opencode-${output.message.id}`,
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
  } satisfies Plugin
})