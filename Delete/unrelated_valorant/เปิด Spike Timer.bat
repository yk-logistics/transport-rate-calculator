@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Spike Timer Overlay - 5=ปลูก, 6=กู้ครึ่ง, F10=ปิด
echo ปิด: กด F10 หรือปิดหน้าต่างนี้
echo.
python spike_overlay.py
pause
