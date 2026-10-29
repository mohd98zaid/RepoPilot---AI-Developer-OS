@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run launch.bat first to prepare the Python environment.
  exit /b 1
)
.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe scripts\build_desktop.py
if errorlevel 1 pause
