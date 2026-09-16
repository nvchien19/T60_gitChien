@echo off
REM Cross-platform Python launcher for AI log hooks (Windows cmd.exe).
REM Tries py -3 -> python -> python3, runs the given script with all args.
REM Exits 0 silently if no Python is found - hooks must never block the AI tool.

REM Run from the repo root so relative paths in the called script resolve.
REM %~dp0 is scripts\, so its parent is the repo root.
pushd "%~dp0.." >nul 2>nul

REM `where` only proves a file exists, not that it runs. On Windows,
REM python.exe / python3.exe on PATH are often the Microsoft Store App
REM Execution Alias stubs, which exist but exit with an error telling you to
REM install from the Store. So probe each candidate by actually running it.

py -3 --version >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 %*
  set RC=%ERRORLEVEL%
  popd >nul 2>nul
  exit /b %RC%
)

python --version >nul 2>nul
if %ERRORLEVEL%==0 (
  python %*
  set RC=%ERRORLEVEL%
  popd >nul 2>nul
  exit /b %RC%
)

python3 --version >nul 2>nul
if %ERRORLEVEL%==0 (
  python3 %*
  set RC=%ERRORLEVEL%
  popd >nul 2>nul
  exit /b %RC%
)

popd >nul 2>nul
exit /b 0
