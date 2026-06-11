@echo off
setlocal enableextensions
rem ============================================================
rem  START.bat - start button on the SERVER machine
rem  Opens the bot + named tunnel (line.yklogistics.uk)
rem ============================================================
cd /d "%~dp0"

set "CLOUDFLARED=C:\Program Files (x86)\cloudflared\cloudflared.exe"
set "PYTHON=.venv\Scripts\python.exe"
set "TUNNEL_NAME=yk-line"

if not exist ".env" (
    echo [ERROR] .env not found - install incomplete, run INSTALL.bat again
    pause & exit /b 1
)
if not exist "%PYTHON%" (
    echo [ERROR] venv not found - run INSTALL.bat again
    pause & exit /b 1
)
if not exist "%CLOUDFLARED%" goto :no_cf

echo [1/2] starting LINE archiver bot (port 8020) ...
start "LINE Archiver BOT" cmd /k ""%PYTHON%" main.py"

echo [2/2] starting cloudflare named tunnel (%TUNNEL_NAME%) ...
echo === Fixed URL: https://line.yklogistics.uk - no need to touch LINE ===
echo.
"%CLOUDFLARED%" tunnel run %TUNNEL_NAME%
pause
exit /b 0

:no_cf
echo [ERROR] cloudflared not found.
echo Install with: winget install Cloudflare.cloudflared
pause
exit /b 1
