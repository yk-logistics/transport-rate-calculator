@echo off
setlocal
cd /d "%~dp0"
echo Starting local server at http://127.0.0.1:8080
python -m http.server 8080
endlocal
