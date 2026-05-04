@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo กำลังสร้าง PDF จากโฟลเดอร์ย่อย...
echo.

where py >nul 2>&1 && (
  py -3 "%~dp0build_collage_pdf.py"
  goto :done
)
where python >nul 2>&1 && (
  python "%~dp0build_collage_pdf.py"
  goto :done
)

echo ไม่พบ Python ใน PATH — ติดตั้ง Python จาก python.org แล้วลองใหม่
echo หรือเปิด Command Prompt ในโฟลเดอร์นี้แล้วรัน: py -3 build_collage_pdf.py
exit /b 1

:done
echo.
pause
