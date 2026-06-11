@echo off
rem ============================================================
rem  start_all.bat - one click: bot + cloudflare tunnel
rem  Just double-click this single file.
rem ============================================================
cd /d "%~dp0"

set "CLOUDFLARED=C:\Program Files (x86)\cloudflared\cloudflared.exe"
set "PYTHON=..\app\.venv\Scripts\python.exe"

rem ---- named tunnel name (empty = quick tunnel, URL changes each time) ----
rem  after named tunnel is set up, put its name here, e.g.: set "TUNNEL_NAME=yk-line"
set "TUNNEL_NAME=yk-line"

rem ---- checks ----
if not exist ".env" (
    echo [ERROR] .env not found - see SETUP_CHECKLIST.md
    pause
    exit /b 1
)
if not exist "%CLOUDFLARED%" (
    echo [ERROR] cloudflared not found at %CLOUDFLARED%
    echo Install with: winget install Cloudflare.cloudflared
    pause
    exit /b 1
)

rem ---- 1) start bot in a new window ----
echo [1/2] starting LINE archiver bot (port 8020) ...
start "LINE Archiver BOT" cmd /k ""%PYTHON%" main.py"

rem ---- 2) start tunnel in this window ----
echo [2/2] starting cloudflare tunnel ...
echo.
if defined TUNNEL_NAME (
    echo === NAMED TUNNEL: %TUNNEL_NAME% - fixed URL, no need to touch LINE ===
    echo.
    "%CLOUDFLARED%" tunnel run %TUNNEL_NAME%
) else (
    echo ============================================================
    echo  QUICK TUNNEL - find the line https://xxxx.trycloudflare.com
    echo  below, then put it in LINE Developers ^> Webhook URL
    echo  with /line/webhook appended, then click Verify
    echo ============================================================
    echo.
    "%CLOUDFLARED%" tunnel --url http://127.0.0.1:8020
)

pause
