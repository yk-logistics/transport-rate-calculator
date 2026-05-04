@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "MODULE_PATH=%~1"
set "MODULE_PURPOSE=%~2"

if "%MODULE_PATH%"=="" (
  echo.
  echo [Project YK] Module Bootstrap
  echo.
  set /p MODULE_PATH=Module path (example: PettyCash): 
)

if "%MODULE_PURPOSE%"=="" (
  set /p MODULE_PURPOSE=Purpose (example: ระบบเงินสดย่อย): 
)

if "%MODULE_PATH%"=="" (
  echo Module path is required.
  pause
  exit /b 1
)

if "%MODULE_PURPOSE%"=="" (
  set "MODULE_PURPOSE=TODO: describe module purpose"
)

python "ProjectYK_System\bootstrap_module.py" "%MODULE_PATH%" --purpose "%MODULE_PURPOSE%"
if errorlevel 1 (
  echo.
  echo Bootstrap failed.
  pause
  exit /b 1
)

echo.
echo Bootstrap completed successfully.
pause
endlocal
