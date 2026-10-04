---
name: p060-frontend
description: Build and fix the P-060 Vietnamese medication interface in interface/fontend using its existing Next.js, React, TypeScript and Tailwind stack. Use for UI, client state, accessibility and frontend API integration in this folder.
---

# P-060 frontend

Work from interface/fontend; the spelling fontend is the actual directory name. Read its AGENTS.md and package.json first. For Next.js changes, consult the relevant installed guides in node_modules/next/dist/docs/ as required by AGENTS.md; if unavailable, report the limitation and consult official documentation for the installed version.

## Project conventions

- Inspect app/page.tsx, the affected components, app/globals.css and app/theme before choosing layout or styling. Reuse components/ui/button.tsx, existing Base UI/shadcn patterns, lucide-react and lib/utils.ts where appropriate.
- Keep Vietnamese labels and the existing light/dark theme coherent. Provide usable keyboard focus, accessible labels and layouts for mobile and desktop.
- Keep API calls and response mapping consistent with lib/api.ts and the existing /api/v1 integration. Check backend schemas and routes when changing a contract; preserve loading, empty, timeout and failure states.
- Respect Next.js server/client boundaries; add client directives only where interactive browser behavior requires them. Keep service credentials on the backend.
- Preserve citations, unknown/no-record states, translation indicators and severity from backend evidence. Do not turn missing records into an assurance of safety or invent a severity.

## Verification

Use the package manager declared in package.json, currently pnpm, and avoid changing competing lockfiles incidentally. Check the affected behavior and run pnpm exec tsc --noEmit or pnpm build when appropriate to the change. For prescription-normalization changes, inspect and run the existing lib/prescription-normalize.test.cjs test with Node. For visual changes, verify relevant viewport sizes and themes when a browser is available. Report checks performed and any unavailable dependencies.
