#!/bin/sh
# Cross-platform Python launcher for AI log hooks.
#
# POSIX sh on purpose, not bash: on Windows a bare `bash` on PATH resolves to
# C:\Windows\System32\bash.exe (the WSL launcher), which aborts with "Please
# enable the Virtual Machine Platform" on machines without WSL2. Keeping this
# script free of bashisms means whatever shell a hook runner picks can execute
# it — and callers no longer need to name a shell at all.
#
# Tries python3 → python → py -3 on PATH; on Windows, falls back to common
# Python install locations because a hook's shell may get a stripped PATH that
# omits the Windows Python directory.
#
# Usage: scripts/_pyrun.sh <script> [args...]
#
# Exits 0 silently if no Python is found — hooks must never block the AI tool.
set -u

# Run from the repo root so relative paths in the called script resolve, and so
# `git` calls inside it see the right repository.
if command -v git >/dev/null 2>&1; then
  ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null) || ROOT=""
  [ -n "$ROOT" ] && cd "$ROOT" 2>/dev/null || true
fi

# On Windows, `python3`/`python` on PATH may resolve to the Microsoft Store's
# App Execution Alias stub, which exists as a file but errors when run instead
# of launching Python. `command -v` can't detect that, so probe by actually
# running --version.
works() { "$@" --version >/dev/null 2>&1; }

if works python3; then
  PY=python3
elif works python; then
  PY=python
elif works py -3; then
  PY="py -3"
else
  # PATH lookup failed — probe standard Windows install locations.
  # `[ -e ]` guards each match so an unmatched glob (which sh leaves as a
  # literal containing `*`) is skipped; that is what bash's nullglob did.
  PY=""
  for cand in \
    /c/Users/*/AppData/Local/Programs/Python/Python*/python.exe \
    "/c/Program Files/Python"*/python.exe \
    "/c/Program Files (x86)/Python"*/python.exe \
    /c/Python*/python.exe; do
    [ -e "$cand" ] || continue
    if [ -x "$cand" ] && works "$cand"; then PY="$cand"; break; fi
  done
  [ -n "$PY" ] || exit 0
fi

# shellcheck disable=SC2086
exec $PY "$@"
