@echo off
rem ============================================================
rem  BUILD_USB.bat - run on the DEV machine (this one)
rem  Assembles the installer onto a flashdrive for the Server.
rem
rem  Usage:  BUILD_USB.bat E:
rem          (E: = your flashdrive letter)
rem ============================================================
setlocal
if "%~1"=="" (
    echo Please pass the flashdrive letter, e.g.:  BUILD_USB.bat E:
    pause & exit /b 1
)
set "USB=%~1"
set "DEST=%USB%\YK_LINE_INSTALLER"
set "HERE=%~dp0"
set "ARCHIVER=%HERE%.."
set "USERCF=%USERPROFILE%\.cloudflared"

echo.
echo === Building installer to %DEST% ===

rem 1) folder structure
if not exist "%DEST%\project" mkdir "%DEST%\project"
if not exist "%DEST%\cloudflared_home" mkdir "%DEST%\cloudflared_home"

rem 2) copy archiver code (exclude venv/db/media/cache/tests - rebuilt on server)
robocopy "%ARCHIVER%" "%DEST%\project" /E /XD "__pycache__" ".pytest_cache" "tests" "line_media" "installer" /XF "line_archive.db" >nul

rem 3) copy .env (contains tokens - this is why the flashdrive must be kept safe)
copy /Y "%ARCHIVER%\.env" "%DEST%\project\.env" >nul

rem 4) copy cloudflare cert + tunnel credentials + config
copy /Y "%USERCF%\cert.pem" "%DEST%\cloudflared_home\" >nul
copy /Y "%USERCF%\*.json" "%DEST%\cloudflared_home\" >nul
copy /Y "%USERCF%\config.yml" "%DEST%\cloudflared_home\" >nul

rem 5) copy installer scripts + requirements
copy /Y "%HERE%INSTALL.bat" "%DEST%\" >nul
copy /Y "%HERE%START.bat" "%DEST%\" >nul
copy /Y "%HERE%README.txt" "%DEST%\" >nul
copy /Y "%HERE%requirements-archiver.txt" "%DEST%\project\requirements-archiver.txt" >nul

echo.
echo === DONE ===
echo Flashdrive ready at %DEST%
echo Take it to the Server and double-click INSTALL.bat
echo.
pause
