@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
REM Test: double-click -> prompts plan then fuel; Enter on both -> auto *05.26*.txt + *Fuel_Level*LCB*.xlsx
REM Test: drag plan.txt only -> %1=plan, fuel prompt still shown
REM Test: drag plan.txt + fuel.xlsx onto .bat -> %1 and %2 set, no prompts

cd /d "%~dp0..\.."

set "PLAN=%~1"
set "FUEL=%~2"
set "DIESEL=42.20"

REM ลากไฟล์ .xlsx มาวางบน bat ตัวเดียว -> ใช้เป็น GPS
if /i "%~x1"==".xlsx" (
  set "FUEL=%~1"
  set "PLAN="
)

echo.
echo === LCB fuel dispatch: LINE plan .txt + GPS ===
echo.

if "%PLAN%"=="" (
  echo Paste full path to plan .txt then press Enter.
  echo Or drag the .txt file onto this window and press Enter.
  echo Example: %USERPROFILE%\Downloads\21.05.26.txt
  echo Press Enter alone to use latest *05.26*.txt in Downloads.
  set /p "PLAN=Plan .txt path: "
  set "PLAN=!PLAN:"=!"
)

if "%PLAN%"=="" (
  set "PLAN="
  for /f "delims=" %%F in ('dir /b /o-d "%CD%\ProjectYK_System\reports\gps_inbox\*.txt" 2^>nul') do (
    set "PLAN=%CD%\ProjectYK_System\reports\gps_inbox\%%F"
    echo Auto-selected plan from gps_inbox: %%F
    goto :plan_done
  )
  for /f "delims=" %%F in ('dir /b /o-d "%USERPROFILE%\Downloads\*05.26*.txt" 2^>nul') do (
    set "PLAN=%USERPROFILE%\Downloads\%%F"
    echo Using default plan: !PLAN!
    goto :plan_done
  )
  for /f "delims=" %%F in ('dir /b /o-d "%USERPROFILE%\Downloads\*.txt" 2^>nul') do (
    set "PLAN=%USERPROFILE%\Downloads\%%F"
    echo Using latest .txt in Downloads: !PLAN!
    goto :plan_done
  )
)
:plan_done

if "%PLAN%"=="" (
  echo [ERROR] No plan file specified.
  pause
  exit /b 1
)

if not exist "%PLAN%" (
  echo [ERROR] File not found: %PLAN%
  pause
  exit /b 1
)

if "%FUEL%"=="" (
  echo.
  echo GPS fuel file (.xlsx or .csv)
  echo RECOMMENDED: Press Enter alone = newest .xlsx in gps_inbox (avoids Thai filename paste bugs in cmd).
  echo Or drag .xlsx onto this .bat file (two files: plan.txt then fuel.xlsx).
  set /p "FUEL=GPS fuel file path (Enter=auto): "
  set "FUEL=!FUEL:"=!"
)

if not "%FUEL%"=="" if not exist "%FUEL%" (
  echo.
  echo [WARN] File not found - Thai/special chars often break when pasted in cmd.
  echo        Will auto-pick newest .xlsx in gps_inbox instead.
  echo        Broken path was: %FUEL%
  set "FUEL="
)

if "%FUEL%"=="" (
  for /f "delims=" %%F in ('dir /b /o-d "%CD%\ProjectYK_System\reports\gps_inbox\*.xlsx" 2^>nul') do (
    set "FUEL=%CD%\ProjectYK_System\reports\gps_inbox\%%F"
    echo Auto-selected from gps_inbox: %%F
    goto :fuel_resolved
  )
  for /f "delims=" %%F in ('dir /b /o-d "%USERPROFILE%\Downloads\*Fuel_Level*LCB*.xlsx" 2^>nul') do (
    set "FUEL=%USERPROFILE%\Downloads\%%F"
    echo Auto-selected GPS xlsx: %%F
    goto :fuel_resolved
  )
  for /f "delims=" %%F in ('dir /b /o-d "%USERPROFILE%\Downloads\*LCB*Fuel*.xlsx" 2^>nul') do (
    set "FUEL=%USERPROFILE%\Downloads\%%F"
    echo Auto-selected GPS xlsx: %%F
    goto :fuel_resolved
  )
  for /f "delims=" %%F in ('dir /b /o-d "%USERPROFILE%\Downloads\*tracking_report*.xlsx" 2^>nul') do (
    set "FUEL=%USERPROFILE%\Downloads\%%F"
    echo Auto-selected GPS xlsx: %%F
    goto :fuel_resolved
  )
)

if "%FUEL%"=="" (
  echo [ERROR] No GPS .xlsx in ProjectYK_System\reports\gps_inbox
  echo         Export Wialon Fuel Level LCB and copy .xlsx into that folder.
  pause
  exit /b 1
)
if not exist "%FUEL%" (
  echo [ERROR] Fuel file not found: %FUEL%
  pause
  exit /b 1
)
echo Using fuel file: %FUEL%
:fuel_resolved

set "BUDGET_LOW=5000"
set "BUDGET_HIGH=10000"
set "ADD_FUEL=--add-fuel 72-0420=30 --add-fuel 71-6803=20 --add-fuel 71-6804=30"

echo Plan: %PLAN%
echo Diesel price: %DIESEL% THB/L  (เติมแล้ว: 0420+30, 6803+20, 6804+30 ล.)
echo Budget cap: %BUDGET_LOW% - %BUDGET_HIGH% baht
echo Pump PDF: auto from ProjectYK_System\reports\pump_inbox\ (วางรายงานปั๊มเช้า)
echo.

if "%FUEL%"=="" (
  python ProjectYK_System\tools\build_lcb_fuel_dispatch_from_plan.py "%PLAN%" %ADD_FUEL% --diesel-price %DIESEL% --budget-low %BUDGET_LOW% --budget-high %BUDGET_HIGH%
) else (
  python ProjectYK_System\tools\build_lcb_fuel_dispatch_from_plan.py "%PLAN%" "%FUEL%" %ADD_FUEL% --diesel-price %DIESEL% --budget-low %BUDGET_LOW% --budget-high %BUDGET_HIGH%
)
if errorlevel 1 (
  echo.
  echo [ERROR] Build failed - see messages above.
  pause
  exit /b 1
)

set "HTML_PRINT=%CD%\ProjectYK_System\docs\print\lcb_fuel_dispatch_plan.html"
set "HTML_PAGES=%CD%\reports\lcb-fuel-dispatch\index.html"
set "HTML_PAGES2=%CD%\ProjectYK_System\TransportRateCalculator\reports\lcb-fuel-dispatch\index.html"

echo.
echo Done. Open these files:
echo   Print HTML:  %HTML_PRINT%
echo   GitHub Pages source:  %HTML_PAGES%
echo   TransportRateCalculator copy:  %HTML_PAGES2%
echo.
echo Public URL after push:
echo   https://yk-logistics.github.io/transport-rate-calculator/reports/lcb-fuel-dispatch/
echo Local test: http://localhost:8011/ops/lcb-fuel-dispatch
echo.

start "" "%HTML_PRINT%"

echo.
echo Pushing to GitHub Pages...
call "%~dp0push_lcb_fuel_dispatch_pages.bat"
pause
