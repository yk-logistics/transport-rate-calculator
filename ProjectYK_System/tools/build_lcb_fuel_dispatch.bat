@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0..\.."

set "PLAN=%~1"
set "FUEL=%~2"
set "DIESEL=42.20"

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

set "FUEL_ARG="
if not "%FUEL%"=="" (
  echo %FUEL% | findstr /i "\.xlsx" >nul && (
    set "FUEL_ARG=--fuel-xlsx "%FUEL%""
    echo Fuel file: %FUEL%
  ) || (
    set "FUEL_ARG=--fuel-csv "%FUEL%""
    echo Fuel file: %FUEL%
  )
) else (
  for /f "delims=" %%F in ('dir /b /o-d "%USERPROFILE%\Downloads\*Fuel_Level*LCB*.xlsx" 2^>nul') do (
    set "FUEL_ARG=--fuel-xlsx "%USERPROFILE%\Downloads\%%F""
    echo Latest GPS xlsx in Downloads: %%F
    goto :fuel_done
  )
  if exist "ProjectYK_System\reports\fuel_level_latest_LCB_2026-05-20.csv" (
    set "FUEL_ARG=--fuel-csv "ProjectYK_System\reports\fuel_level_latest_LCB_2026-05-20.csv""
    echo Using CSV: ProjectYK_System\reports\fuel_level_latest_LCB_2026-05-20.csv
  ) else (
    echo [WARN] No *Fuel_Level*LCB*.xlsx in Downloads - pass fuel path as 2nd argument.
  )
)
:fuel_done

set "ADD_FUEL=--add-fuel 72-0420=30 --add-fuel 71-6803=20"

echo Plan: %PLAN%
echo Diesel price: %DIESEL% THB/L  (extra fuel: 0420 +30L, 6803 +20L)
echo.

python ProjectYK_System\tools\build_lcb_fuel_dispatch_from_plan.py "%PLAN%" %FUEL_ARG% %ADD_FUEL% --diesel-price %DIESEL%
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

set /p "DO_PUSH=Push to GitHub Pages now? (Y/N) [N]: "
if /i "!DO_PUSH!"=="Y" (
  call "%~dp0push_lcb_fuel_dispatch_pages.bat"
) else (
  echo Skipped push. Run: ProjectYK_System\tools\push_lcb_fuel_dispatch_pages.bat
)
pause
