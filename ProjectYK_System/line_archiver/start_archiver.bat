@echo off
rem line_archiver - run on the MVP machine (keep open 24/7)
cd /d "%~dp0"
if not exist .env (
    echo [ERROR] .env not found - copy .env.example to .env and fill in tokens first
    echo See SETUP_CHECKLIST.md
    pause
    exit /b 1
)
echo Starting line_archiver on port 8020 ...
"..\app\.venv\Scripts\python.exe" main.py
pause
