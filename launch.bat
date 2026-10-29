@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python scripts\launch.py %*
) else (
  py -3 scripts\launch.py %*
)
if errorlevel 1 (
  echo RepoPilot could not start. See the error above.
  pause
  exit /b 1
)
