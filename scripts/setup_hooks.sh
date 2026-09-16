#!/usr/bin/env bash
# Install git pre-push hook for AI log submission (POSIX / Git Bash).
# Run once after cloning: bash scripts/setup_hooks.sh
set -e

HOOK_FILE=".git/hooks/pre-push"

# On Windows, a bare `bash` in the hook resolves to C:\Windows\System32\bash.exe
# (the WSL launcher), which aborts with "Please enable the Virtual Machine
# Platform" on machines without WSL2 and kills the push. Resolve the bash that
# is running this installer instead and bake its absolute path into the hook.
BASH_BIN="$(command -v bash)"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    # Translate /c/... to C:/... so Git's hook runner can exec it directly.
    if command -v cygpath >/dev/null 2>&1; then
      BASH_BIN="$(cygpath -m "$BASH_BIN")"
    fi
    ;;
esac

cat > "$HOOK_FILE" <<EOF
#!/bin/sh
# Pre-push: sweep recent Antigravity / Gemini prompts, then submit AI logs.
# BASH_BIN is an absolute path resolved at install time so this never falls
# through to the WSL bash stub on Windows.
BASH_BIN="$BASH_BIN"
[ -x "\$BASH_BIN" ] || exit 0  # No usable bash: never block the push.

# Run from the repo root so the relative script paths below always resolve.
cd "\$(git rev-parse --show-toplevel)" || exit 0

"\$BASH_BIN" scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
"\$BASH_BIN" scripts/_pyrun.sh scripts/submit_log.py || true
exit 0  # Never block push, even if either step fails
EOF

chmod +x "$HOOK_FILE"
chmod +x scripts/_pyrun.sh 2>/dev/null || true
echo "[ai-log] Git pre-push hook installed (bash: $BASH_BIN)."

mkdir -p .ai-log
touch .ai-log/.gitkeep

echo "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
