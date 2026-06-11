@echo off
chcp 65001 >nul
rem ============================================================
rem  BUILD_USB.bat — รันบนเครื่อง dev (เครื่องนี้)
rem  ประกอบชุดติดตั้งลง flashdrive ให้พร้อมยกไปเครื่อง Server
rem
rem  วิธีใช้:  BUILD_USB.bat E:
rem           (E: = ไดรฟ์ flashdrive ของโอ)
rem ============================================================
setlocal
if "%~1"=="" (
    echo ใส่ไดรฟ์ flashdrive ด้วย เช่น:  BUILD_USB.bat E:
    pause & exit /b 1
)
set "USB=%~1"
set "DEST=%USB%\YK_LINE_INSTALLER"
set "HERE=%~dp0"
set "ARCHIVER=%HERE%.."
set "USERCF=%USERPROFILE%\.cloudflared"

echo.
echo === กำลังประกอบชุดติดตั้งไปที่ %DEST% ===

rem 1) โครงโฟลเดอร์
if not exist "%DEST%\project" mkdir "%DEST%\project"
if not exist "%DEST%\cloudflared_home" mkdir "%DEST%\cloudflared_home"

rem 2) ก็อปโค้ด archiver (ยกเว้น venv/db/media/__pycache__ — สร้างใหม่บน server)
robocopy "%ARCHIVER%" "%DEST%\project" /E ^
  /XD "__pycache__" ".pytest_cache" "tests" "line_media" "installer" ^
  /XF "line_archive.db" >nul

rem 3) ก็อป .env (มี token — นี่คือเหตุที่ flashdrive ต้องเก็บให้ดี)
copy /Y "%ARCHIVER%\.env" "%DEST%\project\.env" >nul

rem 4) ก็อป cloudflare cert + tunnel credentials + config
copy /Y "%USERCF%\cert.pem" "%DEST%\cloudflared_home\" >nul
copy /Y "%USERCF%\*.json" "%DEST%\cloudflared_home\" >nul
copy /Y "%USERCF%\config.yml" "%DEST%\cloudflared_home\" >nul

rem 5) ก็อปตัวติดตั้ง + requirements
copy /Y "%HERE%INSTALL.bat" "%DEST%\" >nul
copy /Y "%HERE%START.bat" "%DEST%\" >nul
copy /Y "%HERE%README.txt" "%DEST%\" >nul
copy /Y "%HERE%requirements-archiver.txt" "%DEST%\project\requirements-archiver.txt" >nul

echo.
echo === เสร็จ! ===
echo flashdrive พร้อมแล้วที่ %DEST%
echo ยกไปเสียบเครื่อง Server แล้วดับเบิลคลิก INSTALL.bat
echo.
pause
