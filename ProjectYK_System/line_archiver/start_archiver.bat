@echo off
rem line_archiver — รันบนเครื่อง MVP (เปิดค้างไว้ 24 ชม.)
cd /d "%~dp0"
if not exist .env (
    echo [ERROR] ยังไม่มี .env — copy .env.example เป็น .env แล้วใส่ token ก่อน
    echo ดูขั้นตอนใน SETUP_CHECKLIST.md
    pause
    exit /b 1
)
echo Starting line_archiver on port 8020 ...
"..\app\.venv\Scripts\python.exe" main.py
pause
