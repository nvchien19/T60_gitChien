# Install git pre-push hook for AI log submission (Windows PowerShell).
# Run once after cloning: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1

$ErrorActionPreference = 'Stop'

$HookFile = '.git/hooks/pre-push'

# A bare `bash` in the hook resolves to C:\Windows\System32\bash.exe (the WSL
# launcher) on most Windows boxes. Without WSL2 installed that aborts with
# "Please enable the Virtual Machine Platform" and the push fails. Find the Git
# Bash that ships with Git for Windows and bake its absolute path into the hook.
$BashBin = $null
$Candidates = @()

# Prefer the bash sitting next to the git.exe actually in use.
$GitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($GitCmd) {
    $GitRoot = Split-Path (Split-Path $GitCmd.Source -Parent) -Parent
    $Candidates += (Join-Path $GitRoot 'bin\bash.exe')
    $Candidates += (Join-Path $GitRoot 'usr\bin\bash.exe')
}
$Candidates += 'C:\Program Files\Git\bin\bash.exe'
$Candidates += 'C:\Program Files\Git\usr\bin\bash.exe'
$Candidates += 'C:\Program Files (x86)\Git\bin\bash.exe'

foreach ($c in $Candidates) {
    if ($c -and (Test-Path $c)) { $BashBin = $c; break }
}

if (-not $BashBin) {
    Write-Warning "[ai-log] Git Bash not found. Install Git for Windows, then re-run this script."
    exit 1
}

# Forward slashes so Git's hook runner can exec the path directly.
$BashBinPosix = $BashBin -replace '\\', '/'

# Git on Windows runs hooks through its own shell, so the hook body is sh.
$HookBody = @"
#!/bin/sh
# Pre-push: sweep recent Antigravity / Gemini prompts, then submit AI logs.
# BASH_BIN is an absolute path resolved at install time so this never falls
# through to the WSL bash stub on Windows.
BASH_BIN="$BashBinPosix"
[ -x "`$BASH_BIN" ] || exit 0  # No usable bash: never block the push.

# Run from the repo root so the relative script paths below always resolve.
cd "`$(git rev-parse --show-toplevel)" || exit 0

"`$BASH_BIN" scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
"`$BASH_BIN" scripts/_pyrun.sh scripts/submit_log.py || true
exit 0
"@

# LF endings and no BOM: Git's sh chokes on CRLF and on a UTF-8 BOM shebang.
$HookBody = $HookBody -replace "`r`n", "`n"
[System.IO.File]::WriteAllText(
    (Join-Path (Get-Location) $HookFile),
    $HookBody,
    (New-Object System.Text.UTF8Encoding $false)
)

Write-Host "[ai-log] Git pre-push hook installed (bash: $BashBin)."

if (-not (Test-Path .ai-log)) { New-Item -ItemType Directory -Path .ai-log | Out-Null }
if (-not (Test-Path .ai-log/.gitkeep)) { New-Item -ItemType File -Path .ai-log/.gitkeep | Out-Null }

Write-Host "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
