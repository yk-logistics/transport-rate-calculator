@echo off
setlocal
REM UTF-8 console — ถ้าไม่ตั้ง ภาษาไทยจาก Python จะกลายเป็น ??? / เพี้ยนใน cmd เดิม
chcp 65001 >nul 2>nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

cd /d "%~dp0"

echo === Project YK - One Platform ===
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Please install Python 3.10+ from https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [SETUP] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 ( echo Failed to create venv & pause & exit /b 1 )
)

echo [SETUP] Installing / updating packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 ( echo Failed to install packages & pause & exit /b 1 )

echo.
echo ================================================
echo   Project YK starting...
echo   - Python will auto-select a free port (default 8010)
echo   - Bind 0.0.0.0 : เครื่องอื่นใน LAN เข้าได้ (ใช้ IP เครื่องนี้แทน 127.0.0.1)
echo   - ถ้าต้องการเปิดแค่เครื่องนี้: set YK_BIND_HOST=127.0.0.1 แล้วรันใหม่
echo   - Browser will open automatically
echo   - Press CTRL+C to stop
echo ================================================

REM main.py handles port detection AND opens the browser.
".venv\Scripts\python.exe" main.py

pause
