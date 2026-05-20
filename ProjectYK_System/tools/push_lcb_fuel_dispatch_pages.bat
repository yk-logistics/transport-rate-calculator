@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0..\.."

echo.
echo === Push LCB fuel dispatch report to GitHub Pages ===
echo.

if not exist "reports\lcb-fuel-dispatch\index.html" (
  echo [SKIP] Missing reports\lcb-fuel-dispatch\index.html
  echo        Run build_lcb_fuel_dispatch.bat first, then push again.
  pause
  exit /b 1
)

git remote get-url origin 2>nul | findstr /i "yk-logistics/transport-rate-calculator" >nul
if errorlevel 1 (
  echo [SKIP] remote origin is not yk-logistics/transport-rate-calculator
  pause
  exit /b 1
)

for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%d"

echo Will commit only GitHub Pages folders (no other files)...
git add "reports/lcb-fuel-dispatch/"
git add "ProjectYK_System/TransportRateCalculator/reports/lcb-fuel-dispatch/"

echo.
echo --- staged ---
git diff --cached --name-only
echo.

git diff --cached --quiet
if not errorlevel 1 (
  echo [SKIP] Nothing new to commit (may already be pushed).
  goto :try_push
)

git commit -m "docs(pages): LCB fuel dispatch %TODAY%"
if errorlevel 1 (
  echo [ERROR] commit failed
  pause
  exit /b 1
)

:try_push
echo Pushing origin main ...
git push origin main
if errorlevel 1 (
  echo.
  echo [ERROR] push failed - often login / token issue.
  echo.
  echo In GitHub Desktop:
  echo   1. File -^> Add Local Repository -^> Project YK folder
  echo   2. Remote: yk-logistics/transport-rate-calculator
  echo   3. Branch main - stage only reports/lcb-fuel-dispatch
  echo   4. Summary: docs(pages): LCB fuel dispatch - Commit to main
  echo   5. Push origin
  echo.
  pause
  exit /b 1
)

echo.
echo Done. Open (wait 1-2 min after push):
echo   https://yk-logistics.github.io/transport-rate-calculator/reports/lcb-fuel-dispatch/
echo.
pause
