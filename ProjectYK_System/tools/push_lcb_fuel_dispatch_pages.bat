@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0..\.."

echo.
echo === Push รายงาน LCB น้ำมัน ขึ้น GitHub Pages ===
echo.

if not exist "reports\lcb-fuel-dispatch\index.html" (
  echo [ข้าม] ยังไม่มี reports\lcb-fuel-dispatch\index.html
  echo       รัน build_lcb_fuel_dispatch.bat ก่อน แล้วค่อย push
  pause
  exit /b 1
)

git remote get-url origin 2>nul | findstr /i "yk-logistics/transport-rate-calculator" >nul
if errorlevel 1 (
  echo [ข้าม] remote origin ไม่ใช่ yk-logistics/transport-rate-calculator
  pause
  exit /b 1
)

for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set TODAY=%%d

echo จะ commit เฉพาะโฟลเดอร์ GitHub Pages ^(ไม่แตะไฟล์อื่น^)...
git add "reports/lcb-fuel-dispatch/"
git add "ProjectYK_System/TransportRateCalculator/reports/lcb-fuel-dispatch/"

echo.
echo --- staged ---
git diff --cached --name-only
echo.

git diff --cached --quiet
if not errorlevel 1 (
  echo [ข้าม] ไม่มีไฟล์ใหม่ให้ commit ^(อาจ push ไปแล้ว^)
  goto :try_push
)

git commit --trailer "Co-authored-by: Cursor <cursoragent@cursor.com>" -m "docs(pages): LCB fuel dispatch %TODAY%"
if errorlevel 1 (
  echo [ผิดพลาด] commit ไม่สำเร็จ
  pause
  exit /b 1
)

:try_push
echo กำลัง push origin main ...
git push origin main
if errorlevel 1 (
  echo.
  echo [ผิดพลาด] push ไม่สำเร็จ — มักเป็นเรื่อง login / token
  echo.
  echo ทำใน GitHub Desktop:
  echo   1. File -^> Add Local Repository -^> โฟลเดอร์ Project YK
  echo   2. ตรวจว่า remote คือ yk-logistics/transport-rate-calculator
  echo   3. เลือก branch main — ติ๊กเฉพาะ reports/lcb-fuel-dispatch และ README ใน TransportRateCalculator
  echo   4. Summary: docs(pages): LCB fuel dispatch แล้วกด Commit to main
  echo   5. กด Push origin
  echo.
  pause
  exit /b 1
)

echo.
echo เสร็จ — เปิดลิงก์ ^(รอ 1–2 นาทีหลัง push^):
echo   https://yk-logistics.github.io/transport-rate-calculator/reports/lcb-fuel-dispatch/
echo.
pause