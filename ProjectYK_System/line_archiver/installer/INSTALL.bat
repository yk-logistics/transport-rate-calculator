@echo off
rem ============================================================
rem  INSTALL.bat - run on the SERVER machine (double-click once)
rem  Installs Python(if missing) + cloudflared + code + venv + cert
rem ============================================================
setlocal
set "HERE=%~dp0"
set "TARGET=%USERPROFILE%\YK_LINE_ARCHIVER"

echo.
echo ============================================================
echo   Installing YK LINE Archiver on this machine
echo   Target: %TARGET%
echo ============================================================
echo.

rem ---- 1) Python ----
echo [1/6] Checking Python ...
where python >nul 2>nul
if errorlevel 1 (
    echo     Python not found - installing via winget ...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    echo     *** Close this window and run INSTALL.bat again ***
    echo     *** so Windows can detect python. ***
    pause & exit /b 0
) else (
    echo     Python found
)

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
"%TARGET%\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%TARGET%\.venv\Scripts\python.exe" -m pip install --quiet -r "%TARGET%\requirements-archiver.txt"

rem ---- 5) place cloudflare cert/config ----
echo [5/6] Setting up cloudflare tunnel ...
if not exist "%USERPROFILE%\.cloudflared" mkdir "%USERPROFILE%\.cloudflared"
copy /Y "%HERE%cloudflared_home\*" "%USERPROFILE%\.cloudflared\" >nul

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
