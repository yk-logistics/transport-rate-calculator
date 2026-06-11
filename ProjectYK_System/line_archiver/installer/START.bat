@echo off
chcp 65001 >nul
rem ============================================================
rem  START.bat — ปุ่มเริ่มทำงานบนเครื่อง SERVER
rem  เปิดบอท + named tunnel (line.yklogistics.uk)
rem ============================================================
cd /d "%~dp0"

set "CLOUDFLARED=C:\Program Files (x86)\cloudflared\cloudflared.exe"
set "PYTHON=.venv\Scripts\python.exe"
set "TUNNEL_NAME=yk-line"

if not exist ".env" (
    echo [ERROR] ไม่พบ .env — ติดตั้งไม่สมบูรณ์ ลองรัน INSTALL.bat ใหม่
    pause & exit /b 1
)
if not exist "%PYTHON%" (
    echo [ERROR] ไม่พบ venv — ลองรัน INSTALL.bat ใหม่
    pause & exit /b 1
)

echo [1/2] starting LINE archiver bot (port 8020) ...
start "LINE Archiver BOT" cmd /k ""%PYTHON%" main.py"

echo [2/2] starting cloudflare named tunnel (%TUNNEL_NAME%) ...
echo === URL คงที่: https://line.yklogistics.uk — ไม่ต้องแตะ LINE ===
echo.
"%CLOUDFLARED%" tunnel run %TUNNEL_NAME%
pause
