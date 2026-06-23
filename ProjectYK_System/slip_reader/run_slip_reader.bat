@echo off
REM --- LCB slip-reader: scheduled launcher (every ~20 min, SYSTEM) ---
REM Loads secrets from slip_reader\.env, then reads slips from the last 2 days
REM and pushes drafts to the MVP as pending_review. Idempotent (no dupes).
cd /d C:\Users\yklog\YK_MVP

REM Load .env (KEY=VALUE per line, ignore blanks/#comments) into this process env.
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("slip_reader\.env") do set "%%A=%%B"

REM Rolling 2-day window so each run doesn't rescan the whole archive (token spend).
for /f %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-2).ToString('yyyy-MM-dd')"') do set "SINCE=%%D 00:00:00"

app\.venv\Scripts\python.exe -m slip_reader.run_once "%SINCE%"
