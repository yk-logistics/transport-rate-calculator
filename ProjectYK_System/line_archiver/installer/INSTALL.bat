@echo off
chcp 65001 >nul
rem ============================================================
rem  INSTALL.bat — รันบนเครื่อง SERVER (ดับเบิลคลิกครั้งเดียว)
rem  ติดตั้ง Python(ถ้าไม่มี) + cloudflared + โค้ด + venv + cert
rem ============================================================
setlocal
set "HERE=%~dp0"
set "TARGET=%USERPROFILE%\YK_LINE_ARCHIVER"

echo.
echo ============================================================
echo   ติดตั้ง YK LINE Archiver ลงเครื่องนี้
echo   ปลายทาง: %TARGET%
echo ============================================================
echo.

rem ---- 1) Python ----
echo [1/6] ตรวจ Python ...
where python >nul 2>nul
if errorlevel 1 (
    echo     ไม่พบ Python — กำลังติดตั้งผ่าน winget ...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    echo     *** ปิดหน้าต่างนี้แล้วเปิด INSTALL.bat ใหม่อีกครั้ง (ให้ Windows รู้จัก python) ***
    pause & exit /b 0
) else (
    echo     พบ Python แล้ว
)

rem ---- 2) cloudflared ----
echo [2/6] ตรวจ cloudflared ...
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    echo     พบแล้ว
) else (
    echo     กำลังติดตั้ง cloudflared ...
    winget install -e --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements
)

rem ---- 3) ก็อปโค้ดลงเครื่อง ----
echo [3/6] ก็อปโค้ดไป %TARGET% ...
if not exist "%TARGET%" mkdir "%TARGET%"
robocopy "%HERE%project" "%TARGET%" /E >nul

rem ---- 4) สร้าง venv + ติดตั้ง lib ----
echo [4/6] สร้าง venv + ติดตั้ง lib (ใช้เวลาสักครู่) ...
python -m venv "%TARGET%\.venv"
"%TARGET%\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%TARGET%\.venv\Scripts\python.exe" -m pip install --quiet -r "%TARGET%\requirements-archiver.txt"

rem ---- 5) วาง cloudflare cert/config ----
echo [5/6] ตั้งค่า cloudflare tunnel ...
if not exist "%USERPROFILE%\.cloudflared" mkdir "%USERPROFILE%\.cloudflared"
copy /Y "%HERE%cloudflared_home\*" "%USERPROFILE%\.cloudflared\" >nul

rem ---- 6) สร้าง START.bat ในตำแหน่งจริง ----
echo [6/6] สร้างปุ่มเริ่มทำงาน ...
copy /Y "%HERE%START.bat" "%TARGET%\START.bat" >nul

echo.
echo ============================================================
echo   ติดตั้งเสร็จแล้ว!
echo   เริ่มทำงาน: ไปที่ %TARGET% แล้วดับเบิลคลิก START.bat
echo   (หรือกดปุ่มใดก็ได้ ระบบจะเปิด START.bat ให้เลย)
echo ============================================================
pause
start "" "%TARGET%\START.bat"
