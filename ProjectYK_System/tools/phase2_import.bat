@echo off

chcp 65001 >nul

cd /d "%~dp0..\.."



echo === Phase 2: Daily.xlsx + Petty Cash (canonical xlsx) ===

echo.

echo If your DB had Daily rows from import BEFORE schema v12 (no source field):

echo   1^) Backup app.db

echo   2^) Run ONCE:  python ProjectYK_System\tools\import_daily.py --mark-legacy-import --wipe-prior

echo      (only if ALL empty-source Daily rows are from Excel import, NOT manual UI)

echo.



python ProjectYK_System\tools\import_daily.py %*

if errorlevel 1 exit /b 1



python ProjectYK_System\tools\import_petty_cash.py %*

if errorlevel 1 exit /b 1



echo.

echo Done. Next: open http://localhost:8010/admin/promote — Drivers + Plates tabs.

pause

