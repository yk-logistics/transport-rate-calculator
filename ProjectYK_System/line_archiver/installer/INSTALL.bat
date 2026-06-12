@echo off
setlocal enableextensions
rem ============================================================
rem  INSTALL.bat - run on the SERVER machine (double-click once)
rem  Installs cloudflared + code + venv + cert
rem  REQUIRES Python 3.12 already installed (from python.org, with
rem  "Add python.exe to PATH" ticked). See README.txt.
rem ============================================================
set "HERE=%~dp0"
set "TARGET=%USERPROFILE%\YK_LINE_ARCHIVER"

echo.
echo ============================================================
echo   Installing YK LINE Archiver on this machine
echo   Target: %TARGET%
echo ============================================================
echo.

rem ---- 1) Python (run it for real, not just "where") ----
echo [1/6] Checking Python ...
python --version >nul 2>nul
if errorlevel 1 goto :no_python
rem detect the Microsoft Store stub (it exits 0 but does nothing useful)
for /f "delims=" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo     Found: %PYVER%

rem ---- 2) cloudflared ----
echo [2/6] Checking cloudflared ...
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    echo     Found
) else (
    echo     Installing cloudflared ...
    winget install -e --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements
)

rem ---- 3) copy code to machine ----
echo [3/6] Copying code to %TARGET% ...
if not exist "%TARGET%" mkdir "%TARGET%"
robocopy "%HERE%project" "%TARGET%" /E >nul

rem ---- 4) create venv + install libs ----
echo [4/6] Creating venv + installing libs (please wait) ...
python -m venv "%TARGET%\.venv"
if not exist "%TARGET%\.venv\Scripts\python.exe" goto :venv_failed
"%TARGET%\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%TARGET%\.venv\Scripts\python.exe" -m pip install --quiet -r "%TARGET%\requirements-archiver.txt"
if errorlevel 1 goto :pip_failed

rem ---- 5) place cloudflare cert/creds, then WRITE config.yml for THIS user ----
rem    (don't copy the dev machine's config.yml - its paths are hardcoded to
rem     another username. Generate it fresh from %USERPROFILE% here.)
echo [5/6] Setting up cloudflare tunnel ...
if not exist "%USERPROFILE%\.cloudflared" mkdir "%USERPROFILE%\.cloudflared"
copy /Y "%HERE%cloudflared_home\cert.pem" "%USERPROFILE%\.cloudflared\" >nul
copy /Y "%HERE%cloudflared_home\*.json" "%USERPROFILE%\.cloudflared\" >nul
set "TID=741eef82-38c6-4243-be04-a4b4e287a303"
(
echo tunnel: yk-line
echo credentials-file: %USERPROFILE%\.cloudflared\%TID%.json
echo.
echo ingress:
echo   - hostname: line.yklogistics.uk
echo     service: http://127.0.0.1:8020
echo   - service: http_status:404
) > "%USERPROFILE%\.cloudflared\config.yml"

rem ---- 6) put START.bat in the real folder ----
echo [6/6] Creating start button ...
copy /Y "%HERE%START.bat" "%TARGET%\START.bat" >nul

echo.
echo ============================================================
echo   Install complete!
echo   To start: go to %TARGET% and double-click START.bat
echo   (launching it now...)
echo ============================================================
pause
start "" "%TARGET%\START.bat"
exit /b 0

:no_python
echo.
echo [ERROR] Python not found (or it's the Microsoft Store stub).
echo   1) Install Python 3.12 from https://www.python.org/downloads
echo      -- TICK "Add python.exe to PATH" during setup.
echo   2) Settings -^> "Manage app execution aliases" -^> turn OFF
echo      python.exe and python3.exe.
echo   3) Run INSTALL.bat again.
pause
exit /b 1

:venv_failed
echo.
echo [ERROR] venv was not created. Python is likely the Store stub.
echo   Settings -^> "Manage app execution aliases" -^> turn OFF
echo   python.exe / python3.exe, then re-run INSTALL.bat.
pause
exit /b 1

:pip_failed
echo.
echo [ERROR] pip install failed (network? proxy?). See messages above.
pause
exit /b 1
