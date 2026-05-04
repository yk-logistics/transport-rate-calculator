@echo off
setlocal
cd /d "%~dp0"

set "PORT=8765"
set "TARGET=http://localhost:%PORT%/"
if not "%~1"=="" set "TARGET=http://localhost:%PORT%/%~1/index.html"

echo Starting local server at http://localhost:%PORT%/
echo.
echo Browser will open automatically:
echo %TARGET%
echo.
echo Tips:
echo - No need to run from each case folder.
echo - To open a specific case directly:
echo   run_local_server.bat 2026-04-25_71-8008
echo.

start "" "%TARGET%"

where py >nul 2>nul
if %errorlevel%==0 (
  py -m http.server %PORT%
) else (
  python -m http.server %PORT%
)

endlocal
