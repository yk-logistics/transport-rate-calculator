@echo off
setlocal
cd /d "%~dp0"
echo Starting local server at http://localhost:8765
echo Opening template page automatically...
start "" "http://localhost:8765/index.html"
where py >nul 2>nul
if %errorlevel%==0 (
  py -m http.server 8765
) else (
  python -m http.server 8765
)
endlocal
