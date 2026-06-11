@echo off
rem ============================================================
rem  LINE Archiver — ปุ่มเดียวเปิดทั้งบอท + cloudflare tunnel
rem  ดับเบิลคลิกไฟล์นี้ไฟล์เดียวพอ
rem ============================================================
cd /d "%~dp0"

set "CLOUDFLARED=C:\Program Files (x86)\cloudflared\cloudflared.exe"
set "PYTHON=..\app\.venv\Scripts\python.exe"

rem ---- ชื่อ named tunnel (เว้นว่าง = ใช้ quick tunnel URL เปลี่ยนทุกครั้ง) ----
rem  พอตั้ง named tunnel เสร็จ ให้ใส่ชื่อ tunnel ตรงนี้ เช่น: set "TUNNEL_NAME=yk-line"
set "TUNNEL_NAME=yk-line"

rem ---- ตรวจของจำเป็น ----
if not exist ".env" (
    echo [ERROR] ยังไม่มี .env — ดู SETUP_CHECKLIST.md
    pause
    exit /b 1
)
if not exist "%CLOUDFLARED%" (
    echo [ERROR] ไม่พบ cloudflared ที่ %CLOUDFLARED%
    echo ติดตั้งด้วย: winget install Cloudflare.cloudflared
    pause
    exit /b 1
)

rem ---- 1) เปิดบอทในหน้าต่างใหม่ ----
echo [1/2] starting LINE archiver bot (port 8020) ...
start "LINE Archiver BOT" cmd /k ""%PYTHON%" main.py"

rem ---- 2) เปิด tunnel ในหน้าต่างนี้ ----
echo [2/2] starting cloudflare tunnel ...
echo.
if defined TUNNEL_NAME (
    echo === NAMED TUNNEL: %TUNNEL_NAME% — URL คงที่ ไม่ต้องแก้ LINE ===
    echo.
    "%CLOUDFLARED%" tunnel run %TUNNEL_NAME%
) else (
    echo ============================================================
    echo  QUICK TUNNEL — หา URL บรรทัด https://xxxx.trycloudflare.com
    echo  ด้านล่าง แล้วเอาไปใส่ LINE Developers ^> Webhook URL
    echo  ต่อท้ายด้วย /line/webhook แล้วกด Verify
    echo ============================================================
    echo.
    "%CLOUDFLARED%" tunnel --url http://127.0.0.1:8020
)

pause
