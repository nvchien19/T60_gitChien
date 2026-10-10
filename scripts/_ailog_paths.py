"""Shared path resolution for the AI log scripts.

Every log script writes to `.ai-log/`. Resolving that as a bare relative path
makes it depend on the current working directory, and hooks do not reliably get
the repo root as their CWD — an editor may spawn them from the open file's
folder, and `git push` from a subdirectory does the same. That would scatter
half-written logs into subfolders (or into nothing) and quietly lose entries.

`log_dir()` anchors the path to the repo root instead, which is stable no matter
who invokes the script or from where.

Resolution order:
  1. $AI_LOG_DIR, if set (absolute, or relative to the repo root)
  2. <repo root>/.ai-log

The repo root comes from `git rev-parse --show-toplevel`; if git is unavailable
(no git on PATH, or not a checkout), it falls back to the parent of scripts/,
which is where these files live.
"""
import os
import subprocess
from pathlib import Path


def repo_root() -> Path:
    """Absolute path to the repo root. Never raises."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            # git prints UTF-8. Without this, text=True decodes with the Windows
            # code page (cp1252), so a path containing non-ASCII characters
            # (e.g. Vietnamese folder names) comes back as mojibake that does not
            # exist on disk, and every log script silently drops its entries.
            encoding="utf-8",
            errors="replace",
            timeout=10,
            cwd=str(Path(__file__).resolve().parent),
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except Exception:
        pass
    # scripts/_ailog_paths.py → scripts/ → repo root
    return Path(__file__).resolve().parent.parent


def log_dir() -> Path:
    """Absolute path to the AI log directory, honouring $AI_LOG_DIR."""
    override = os.environ.get("AI_LOG_DIR", "").strip()
    if override:
        p = Path(override)
        return p.resolve() if p.is_absolute() else (repo_root() / p).resolve()
    return repo_root() / ".ai-log"
