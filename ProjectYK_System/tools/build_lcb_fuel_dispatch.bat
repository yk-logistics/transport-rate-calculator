@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0..\.."



set PLAN=%~1

set FUEL=%~2

set DIESEL=42.20



echo.

echo === สร้างแผนเติมน้ำมัน LCB จากแผน LINE + GPS ===

echo.



if "%PLAN%"=="" (

  echo ลากไฟล์แผน .txt มาวางบนหน้าต่างนี้ แล้วกด Enter

  echo หรือพิมพ์ path เต็ม เช่น %%USERPROFILE%%\Downloads\21.05.26.txt

  set /p PLAN=แผน .txt: 

  set PLAN=!PLAN:"=!

)

if "%PLAN%"=="" (

  echo [ยกเลิก] ไม่ได้ระบุไฟล์แผน

  pause

  exit /b 1

)

if not exist "%PLAN%" (

  echo [ผิดพลาด] ไม่พบไฟล์: %PLAN%

  pause

  exit /b 1

)



set FUEL_ARG=

if not "%FUEL%"=="" (

  echo %FUEL% | findstr /i "\.xlsx" >nul && (

    set FUEL_ARG=--fuel-xlsx "%FUEL%"

    echo ใช้ไฟล์น้ำมัน: %FUEL%

  ) || (

    set FUEL_ARG=--fuel-csv "%FUEL%"

    echo ใช้ไฟล์น้ำมัน: %FUEL%

  )

) else (

  for /f "delims=" %%F in ('dir /b /o-d "%USERPROFILE%\Downloads\*Fuel_Level*LCB*.xlsx" 2^>nul') do (

    set FUEL_ARG=--fuel-xlsx "%USERPROFILE%\Downloads\%%F"

    echo พบไฟล์ GPS ล่าสุดใน Downloads: %%F

    goto :fuel_done

  )

  if exist "ProjectYK_System\reports\fuel_level_latest_LCB_2026-05-20.csv" (

    set FUEL_ARG=--fuel-csv "ProjectYK_System\reports\fuel_level_latest_LCB_2026-05-20.csv"

    echo ใช้ CSV ใน reports\fuel_level_latest_LCB_2026-05-20.csv

  ) else (

    echo [คำเตือน] ไม่พบ *Fuel_Level*LCB*.xlsx ใน Downloads — ส่ง path เป็นพารามิเตอร์ที่ 2

  )

)

:fuel_done



set ADD_FUEL=--add-fuel 72-0420=30 --add-fuel 71-6803=20



echo แผน: %PLAN%

echo ราคาดีเซล: %DIESEL% บาท/ล. ^(เติมคืนนี้ 0420 +30 ล., 6803 +20 ล.^)

echo.



python ProjectYK_System\tools\build_lcb_fuel_dispatch_from_plan.py "%PLAN%" %FUEL_ARG% %ADD_FUEL% --diesel-price %DIESEL%

if errorlevel 1 (

  echo.

  echo [ผิดพลาด] สคริปต์ล้มเหลว — ดูข้อความด้านบน

  pause

  exit /b 1

)



echo.

echo เปิด HTML ในเบราว์เซอร์...

start "" "ProjectYK_System\docs\print\lcb_fuel_dispatch_plan.html"

echo.

echo ลิงก์สาธารณะ (หลัง git add + commit + push ขึ้น yk-logistics/transport-rate-calculator):

echo   https://yk-logistics.github.io/transport-rate-calculator/reports/lcb-fuel-dispatch/

echo ทดสอบก่อน push: http://localhost:8011/ops/lcb-fuel-dispatch

echo.

echo เสร็จ — ปิดหน้าต่างนี้ได้

echo.
set /p DO_PUSH=Push ขึ้น GitHub Pages? (Y/N) [N]: 
if /i "!DO_PUSH!"=="Y" (
  call "%~dp0push_lcb_fuel_dispatch_pages.bat"
) else (
  echo ข้าม push — ดับเบิลคลิก ProjectYK_System\tools\push_lcb_fuel_dispatch_pages.bat เมื่อพร้อม
)
pause
